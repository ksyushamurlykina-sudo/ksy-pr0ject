"""
ksy-pr0ject v5 — google_creds читається зі змінної середовища GOOGLE_CREDS_JSON
"""
import logging, os, json, tempfile
from datetime import datetime, time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN         = os.environ.get("BOT_TOKEN", "ВСТАВТЕ_ТОКЕН")
GOOGLE_SHEET_ID   = os.environ.get("GOOGLE_SHEET_ID", "ВСТАВТЕ_ID")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON", "")   # JSON-рядок
GOOGLE_CREDS_FILE = os.environ.get("GOOGLE_CREDS_FILE", "google_creds.json")  # для локального запуску
ADMIN_ID          = 180212299
TIMEZONE          = pytz.timezone("Europe/Kyiv")
MORNING_TIME      = time(9, 0)
EVENING_TIME      = time(20, 0)
STATE_FILE        = "state.json"

DAYS = {
    0:  {"badge":"Вступ","title":"Вітаємо у програмі","text":"Наступні 14 днів — коротка програма усвідомленого використання смартфона.\n\n*Як усе влаштовано:*\n— Щоранку о 09:00 — завдання дня (~10–15 хв)\n— Ввечері о 20:00 — питання «Виконали?»\n— Коли виконаєте завдання — надішліть /done\n\nЗавтра — перше завдання. До зустрічі!"},
    1:  {"badge":"День 1. Усвідомлена дія","title":"Помітити автопілот","text":"У підходах MBSR/MBCT є поняття — дія на «автопілоті». Це коли поведінка відбувається без участі уваги.\n\n*Завдання:* зловіть себе на моменті, коли телефон у руках — а причини нема:\n— дістали телефон на світлофорі\n— відкрили Instagram одразу після того, як його закрили\n— розблокували, подивились — і забули навіщо\n\nПросто зловіть хоча б один такий момент."},
    2:  {"badge":"День 2. Усвідомлена дія","title":"Одна секунда","text":"*Техніка STOP* (MBSR / MBCT):\n*S* — Stop. Зупиніться.\n*T* — Take a breath. Вдих і видих.\n*O* — Observe. «Навіщо я зараз це роблю?»\n*P* — Proceed. Продовжуйте — але вже усвідомлено.\n\n*Завдання:* застосуйте STOP кілька разів сьогодні, коли рука тягнеться до телефону."},
    3:  {"badge":"День 3. Усвідомлена дія","title":"Одна дія — без екрана","text":"«When walking, walk. When eating, eat.» — ця ідея лежить в основі MBSR.\n\n*Завдання:* оберіть одну рутинну дію і проведіть її без телефону:\n— ранкова кава чи сніданок\n— дорога на роботу\n— прогулянка\n— душ\n\nЯкщо тягне до телефону — STOP."},
    4:  {"badge":"День 4. Усвідомлена дія","title":"Свідомий вибір","text":"*Завдання:* перед кожним відкриттям телефону запитайте себе: «Що я зараз відчуваю? Чого я насправді хочу?»\n\n_Завтра починаємо другий блок — Нереактивність._"},
    5:  {"badge":"День 5. Нереактивність","title":"Імпульс — це ще не дія","text":"*Завдання:* коли відчуєте бажання відкрити телефон — почекайте 2 хвилини. Поставте таймер. Після — робіть що хочете.\n\nАбо бажання зникає само, або ви берете телефон свідомо. Обидва варіанти — перемога."},
    6:  {"badge":"День 6. Нереактивність","title":"Тиша як експеримент","text":"*Завдання:* знайдіть 2 години тиші. Оберіть варіант:\n— *Повна:* телефон на беззвучний\n— *Часткова:* тільки дзвінки\n— *Мінімальна:* вимкніть один «найшумніший» застосунок\n\nСкільки часу пройшло до першого «а може, глянути?»"},
    7:  {"badge":"День 7. Нереактивність","title":"Нудьга — не ворог","text":"*Завдання:* дозвольте собі нудьгувати навмисно. 10 хвилин — без телефону, без книги. Просто будьте.\n\nНудьга — це не сигнал «потрібен телефон». Це сигнал «мозок готовий до чогось іншого»."},
    8:  {"badge":"День 8. Нереактивність","title":"Запланований думскрол","text":"*Завдання:* визначте один «дозволений» слот — наприклад, 15 хв увечері. Поставте таймер. Коли час вийде — зупиніться.\n\nВи не забороняєте собі думскрол — ви берете контроль."},
    9:  {"badge":"День 9. Безоцінковість","title":"Як би ви поставились до друга?","text":"*Завдання:* коли помітите себе з телефоном у «небажаний» момент — замість критики запитайте: «Що ти зараз відчуваєш?»\n\nБезоцінковість — це дивитись на себе із цікавістю, а не засудженням."},
    10: {"badge":"День 10. Безоцінковість","title":"Що телефон вам дає?","text":"*Завдання:* які ваші реальні потреби закриває телефон?\n\nПотім запитайте: чи є інші способи задовольнити ці потреби? Не «кращі» — просто інші."},
    11: {"badge":"День 11. Безоцінковість","title":"Внутрішній коментатор","text":"*Завдання:* зверніть увагу на внутрішнього коментатора. Що він каже?\n\n«Я помічаю, що думаю, що мав/ла би не брати телефон» — це інша позиція, ніж «я слабак/слабачка».\n\n_Це і є децентрування._"},
    12: {"badge":"День 12. Безоцінковість","title":"Два погляди на одну ситуацію","text":"*Завдання:* згадайте ситуацію, коли телефон вас турбував.\n\n*Критичний погляд:* що пішло не так?\n*З цікавістю:* що це говорить про ваші потреби?"},
    13: {"badge":"День 13. Інтеграція","title":"Не скільки — а коли і навіщо","text":"*Завдання:* перед кожним відкриттям телефону запитайте: «Зараз — це коли і навіщо?»\n\nНе потрібно нічого забороняти. Просто — запитати."},
    14: {"badge":"День 14. Фінал","title":"Що змінилось?","text":"Ви дійшли до фіналу!\n\n*Рефлексія:*\n— Що ви помітили за ці два тижні?\n— Чи змінилось щось у взаємодії з телефоном?\n— Що хотіли б зберегти?\n\n*Наступний крок:* будь ласка, заповніть повторну анкету. Дякую за участь!"},
}

