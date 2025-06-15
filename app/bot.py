 from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.models import User, Sprint, Word, SprintStatus
from app.filters import is_valid_input
from app.config import ADMIN_IDS
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import csv
import io
import logging

logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for detailed logs
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    logger.debug(f"Received /start from user_id: {user_id}, username: @{username}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    try:
        # Register or update user in DB
        db_user = db.query(User).filter(User.id == user_id).first()
        logger.debug(f"DB query for user_id {user_id}: {'Found' if db_user else 'Not found'}")
        if not db_user:
            db_user = User(id=user_id, username=username)
            db.add(db_user)
            db.commit()
            logger.debug(f"Created new user in DB: user_id {user_id}, username: @{username}")
        else:
            db_user.username = username  # Update username if changed
            db.commit()
            logger.debug(f"Updated username for user_id {user_id} to @{username}")

        # Query active sprints
        active_sprints = db.query(Sprint).filter(Sprint.status == SprintStatus.active).all()
        logger.debug(f"Found {len(active_sprints)} active sprints for user_id {user_id}")

        # Build response message
        response = "🎉 Привет! Готов кинуть пару слов для спринта? (Hi! Ready to drop some words for the sprint?)\n\n"
        if active_sprints:
            response += "📋 Текущие активные спринты (Active sprints):\n"
            for sprint in active_sprints:
                response += f"Спринт #{sprint.id}: Тема '{sprint.theme}', Длительность: {sprint.duration} дней (Sprint #{sprint.id}: Theme '{sprint.theme}', Duration: {sprint.duration} days)\n"
            response += "\nОтправь 1 или 3 слова для участия! (Send 1 or 3 words to participate!)"
        else:
            response += "❌ Сейчас нет активных спринтов. Жди объявления нового! (No active sprints right now. Wait for a new one!)"

        await update.message.reply_text(response)
        logger.debug(f"Sent response to user_id {user_id}: {response}")
    except Exception as e:
        logger.error(f"Error in start for user_id {user_id}: {e}")
        await update.message.reply_text("❌ Ой, что-то пошло не так! (Something went wrong!)")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    logger.debug(f"Received /whoami from user_id: {user_id}, username: @{username}")
    try:
        is_admin = user_id in ADMIN_IDS
        response = (
            f"ℹ️ Твой Telegram ID: {user_id}\n"
            f"Username: @{username}\n"
            f"Статус админа: {'Да' if is_admin else 'Нет'} (Admin status: {'True' if is_admin else 'False'})\n"
        )
        if is_admin:
            response += "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        await update.message.reply_text(response)
        logger.debug(f"Sent /whoami response to user_id {user_id}: {response}")
    except Exception as e:
        logger.error(f"Error in whoami for user_id {user_id}: {e}")
        await update.message.reply_text("❌ Ой, что-то пошло не так! (Something went wrong!)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /help from user_id: {user_id}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting /help")
        await update.message.reply_text("❌ Только админ может использовать /help! (Only admins can use /help!)")
        return
    try:
        response = (
            "📖 Возможности админа (Admin options):\n"
            "/start_sprint <длительность: 1, 7 или 30> <тема> - Запустить новый спринт (Start a new sprint)\n"
            "/end_sprint <id> - Завершить спринт (End a sprint)\n"
            "/get_words <id> - Получить слова спринта в CSV (Get sprint words in CSV)\n"
            "/list_sprints - Показать все спринты (List all sprints)\n"
            "/broadcast <текст> - Отправить сообщение всем пользователям (Send message to all users)\n"
            "\nНапиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        await update.message.reply_text(response)
        logger.debug(f"Sent /help response to admin {user_id}")
    except Exception as e:
        logger.error(f"Error in help_command for user_id {user_id}: {e}")
        await update.message.reply_text("❌ Ой, что-то пошло не так! (Something went wrong!)")

async def start_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /start_sprint from user_id: {user_id}, args: {context.args}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting command")
        await update.message.reply_text(
            "❌ Только админ может запускать спринты! (Only the admin can start sprints!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        return
    try:
        if len(context.args) < 2:
            logger.debug(f"Invalid arguments for /start_sprint: {context.args}")
            await update.message.reply_text(
                "❌ Используй: /start_sprint <длительность: 1, 7 или 30> <тема> (Use: /start_sprint <duration: 1, 7, or 30> <theme>)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        duration = int(context.args[0])
        logger.debug(f"Parsed duration: {duration}")
        if duration not in [1, 7, 30]:
            raise ValueError("Invalid duration")
        theme = " ".join(context.args[1:])
        logger.debug(f"Parsed theme: {theme}")
        if not theme:
            raise ValueError("Theme is required")
        sprint = Sprint(
            duration=duration,
            theme=theme,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=duration)
        )
        db.add(sprint)
        db.commit()
        logger.debug(f"Created sprint #{sprint.id} with duration {duration} and theme '{theme}'")
        users = db.query(User).all()
        logger.debug(f"Found {len(users)} users to notify about new sprint")
        for user in users:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"🎉 Новый спринт начался! Тема: {theme}. Время: {duration} дней. Кидайте свои слова! (New sprint started! Theme: {theme}. Duration: {duration} days. Send your words!)"
            )
            logger.debug(f"Notified user_id {user.id} about new sprint")
        await update.message.reply_text(
            f"✅ Спринт #{sprint.id} запущен! (Sprint #{sprint.id} started!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        logger.debug(f"Confirmed sprint start to admin {user_id}")
    except ValueError as e:
        logger.error(f"ValueError in start_sprint for user_id {user_id}: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}. Используй: /start_sprint <длительность: 1, 7 или 30> <тема> (Error: {str(e)}. Use: /start_sprint <duration: 1, 7, or 30> <theme>)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
    except Exception as e:
        logger.error(f"Error in start_sprint for user_id {user_id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось запустить спринт! (Failed to start sprint!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )

async def end_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /end_sprint from user_id: {user_id}, args: {context.args}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting command")
        await update.message.reply_text(
            "❌ Только админ может завершать спринты! (Only the admin can end sprints!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        return
    try:
        if not context.args:
            logger.debug(f"No sprint ID provided for /end_sprint")
            await update.message.reply_text(
                "❌ Укажи ID спринта: /end_sprint <id> (Specify sprint ID: /end_sprint <id>)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        sprint_id = int(context.args[0])
        logger.debug(f"Parsed sprint_id: {sprint_id}")
        sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
        if not sprint:
            logger.debug(f"Sprint {sprint_id} not found")
            await update.message.reply_text(
                "❌ Спринт не найден! (Sprint not found!)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        sprint.status = SprintStatus.completed
        db.commit()
        logger.debug(f"Updated sprint {sprint_id} to completed")
        await update.message.reply_text(
            f"✅ Спринт #{sprint_id} завершён! (Sprint #{sprint_id} completed!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        logger.debug(f"Confirmed sprint end to admin {user_id}")
    except (IndexError, ValueError):
        logger.error(f"Invalid sprint ID in end_sprint for user_id {user_id}")
        await update.message.reply_text(
            "❌ Укажи ID спринта: /end_sprint <id> (Specify sprint ID: /end_sprint <id>)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
    except Exception as e:
        logger.error(f"Error in end_sprint for user_id {user_id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось завершить спринт! (Failed to end sprint!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )

async def get_words(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /get_words from user_id: {user_id}, args: {context.args}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting command")
        await update.message.reply_text(
            "❌ Только админ может получать слова! (Only the admin can get words!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        return
    try:
        if not context.args:
            logger.debug(f"No sprint ID provided for /get_words")
            await update.message.reply_text(
                "❌ Укажи ID спринта: /get_words <id> (Specify sprint ID: /get_words <id>)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        sprint_id = int(context.args[0])
        logger.debug(f"Parsed sprint_id: {sprint_id}")
        words = db.query(Word).filter(Word.sprint_id == sprint_id).all()
        logger.debug(f"Found {len(words)} words for sprint {sprint_id}")
        if not words:
            await update.message.reply_text(
                "❌ Нет слов для этого спринта! (No words for this sprint!)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
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
        logger.debug(f"Sent words CSV for sprint {sprint_id} to admin {user_id}")
        await update.message.reply_text(
            f"✅ Слова для спринта #{sprint_id} отправлены! (Words for sprint #{sprint_id} sent!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
    except (IndexError, ValueError):
        logger.error(f"Invalid sprint ID in get_words for user_id {user_id}")
        await update.message.reply_text(
            "❌ Укажи ID спринта: /get_words <id> (Specify sprint ID: /get_words <id>)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
    except Exception as e:
        logger.error(f"Error in get_words for user_id {user_id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить слова! (Failed to get words!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )

async def list_sprints(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /list_sprints from user_id: {user_id}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting command")
        await update.message.reply_text(
            "❌ Только админ может смотреть спринты! (Only the admin can list sprints!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        return
    try:
        sprints = db.query(Sprint).all()
        logger.debug(f"Found {len(sprints)} sprints")
        if not sprints:
            await update.message.reply_text(
                "❌ Нет спринтов! (No sprints!)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        response = "📋 Спринты:\n"
        for sprint in sprints:
            response += f"ID: {sprint.id}, Тема: {sprint.theme}, Длительность: {sprint.duration} дней, Статус: {sprint.status.value} (Status: {sprint.status.value})\n"
        response += "\nНапиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        await update.message.reply_text(response)
        logger.debug(f"Sent sprints list to admin {user_id}")
    except Exception as e:
        logger.error(f"Error in list_sprints for user_id {user_id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить список спринтов! (Failed to list sprints!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    logger.debug(f"Received /broadcast from user_id: {user_id}, args: {context.args}")
    logger.debug(f"Checking if user is admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        logger.debug(f"User {user_id} is not an admin, rejecting command")
        await update.message.reply_text(
            "❌ Только админ может рассылать сообщения! (Only the admin can broadcast messages!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        return
    try:
        message = " ".join(context.args)
        if not message:
            logger.debug(f"No message provided for /broadcast")
            await update.message.reply_text(
                "❌ Укажи сообщение: /broadcast <текст> (Specify message: /broadcast <text>)\n"
                "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
            )
            return
        users = db.query(User).all()
        logger.debug(f"Found {len(users)} users to broadcast to")
        for user in users:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"📢 {message} ({message})"
            )
            logger.debug(f"Broadcasted message to user_id {user.id}")
        await update.message.reply_text(
            "✅ Сообщение отправлено всем пользователям! (Message sent to all users!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )
        logger.debug(f"Confirmed broadcast to admin {user_id}")
    except Exception as e:
        logger.error(f"Error in broadcast for user_id {user_id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось отправить сообщение! (Failed to send broadcast!)\n"
            "Напиши /help, чтобы увидеть свои возможности (Write /help to see your options)"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logger.debug(f"Received message from user_id: {user_id}, text: '{text}'")
    try:
        active_sprints = db.query(Sprint).filter(Sprint.status == SprintStatus.active).all()
        logger.debug(f"Found {len(active_sprints)} active sprints")
        if not active_sprints:
            await update.message.reply_text("❌ Нет активных спринтов! Жди новый! (No active sprints! Wait for a new one!)")
            return
        is_valid, result = is_valid_input(text)
        logger.debug(f"Input validation result for '{text}': valid={is_valid}, result={result}")
        if not is_valid:
            await update.message.reply_text(result)
            return
        language = result
        for sprint in active_sprints:
            existing_submission = db.query(Word).filter(Word.user_id == user_id, Word.sprint_id == sprint.id).first()
            logger.debug(f"Checked for existing submission for user_id {user_id}, sprint {sprint.id}: {'Found' if existing_submission else 'Not found'}")
            if existing_submission:
                await update.message.reply_text(
                    f"❌ Ты уже кинул слова для спринта #{sprint.id}! (You already submitted words for sprint #{sprint.id}!)")
                continue
            word = Word(user_id=user_id, sprint_id=sprint.id, words=text, language=language)
            db.add(word)
            db.commit()
            logger.debug(f"Saved word '{text}' for user_id {user_id}, sprint {sprint.id}, language: {language}")
            await update.message.reply_text(
                f"✅ Слова приняты для спринта #{sprint.id}! (Words accepted for sprint #{sprint.id}!)")
    except Exception as e:
        logger.error(f"Error in handle_message for user_id {user_id}: {e}")
        await update.message.reply_text("❌ Ой, что-то пошло не так! (Something went wrong!)")

async def daily_report(context: ContextTypes.DEFAULT_TYPE, db: Session):
    logger.debug("Running daily report")
    try:
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        new_users = db.query(User).filter(User.joined_at >= start_of_day).count()
        new_words = db.query(Word).filter(Word.submitted_at >= start_of_day).count()
        sprints = db.query(Sprint).all()
        logger.debug(f"Daily report stats: new_users={new_users}, new_words={new_words}, sprints={len(sprints)}")
        report = f"📊 Отчёт за {today}:\nНовых пользователей: {new_users}\nНовых слов: {new_words}\n"
        for sprint in sprints:
            total_words = db.query(Word).filter(Word.sprint_id == sprint.id).count()
            report += f"Спринт #{sprint.id} ({sprint.status.value}): {total_words} слов\n"
        report += f"(Report for {today}: New users: {new_users}, New words: {new_words})"
        logger.debug(f"Generated report: {report}")
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=report)
            logger.debug(f"Sent daily report to admin_id {admin_id}")
    except Exception as e:
        logger.error(f"Error in daily_report: {e}")

def setup_bot(app: Application, db: Session):
    logger.debug(f"Setting up bot with ADMIN_IDS: {ADMIN_IDS}")
    try:
        app.add_handler(CommandHandler("start", lambda update, context: start(update, context, db)))
        app.add_handler(CommandHandler("whoami", lambda update, context: whoami(update, context, db)))
        app.add_handler(CommandHandler("help", lambda update, context: help_command(update, context, db)))
        app.add_handler(CommandHandler("start_sprint", lambda update, context: start_sprint(update, context, db)))
        app.add_handler(CommandHandler("end_sprint", lambda update, context: end_sprint(update, context, db)))
        app.add_handler(CommandHandler("get_words", lambda update, context: get_words(update, context, db)))
        app.add_handler(CommandHandler("list_sprints", lambda update, context: list_sprints(update, context, db)))
        app.add_handler(CommandHandler("broadcast", lambda update, context: broadcast(update, context, db)))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_message(update, context, db)))
        scheduler = AsyncIOScheduler()
        scheduler.add_job(daily_report, 'cron', hour=0, minute=0, args=[app.bot, db])
        scheduler.start()
        logger.debug("Bot handlers and scheduler set up successfully")
    except Exception as e:
        logger.error(f"Error in setup_bot: {e}")
        raise
