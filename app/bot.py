from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.models import User, Sprint, Word, SprintStatus
from app.filters import is_valid_input
from app.config import ADMIN_ID
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import csv
import io

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        db_user = User(id=user_id, username=username)
        db.add(db_user)
        db.commit()
    await update.message.reply_text(
        "🎉 Привет! Готов кинуть пару слов для спринта? (Hi! Ready to drop some words for the sprint?)"
    )

async def start_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может запускать спринты! (Only the admin can start sprints!)")
        return
    try:
        duration = int(context.args[0])
        if duration not in [1, 7, 30]:
            raise ValueError
        theme = " ".join(context.args[1:])
        if not theme:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Используй: /start_sprint <длительность: 1, 7 или 30> <тема> (Use: /start_sprint <duration: 1, 7, or 30> <theme>)"
        )
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
    for user in users:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"🎉 Новый спринт начался! Тема: {theme}. Время: {duration} дней. Кидайте свои слова! (New sprint started! Theme: {theme}. Duration: {duration} days. Send your words!)"
        )
    await update.message.reply_text(f"✅ Спринт #{sprint.id} запущен! (Sprint #{sprint.id} started!)")

async def end_sprint(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может завершать спринты! (Only the admin can end sprints!)")
        return
    try:
        sprint_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Укажи ID спринта: /end_sprint <id> (Specify sprint ID: /end_sprint <id>)")
        return
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        await update.message.reply_text("❌ Спринт не найден! (Sprint not found!)")
        return
    sprint.status = SprintStatus.completed
    db.commit()
    await update.message.reply_text(f"✅ Спринт #{sprint_id} завершён! (Sprint #{sprint_id} completed!)")

async def get_words(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может получать слова! (Only the admin can get words!)")
        return
    try:
        sprint_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Укажи ID спринта: /get_words <id> (Specify sprint ID: /get_words <id>)")
        return
    words = db.query(Word).filter(Word.sprint_id == sprint_id).all()
    if not words:
        await update.message.reply_text("❌ Нет слов для этого спринта! (No words for this sprint!)")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["word", "user_id", "language", "submitted_at"])
    for word in words:
        writer.writerow([word.words, word.user_id, word.language, word.submitted_at])
    output.seek(0)
    await context.bot.send_document(
        chat_id=update.effective_user.id,
        document=io.BytesIO(output.getvalue().encode()),
        filename=f"sprint_{sprint_id}_words.csv"
    )

async def list_sprints(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может смотреть спринты! (Only the admin can list sprints!)")
        return
    sprints = db.query(Sprint).all()
    if not sprints:
        await update.message.reply_text("❌ Нет спринтов! (No sprints!)")
        return
    response = "📋 Спринты:\n"
    for sprint in sprints:
        response += f"ID: {sprint.id}, Тема: {sprint.theme}, Длительность: {sprint.duration} дней, Статус: {sprint.status.value} (Status: {sprint.status.value})\n"
    await update.message.reply_text(response)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только админ может рассылать сообщения! (Only the admin can broadcast messages!)")
        return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("❌ Укажи сообщение: /broadcast <текст> (Specify message: /broadcast <text>)")
        return
    users = db.query(User).all()
    for user in users:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"📢 {message} ({message})"
        )
    await update.message.reply_text("✅ Сообщение отправлено всем пользователям! (Message sent to all users!)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    active_sprints = db.query(Sprint).filter(Sprint.status == SprintStatus.active).all()
    if not active_sprints:
        await update.message.reply_text("❌ Нет активных спринтов! Жди новый! (No active sprints! Wait for a new one!)")
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
                f"❌ Ты уже кинул слова для спринта #{sprint.id}! (You already submitted words for sprint #{sprint.id}!)")
            continue
        word = Word(user_id=user_id, sprint_id=sprint.id, words=text, language=language)
        db.add(word)
        db.commit()
        await update.message.reply_text(
            f"✅ Слова приняты для спринта #{sprint.id}! (Words accepted for sprint #{sprint.id}!)")

async def daily_report(context: ContextTypes.DEFAULT_TYPE, db: Session):
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    new_users = db.query(User).filter(User.joined_at >= start_of_day).count()
    new_words = db.query(Word).filter(Word.submitted_at >= start_of_day).count()
    sprints = db.query(Sprint).all()
    report = f"📊 Отчёт за {today}:\nНовых пользователей: {new_users}\nНовых слов: {new_words}\n"
    for sprint in sprints:
        total_words = db.query(Word).filter(Word.sprint_id == sprint.id).count()
        report += f"Спринт #{sprint.id} ({sprint.status.value}): {total_words} слов\n"
    report += f"(Report for {today}: New users: {new_users}, New words: {new_words})"
    await context.bot.send_message(chat_id=ADMIN_ID, text=report)

def setup_bot(app: Application, db: Session):
    app.add_handler(CommandHandler("start", lambda update, context: start(update, context, db)))
    app.add_handler(CommandHandler("start_sprint", lambda update, context: start_sprint(update, context, db)))
    app.add_handler(CommandHandler("end_sprint", lambda update, context: end_sprint(update, context, db)))
    app.add_handler(CommandHandler("get_words", lambda update, context: get_words(update, context, db)))
    app.add_handler(CommandHandler("list_sprints", lambda update, context: list_sprints(update, context, db)))
    app.add_handler(CommandHandler("broadcast", lambda update, context: broadcast(update, context, db)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_message(update, context, db)))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_report, 'cron', hour=0, minute=0, args=[app.bot, db])
    scheduler.start()
