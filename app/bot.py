from telegram import Update, MessageEntity
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, Filters
from sqlalchemy.orm import Session
from app.models import User, Sprint, Word, SprintStatus
from app.filters import is_valid_input
from app.config import ADMIN_IDS
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import csv
import io
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Кастомный фильтр для TEXT_LINK, представляющих команды
class BotCommandLink(Filters):
    def filter(self, message):
        if message.entities:
            for entity in message.entities:
                if entity.type == MessageEntity.TEXT_LINK and entity.url.startswith('tg://bot_command?command='):
                    return True
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция start, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            db_user = User(id=user_id, username=username)
            db.add(db_user)
            db.commit()
        else:
            db_user.username = username
            db.commit()

        active_sprints = db.query(Sprint).filter(Sprint.status == SprintStatus.active).all()
        response = "🎉 Привет! Готов кинуть пару слов для спринта?\n\n"
        if active_sprints:
            response += "📋 Текущие активные спринты:\n"
            for sprint in active_sprints:
                response += f"Спринт #{sprint.id}: Тема '{sprint.theme}', Длительность: {sprint.duration} дней\n"
            response += "\nОтправь 1 или 3 слова для участия!"
        else:
            response += "❌ Сейчас нет активных спринтов. Жди объявления нового!"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in start for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция start, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция whoami, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        is_admin = user_id in ADMIN_IDS
        response = (
            f"ℹ️ Твой Telegram ID: {user_id}\n"
            f"Username: @{username}\n"
            f"Статус админа: {'Да' if is_admin else 'Нет'}\n"
        )
        if is_admin:
            response += "Напиши /help, чтобы увидеть свои возможности"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in whoami for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция whoami, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция help_command, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может использовать /help!")
            return
        response = (
            "📖 Возможности админа:\n"
            "/start_sprint <длительность: 1, 7 или 30> <тема> - Запустить новый спринт\n"
            "/end_sprint <id> - Завершить спринт\n"
            "/get_words <id> - Получить слова спринта в CSV\n"
            "/list_sprints - Показать все спринты\n"
            "/broadcast <текст> - Отправить сообщение всем пользователям\n"
            "/test_sprint - Тестовая команда\n"
            "\nНапиши /help, чтобы увидеть свои возможности"
        )
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in help_command for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция help_command, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def start_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция start_sprint, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может запускать спринты!\nНапиши /help, чтобы увидеть свои возможности")
            return

        if len(context.args) < 2:
            await update.message.reply_text("❌ Используй: /start_sprint <длительность: 1, 7 или 30> <тема>\nНапиши /help, чтобы увидеть свои возможности")
            return

        duration = int(context.args[0])
        if duration not in [1, 7, 30]:
            await update.message.reply_text("❌ Длительность должна быть 1, 7 или 30 дней!\nНапиши /help, чтобы увидеть свои возможности")
            return

        theme = " ".join(context.args[1:])
        if not theme:
            await update.message.reply_text("❌ Укажи тему спринта!\nНапиши /help, чтобы увидеть свои возможности")
            return

        sprint = Sprint(
            duration=duration,
            theme=theme,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=duration)
        )
        db.add(sprint)
        db.commit()

        users = db.query(User).all()
        logger.debug(f"Количество пользователей для уведомления: {len(users)}")
        if not users:
            logger.debug("Нет пользователей для уведомления о новом спринте")
        for user in users:
            logger.debug(f"Отправка уведомления о спринте пользователю {user.id}")
            await context.bot.send_message(
                chat_id=user.id,
                text=f"🎉 Новый спринт начался! Тема: {theme}. Время: {duration} дней. Кидайте свои слова!"
            )
            logger.debug(f"Уведомление отправлено пользователю {user.id}")
        await update.message.reply_text(
            f"✅ Спринт #{sprint.id} запущен!\nНапиши /help, чтобы увидеть свои возможности"
        )
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Неверный формат длительности. Используй: /start_sprint <длительность: 1, 7 или 30> <тема>\nНапиши /help, чтобы увидеть свои возможности")
    except Exception as e:
        logger.error(f"Error in start_sprint for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось запустить спринт!\nНапиши /help, чтобы увидеть свои возможности")
    finally:
        logger.debug(f"Функция start_sprint, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def test_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция test_sprint, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        await update.message.reply_text("✅ Тестовая команда работает! Напиши /help для других команд.")
    except Exception as e:
        logger.error(f"Error in test_sprint for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция test_sprint, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def end_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция end_sprint, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может завершать спринты!\nНапиши /help, чтобы увидеть свои возможности")
            return
        if not context.args:
            await update.message.reply_text("❌ Укажи ID спринта: /end_sprint <id>\nНапиши /help, чтобы увидеть свои возможности")
            return
        sprint_id = int(context.args[0])
        sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
        if not sprint:
            await update.message.reply_text("❌ Спринт не найден!\nНапиши /help, чтобы увидеть свои возможности")
            return
        sprint.status = SprintStatus.completed
        db.commit()
        await update.message.reply_text(
            f"✅ Спринт #{sprint_id} завершён!\nНапиши /help, чтобы увидеть свои возможности"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Укажи ID спринта: /end_sprint <id>\nНапиши /help, чтобы увидеть свои возможности")
    except Exception as e:
        logger.error(f"Error in end_sprint for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось завершить спринт!\nНапиши /help, чтобы увидеть свои возможности")
    finally:
        logger.debug(f"Функция end_sprint, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def get_words(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция get_words, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может получать слова!\nНапиши /help, чтобы увидеть свои возможности")
            return
        if not context.args:
            await update.message.reply_text("❌ Укажи ID спринта: /get_words <id>\nНапиши /help, чтобы увидеть свои возможности")
            return
        sprint_id = int(context.args[0])
        words = db.query(Word).filter(Word.sprint_id == sprint_id).all()
        if not words:
            await update.message.reply_text("❌ Нет слов для этого спринта!\nНапиши /help, чтобы увидеть свои возможности")
            return
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["word", "user_id", "language", "submitted_at"])
        for word in words:
            writer.writerow([word.words, word.user_id, word.language, word.submitted_at])
        output.seek(0)
        await context.bot.send_document(
            chat_id=user_id,
            document=io.BytesIO(output.getvalue().encode()),
            filename=f"sprint_{sprint_id}_words.csv"
        )
        await update.message.reply_text(
            f"✅ Слова для спринта #{sprint_id} отправлены!\nНапиши /help, чтобы увидеть свои возможности"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Укажи ID спринта: /get_words <id>\nНапиши /help, чтобы увидеть свои возможности")
    except Exception as e:
        logger.error(f"Error in get_words for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось получить слова!\nНапиши /help, чтобы увидеть свои возможности")
    finally:
        logger.debug(f"Функция get_words, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def list_sprints(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция list_sprints, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может смотреть спринты!\nНапиши /help, чтобы увидеть свои возможности")
            return
        sprints = db.query(Sprint).all()
        if not sprints:
            await update.message.reply_text("❌ Нет спринтов!\nНапиши /help, чтобы увидеть свои возможности")
            return
        response = "📋 Спринты:\n"
        for sprint in sprints:
            response += f"ID: {sprint.id}, Тема: {sprint.theme}, Длительность: {sprint.duration} дней, Статус: {sprint.status.value}\n"
        response += "\nНапиши /help, чтобы увидеть свои возможности"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in list_sprints for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось получить список спринтов!\nНапиши /help, чтобы увидеть свои возможности")
    finally:
        logger.debug(f"Функция list_sprints, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция broadcast, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Только админ может рассылать сообщения!\nНапиши /help, чтобы увидеть свои возможности")
            return
        message = " ".join(context.args)
        if not message:
            await update.message.reply_text("❌ Укажи сообщение: /broadcast <текст>\nНапиши /help, чтобы увидеть свои возможности")
            return
        users = db.query(User).all()
        logger.debug(f"Количество пользователей в базе: {len(users)}")
        if not users:
            await update.message.reply_text("❌ Нет пользователей в базе для рассылки!\nНапиши /help, чтобы увидеть свои возможности")
            return
        for user in users:
            logger.debug(f"Отправка сообщения пользователю {user.id}")
            await context.bot.send_message(
                chat_id=user.id,
                text=f"📢 {message}"
            )
            logger.debug(f"Сообщение отправлено пользователю {user.id}")
        await update.message.reply_text("✅ Сообщение отправлено всем пользователям!\nНапиши /help, чтобы увидеть свои возможности")
    except Exception as e:
        logger.error(f"Error in broadcast for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось отправить сообщение!\nНапиши /help, чтобы увидеть свои возможности")
    finally:
        logger.debug(f"Функция broadcast, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция handle_message, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        if text.startswith('/'):
            logger.debug(f"Skipping command in handle_message: {text}")
            return
        active_sprints = db.query(Sprint).filter(Sprint.status == SprintStatus.active).all()
        if not active_sprints:
            await update.message.reply_text("❌ Нет активных спринтов! Жди новый!")
            return
        is_valid, result = is_valid_input(text)
        if not is_valid:
            await update.message.reply_text(result)
            return
        language = result
        for sprint in active_sprints:
            existing_submission = db.query(Word).filter(Word.user_id == user_id, Word.sprint_id == sprint.id).first()
            if existing_submission:
                await update.message.reply_text(
                    f"❌ Ты уже кинул слова для спринта #{sprint.id}!")
                continue
            word = Word(user_id=user_id, sprint_id=sprint.id, words=text, language=language)
            db.add(word)
            db.commit()
            await update.message.reply_text(
                f"✅ Слова приняты для спринта #{sprint.id}!")
    except Exception as e:
        logger.error(f"Error in handle_message for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция handle_message, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def handle_unrecognized_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    args = context.args
    logger.debug(f"Функция handle_unrecognized_command, СТАРТ, параметры: {{text: '{text}', args: {args}}}")
    try:
        entities = update.message.entities if update.message.entities else []
        logger.debug(f"Message entities: {[(e.type, e.url if e.url else '') for e in entities]}")
        await update.message.reply_text(
            f"❌ Неизвестная команда: {text}. Напиши /help для списка команд!"
        )
    except Exception as e:
        logger.error(f"Error in handle_unrecognized_command for user_id {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ой, что-то пошло не так!")
    finally:
        logger.debug(f"Функция handle_unrecognized_command, ЗАВЕРШЕНИЕ, параметры: {{text: '{text}', args: {args}}}")

async def daily_report(context: ContextTypes.DEFAULT_TYPE, db: Session):
    logger.debug("Функция daily_report, СТАРТ, параметры: {}")
    try:
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        new_users = db.query(User).filter(User.joined_at >= start_of_day).count()
        new_words = db.query(Word).filter(Word.submitted_at >= start_of_day).count()
        sprints = db.query(Sprint).all()
        report = f"📊 Отчёт за {today}:\nНовых пользователей: {new_users}\nНовых слов: {new_words}\n"
        for sprint in sprints:
            total_words = db.query(Word).filter(Word.sprint_id == sprint.id).count()
            report += f"Спринт #{sprint.id} ({sprint.status.value}): {total_words} слов\n"
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=report)
    except Exception as e:
        logger.error(f"Error in daily_report: {e}", exc_info=True)
    finally:
        logger.debug("Функция daily_report, ЗАВЕРШЕНИЕ, параметры: {}")

def setup_bot(app: Application, db: Session):
    logger.debug(f"Setting up bot with ADMIN_IDS: {ADMIN_IDS}")
    try:
        logger.debug("Registering command handlers")
        app.add_handler(CommandHandler("start", lambda update, context: start(update, context, db)))
        logger.debug("Registered /start handler")
        app.add_handler(CommandHandler("whoami", lambda update, context: whoami(update, context, db)))
        logger.debug("Registered /whoami handler")
        app.add_handler(CommandHandler("help", lambda update, context: help_command(update, context, db)))
        logger.debug("Registered /help handler")
        app.add_handler(CommandHandler("start_sprint", lambda update, context: start_sprint(update, context, db), filters=filters.COMMAND | BotCommandLink()))
        logger.debug("Registered /start_sprint handler")
        app.add_handler(CommandHandler("startsprint", lambda update, context: start_sprint(update, context, db), filters=filters.COMMAND | BotCommandLink()))
        logger.debug("Registered /startsprint handler")
        app.add_handler(CommandHandler("test_sprint", lambda update, context: test_sprint(update, context, db)))
        logger.debug("Registered /test_sprint handler")
        app.add_handler(CommandHandler("end_sprint", lambda update, context: end_sprint(update, context, db)))
        logger.debug("Registered /end_sprint handler")
        app.add_handler(CommandHandler("get_words", lambda update, context: get_words(update, context, db)))
        logger.debug("Registered /get_words handler")
        app.add_handler(CommandHandler("list_sprints", lambda update, context: list_sprints(update, context, db)))
        logger.debug("Registered /list_sprints handler")
        app.add_handler(CommandHandler("broadcast", lambda update, context: broadcast(update, context, db), filters=filters.COMMAND | BotCommandLink()))
        logger.debug("Registered /broadcast handler")
        app.add_handler(MessageHandler(filters.COMMAND, lambda update, context: handle_unrecognized_command(update, context)))
        logger.debug("Registered unrecognized command handler")
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_message(update, context, db)))
        logger.debug("Registered text message handler")

        logger.debug("Setting up scheduler for daily report")
        scheduler = AsyncIOScheduler()
        scheduler.add_job(daily_report, 'cron', hour=0, minute=0, args=[app.bot, db])
        scheduler.start()
        logger.debug("Bot setup completed")
    except Exception as e:
        logger.error(f"Error in setup_bot: {e}", exc_info=True)
        raise