DIFFICULTY_LABELS = {"☠️":"нестерпно","👿":"напряжно","😳":"нормально","❤️":"легко"}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
pending_replies: dict = {}

# ─── СТАН ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Не вдалось зберегти стан: {e}")

def get_user(uid: int) -> dict:
    state = load_state()
    key = str(uid)
    if key not in state:
        state[key] = {"day": 1, "step": None, "difficulty": ""}
        save_state(state)
    return state[key]

def set_user(uid: int, data: dict):
    state = load_state()
    state[str(uid)] = data
    save_state(state)

# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────

def get_creds():
    """Повертає credentials — зі змінної середовища або з файлу."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    if GOOGLE_CREDS_JSON:
        # Railway: читаємо з env-змінної
        info = json.loads(GOOGLE_CREDS_JSON)
        return Credentials.from_service_account_info(info, scopes=scopes)
    else:
        # Локально: читаємо з файлу
        return Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=scopes)

def save_feedback(uid, uname, day, done, difficulty, feedback):
    try:
        sheet = gspread.authorize(get_creds()).open_by_key(GOOGLE_SHEET_ID).sheet1
        now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")
        sheet.append_row([str(uid), uname, day, "так" if done else "ні", difficulty, feedback, now])
        logger.info(f"Sheets: збережено день {day} від {uname}")
    except Exception as e:
        logger.error(f"Sheets помилка: {e}")

# ─── ХЕЛПЕРИ ─────────────────────────────────────────────────────────────────

def day_text(n: int) -> str:
    d = DAYS.get(n)
    if not d:
        return "Програму завершено. Дякуємо за участь!"
    suffix = "\n\n_Коли виконаєте — надішліть /done_" if n >= 1 else ""
    return f"*{d['badge']}*\n\n*{d['title']}*\n\n{d['text']}{suffix}"

def diff_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("☠️ нестерпно", callback_data="diff_☠️"),
            InlineKeyboardButton("👿 напряжно",  callback_data="diff_👿"),
        ],
        [
            InlineKeyboardButton("😳 нормально", callback_data="diff_😳"),
            InlineKeyboardButton("❤️ легко",     callback_data="diff_❤️"),
        ],
    ])

def eve_kb(day: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Виконав/ла", callback_data=f"ev_yes_{day}"),
        InlineKeyboardButton("Не виконав/ла", callback_data=f"ev_no_{day}"),
    ]])

def nav_kb(current_day: int) -> InlineKeyboardMarkup:
    buttons = []
    if current_day > 1:
        buttons.append(InlineKeyboardButton("< попередній", callback_data=f"nav_{current_day - 1}"))
    buttons.append(InlineKeyboardButton("поточний", callback_data=f"nav_{current_day}"))
    if current_day < 14:
        buttons.append(InlineKeyboardButton("наступний >", callback_data=f"nav_{current_day + 1}"))
    return InlineKeyboardMarkup([buttons])

# ─── КОМАНДИ ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    set_user(uid, {"day": 1, "step": None, "difficulty": ""})
    await update.message.reply_text(day_text(0), parse_mode="Markdown")

async def cmd_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    current = u["day"]
    await update.message.reply_text(
        day_text(current),
        parse_mode="Markdown",
        reply_markup=nav_kb(current),
    )

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    u["step"] = "awaiting_difficulty"
    set_user(uid, u)
    await update.message.reply_text("Як вам було сьогодні?", reply_markup=diff_kb())

async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    day = u["day"]
    await update.message.reply_text(
        f"Прогрес: *{max(0, day-1)}/14* днів завершено. Поточний день: *{day}*",
        parse_mode="Markdown"
    )

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    state = load_state()
    lines = [f"Учасників: {len(state)}\n"]
    for uid, s in state.items():
        lines.append(f"- {uid} — день {s.get('day', 0)}/14")
    await update.message.reply_text("\n".join(lines))

# ─── КНОПКИ ──────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid   = q.from_user.id
    uname = q.from_user.username or str(uid)
    u     = get_user(uid)
    data  = q.data

    if data.startswith("diff_"):
        emoji = data.replace("diff_", "")
        u["difficulty"] = f"{emoji} {DIFFICULTY_LABELS.get(emoji, '')}"
        u["step"] = "awaiting_feedback"
        set_user(uid, u)
        await q.edit_message_text(
            f"Зафіксувала: {u['difficulty']}\n\n"
            "Поділіться враженнями або задайте запитання.\n"
            "Якщо не хочете — надішліть «–»"
        )
        return

    if data.startswith("ev_"):
        parts = data.split("_")
        done, day = parts[1] == "yes", int(parts[2])
        if done:
            u["step"] = "awaiting_difficulty"
            set_user(uid, u)
            await q.edit_message_text("Як вам було сьогодні?", reply_markup=diff_kb())
        else:
            save_feedback(uid, uname, day, False, "", "")
            await q.edit_message_text(
                "Нічого страшного. Завтра продовжимо.\n"
                "Якщо щось завадило — можете написати."
            )
        return

    if data.startswith("nav_"):
        nav_day = int(data.replace("nav_", ""))
        await q.edit_message_text(
            day_text(nav_day),
            parse_mode="Markdown",
            reply_markup=nav_kb(u["day"]),
        )
        return

# ─── ПОВІДОМЛЕННЯ ────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    uname = update.effective_user.username or str(uid)
    text  = update.message.text

    if uid == ADMIN_ID and update.message.reply_to_message:
        target = pending_replies.get(update.message.reply_to_message.message_id)
        if target:
            try:
                await context.bot.send_message(chat_id=target, text=f"Відповідь від дослідника:\n\n{text}")
                await update.message.reply_text("Відповідь надіслано.")
            except Exception as e:
                await update.message.reply_text(f"Помилка: {e}")
        else:
            await update.message.reply_text("Не вдалося визначити учасника. Відповідайте reply саме на пересланий фідбек.")
        return

    u   = get_user(uid)
    day = u.get("day", 1)

    if u.get("step") == "awaiting_feedback":
        feedback   = "" if text.strip() == "–" else text
        difficulty = u.get("difficulty", "")
        save_feedback(uid, uname, day, True, difficulty, feedback)
        u["step"] = None
        u["day"]  = min(day + 1, 15)
        set_user(uid, u)
        if feedback:
            fwd = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"Фідбек — день {day}\n@{uname} (id: {uid})\nСкладність: {difficulty}\n\n{feedback}\n\nВідповідайте reply на це повідомлення.",
            )
            pending_replies[fwd.message_id] = uid
        await update.message.reply_text("Дякую! Зафіксувала.\n\nЗавтра о 09:00 — наступне завдання.")
        return

    save_feedback(uid, uname, day, False, "", f"[повідомлення] {text}")
    fwd = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Повідомлення — день {day}\n@{uname} (id: {uid})\n\n{text}\n\nВідповідайте reply на це повідомлення.",
    )
    pending_replies[fwd.message_id] = uid
    await update.message.reply_text("Дякую! Дослідник отримає ваше повідомлення.")

# ─── ПЛАНУВАЛЬНИК ─────────────────────────────────────────────────────────────

async def job_morning(context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    for uid_str, s in state.items():
        day = s.get("day", 0)
        if 1 <= day <= 14:
            try:
                await context.bot.send_message(chat_id=int(uid_str), text=day_text(day), parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ранок {uid_str}: {e}")

async def job_evening(context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    for uid_str, s in state.items():
        day = s.get("day", 0)
        if 1 <= day <= 14:
            try:
                await context.bot.send_message(
                    chat_id=int(uid_str),
                    text=f"Вечірня перевірка — день {day}\n\nЯк пройшов день?\nВдалося виконати «{DAYS[day]['title']}»?",
                    reply_markup=eve_kb(day),
                )
            except Exception as e:
                logger.error(f"Вечір {uid_str}: {e}")

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("day",      cmd_day))
    app.add_handler(CommandHandler("done",     cmd_done))
    app.add_handler(CommandHandler("progress", cmd_progress))
    app.add_handler(CommandHandler("stats",    cmd_stats))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_daily(job_morning, time=MORNING_TIME, days=tuple(range(7)), name="morning")
    app.job_queue.run_daily(job_evening, time=EVENING_TIME, days=tuple(range(7)), name="evening")
    logger.info("Бот запущено.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
