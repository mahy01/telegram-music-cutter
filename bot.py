import os
import json
import tempfile
import subprocess

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError


load_dotenv()


# =========================================================
# تنظیمات
# =========================================================

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_FILE = "required_channel.json"

CANCEL_BUTTON = "لغو"


# =========================================================
# مدیریت کانال جوین اجباری
# =========================================================

def load_required_channel():
    """خواندن کانال جوین اجباری از فایل."""

    if not os.path.exists(CHANNEL_FILE):
        return None

    try:
        with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("channel")

    except Exception:
        return None


def save_required_channel(channel: str):
    """ذخیره کانال جوین اجباری."""

    with open(CHANNEL_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"channel": channel},
            f,
            ensure_ascii=False,
            indent=2,
        )


def remove_required_channel():
    """حذف کانال جوین اجباری."""

    if os.path.exists(CHANNEL_FILE):
        os.remove(CHANNEL_FILE)


# =========================================================
# پیام خطای عمومی
# =========================================================

async def send_error(update: Update):
    """ارسال پیام خطای عمومی."""

    if update.effective_message:
        await update.effective_message.reply_text(
            "مشکلی پیش اومده 😿\n"
            "دوباره امتحان کن."
        )


# =========================================================
# بررسی عضویت در کانال
# =========================================================

async def is_member(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> bool:

    channel = load_required_channel()

    if not channel:
        return True

    try:
        member = await context.bot.get_chat_member(
            chat_id=channel,
            user_id=user_id,
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
        )

    except TelegramError:
        return False


async def check_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user_id = update.effective_user.id

    if await is_member(context, user_id):
        return True

    channel = load_required_channel()

    if not channel:
        return True

    channel_username = channel.lstrip("@")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "عضویت در کانال 🐾",
                url=f"https://t.me/{channel_username}",
            )
        ],
        [
            InlineKeyboardButton(
                "عضو شدم ✅",
                callback_data="check_join",
            )
        ],
    ])

    text = (
        "اول عضو کانال اسپانسر شو 😺🐾\n\n"
"بعد «عضو شدم ✅» رو بزن تا شروع کنیم 🎧"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=keyboard,
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=keyboard,
        )

    return False


# =========================================================
# کیبورد لغو
# =========================================================

def cancel_keyboard():
    """کیبوردی که فقط هنگام دریافت زمان نمایش داده می‌شود."""

    return ReplyKeyboardMarkup(
        [[CANCEL_BUTTON]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="زمان را وارد کن...",
    )


def remove_keyboard():
    """حذف کیبورد لغو."""

    return ReplyKeyboardRemove()


# =========================================================
# توابع زمان
# =========================================================

def normalize_digits(text: str) -> str:
    """تبدیل اعداد فارسی و عربی به انگلیسی."""

    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    english = "0123456789"

    trans = str.maketrans(
        persian + arabic,
        english + english,
    )

    return text.translate(trans).strip()


def time_to_seconds(time_text: str):
    """تبدیل زمان به ثانیه."""

    time_text = normalize_digits(time_text)

    if not time_text:
        return None

    # فقط عدد
    if time_text.isdigit():
        return int(time_text)

    parts = time_text.split(":")

    try:
        parts = [int(x) for x in parts]
    except ValueError:
        return None

    # MM:SS
    if len(parts) == 2:
        minutes, seconds = parts

        if minutes < 0 or seconds < 0:
            return None

        if seconds >= 60:
            return None

        return minutes * 60 + seconds

    # HH:MM:SS
    if len(parts) == 3:
        hours, minutes, seconds = parts

        if hours < 0 or minutes < 0 or seconds < 0:
            return None

        if minutes >= 60 or seconds >= 60:
            return None

        return hours * 3600 + minutes * 60 + seconds

    return None


def seconds_to_time(seconds: float) -> str:
    """تبدیل ثانیه به فرمت خوانا."""

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def get_audio_duration(file_path: str):
    """گرفتن مدت فایل صوتی با ffprobe."""

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        return float(result.stdout.strip())

    except Exception:
        return None


# =========================================================
# خوش‌آمدگویی
# =========================================================

async def send_welcome(update: Update):

    text = (
        "سلااامم 😺\n\n"
        "من میوفای‌ام؛ دستیار میوزیکی تو 🎧\n\n"
        "🎙 ویس بدی، میوزیک تحویل می‌گیری\n"
        "🎵 موزیک بدی، هرجاشو بخوای می‌بُرم ✂️\n\n"
        "فایلتو بفرست!"
    )

    await update.effective_message.reply_text(text)


# =========================================================
# پاک‌سازی وضعیت کاربر
# =========================================================

def clear_user_state(
    context: ContextTypes.DEFAULT_TYPE,
    delete_input_file: bool = True,
):
    """
    پاک کردن state کاربر.
    اگر فایل ورودی وجود داشته باشد، حذف می‌شود.
    """

    input_file = context.user_data.get("input_file")

    if delete_input_file and input_file:
        try:
            if os.path.exists(input_file):
                os.remove(input_file)
        except Exception:
            pass

    context.user_data.clear()


async def cancel_operation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """لغو عملیات فعلی."""

    clear_user_state(context)

    await update.message.reply_text(
        "عملیات لغو شد\n"
        "هر وقت خواستی دوباره شروع کنیم، آهنگت رو بفرست 🎵",
        reply_markup=remove_keyboard(),
    )


# =========================================================
# دستور Start
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    clear_user_state(context)

    if not await check_membership(update, context):
        return

    await send_welcome(update)


# =========================================================
# دستور Cancel
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /cancel فقط زمانی فعال است که ربات منتظر زمان باشد.
    """

    state = context.user_data.get("state")

    if state not in (
        "waiting_start",
        "waiting_end",
    ):
        # خارج از مرحله زمان هیچ کاری انجام نمی‌دهیم.
        return

    await cancel_operation(update, context)



# =========================================================
# دستور Help
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "میووو 😺🐾\n\n"
        "من میوفای‌ام؛ گربه کوچولوی موزیکیت 🎧\n\n"

        "🎙 ویس بده\n"
        "ویستو به موزیک قابل دانلود تبدیل می‌کنم.\n\n"

        "🎵 موزیک بده\n"
        "هر قسمتی از آهنگ رو که بخوای برات می‌بُرم ✂️\n\n"

        "📌 محدودیت‌های من:\n"
        "• حداکثر طول فایل: ۱۰ دقیقه\n"
        "• حداکثر طول هر برش: ۲ دقیقه\n\n"

        "📢 اسپانسر می‌خوای؟\n"
        "اگه می‌خوای کانالت رو به کاربرای میوفای معرفی کنی، "
        "برای رزرو اسپانسری و تبلیغات بهمون پیام بده:\n"
        "@AD_Dotfar \n\n"

        "🐾 سازنده میوفای:\n"
        "@Dotfar1207\n"
    )

    await update.effective_message.reply_text(text)


# =========================================================
# پنل ادمین
# =========================================================

async def set_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "مثال:\n"
            "/setchannel @channelusername"
        )
        return

    channel = context.args[0].strip()

    if not channel.startswith("@"):
        channel = "@" + channel

    try:
        await context.bot.get_chat(channel)

        save_required_channel(channel)

        await update.message.reply_text(
            f"کانال جوین اجباری با موفقیت تنظیم شد ✅\n\n"
            f"{channel}"
        )

    except TelegramError:
        await update.message.reply_text(
            "نتونستم به این کانال دسترسی پیدا کنم 😿\n\n"
            "مطمئن شو ربات داخل کانال ادمین باشه و "
            "آیدی کانال رو درست وارد کرده باشی."
        )


async def remove_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    remove_required_channel()

    await update.message.reply_text(
        "کانال جوین اجباری حذف شد ✅"
    )


async def show_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    channel = load_required_channel()

    if channel:
        await update.message.reply_text(
            f"کانال فعلی جوین اجباری:\n{channel}"
        )
    else:
        await update.message.reply_text(
            "در حال حاضر هیچ کانال جوین اجباری تنظیم نشده."
        )


# =========================================================
# بررسی دکمه عضویت
# =========================================================

async def check_join_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if await is_member(context, user_id):

        await query.edit_message_text(
            "عضویتت تأیید شد 😺✅"
        )

        await send_welcome(update)

    else:

        await query.answer(
            "هنوز عضویتت تأیید نشده 😿\n"
            "اول عضو کانال شو و دوباره امتحان کن.",
            show_alert=True,
        )


# =========================================================
# هندلر ویس
# =========================================================

async def handle_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not await check_membership(update, context):
        return

    clear_user_state(context)

    message = update.message

    await message.reply_text(
        "ویست رو گرفتم 🎙️\n"
        "دارم تبدیلش می‌کنم، یه لحظه صبر کن..."
    )

    temp_input = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".ogg",
    )
    temp_input.close()

    temp_output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3",
    )
    temp_output.close()

    try:

        telegram_file = await message.voice.get_file()

        await telegram_file.download_to_drive(
            temp_input.name
        )

        duration = get_audio_duration(
            temp_input.name
        )

        if duration is None:
            await send_error(update)
            return

        if duration > 600:

            await message.reply_text(
                f"این ویس {seconds_to_time(duration)} طول داره.\n\n"
                "حداکثر زمانی که می‌تونم پردازش کنم "
                "۱۰ دقیقه‌ست 😿"
            )

            return

        command = [
            "ffmpeg",
            "-y",
            "-i",
            temp_input.name,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            temp_output.name,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("FFmpeg voice error:", result.stderr)
            await send_error(update)
            return

        with open(temp_output.name, "rb") as audio_file:

            await message.reply_audio(
                audio=audio_file,
                title="Converted",
                performer="@music_cutter_bot",
            )

    except Exception as e:

        print("Voice convert error:", e)

        await send_error(update)

    finally:

        for file_path in (
            temp_input.name,
            temp_output.name,
        ):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass


# =========================================================
# هندلر آهنگ
# =========================================================

async def handle_music(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not await check_membership(update, context):
        return

    clear_user_state(context)

    message = update.message

    try:

        if message.audio:

            telegram_file = await message.audio.get_file()

            file_name = (
                message.audio.file_name
                or "music.mp3"
            )

        elif message.document:

            mime = message.document.mime_type or ""

            if not mime.startswith("audio/"):
                return

            telegram_file = await message.document.get_file()

            file_name = (
                message.document.file_name
                or "music.mp3"
            )

        else:
            return

        extension = (
            os.path.splitext(file_name)[1]
            or ".mp3"
        )

        temp_input = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        )
        temp_input.close()

        await telegram_file.download_to_drive(
            temp_input.name
        )

        duration = get_audio_duration(
            temp_input.name
        )

        if duration is None:

            if os.path.exists(temp_input.name):
                os.remove(temp_input.name)

            await send_error(update)
            return

        if duration > 600:

            if os.path.exists(temp_input.name):
                os.remove(temp_input.name)

            await message.reply_text(
                f"این آهنگ {seconds_to_time(duration)} طول داره.\n\n"
                "حداکثر طول فایل ۱۰ دقیقه‌ست 😿\n"
                "یه آهنگ کوتاه‌تر بفرست."
            )

            return

        # ذخیره اطلاعات برای مرحله بعد
        context.user_data["input_file"] = temp_input.name
        context.user_data["duration"] = duration
        context.user_data["state"] = "waiting_start"

        await message.reply_text(
            "میو! آهنگ رسید 😺🎵\n\n"
            f"مدت آهنگ: {seconds_to_time(duration)}\n"
            "بگو از کجا شروع کنم؟ ⏱️\n"
            "مثلاً: 43 یا 00:43\n\n"
            "اگه پشیمون شدی، لغو رو بزن"
            ,
            reply_markup=cancel_keyboard(),
        )

    except Exception as e:

        print("Music receive error:", e)

        # اگر در حین دریافت خطا رخ داد
        input_file = context.user_data.get("input_file")

        if input_file and os.path.exists(input_file):
            try:
                os.remove(input_file)
            except Exception:
                pass

        context.user_data.clear()

        await send_error(update)


# =========================================================
# هندلر زمان
# =========================================================

async def handle_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not await check_membership(update, context):
        return

    state = context.user_data.get("state")

    # =====================================================
    # مهم:
    # خارج از مرحله دریافت زمان، هیچ متن معمولی پردازش نمی‌شود.
    # =====================================================

    if state not in (
        "waiting_start",
        "waiting_end",
    ):
        return

    text = update.message.text.strip()

    # =====================================================
    # دکمه لغو فقط همین‌جا کار می‌کند.
    # =====================================================

    if text == CANCEL_BUTTON:

        await cancel_operation(
            update,
            context,
        )

        return

    # تبدیل زمان
    seconds = time_to_seconds(text)

    if seconds is None:

        await update.message.reply_text(
            "میو؟ این زمانو نفهمیدم 😿\n\n"
            "اینطوری برام بفرست:\n"
            "43 یا 00:43 یا 01:20 ⏱️"

        )

        return

    duration = context.user_data.get("duration")

    if duration is None:
        clear_user_state(context)

        await update.message.reply_text(
            "اطلاعات آهنگ پیدا نشد 😿\n"
            "لطفاً دوباره آهنگت رو بفرست.",
            reply_markup=remove_keyboard(),
        )

        return

    # =====================================================
    # زمان شروع
    # =====================================================

    if state == "waiting_start":

        if seconds >= duration:

            await update.message.reply_text(
                "زمان شروع نمی‌تونه برابر یا بیشتر از "
                "مدت آهنگ باشه 😿\n\n"
                f"مدت آهنگ: {seconds_to_time(duration)}\n"
                "یه زمان کوتاه‌تر وارد کن."
            )

            return

        context.user_data["start"] = seconds
        context.user_data["state"] = "waiting_end"

        await update.message.reply_text(
            f"شروع رو روی {seconds_to_time(seconds)} گذاشتم ✅\n\n"
            "حالا بگو برش تا چه زمانی ادامه داشته باشه؟ ⏱️\n"
            "مثلاً اگر می‌خوای تا دقیقه ۱:۲۰ ادامه داشته باشه، "
            "بنویس:\n"
            "01:20\n\n"
            "حداکثر طول برش ۲ دقیقه است",
            reply_markup=cancel_keyboard(),
        )

        return

    # =====================================================
    # زمان پایان
    # =====================================================

    start = context.user_data.get("start")

    if start is None:

        clear_user_state(context)

        await update.message.reply_text(
            "زمان شروع پیدا نشد 😿\n"
            "لطفاً دوباره آهنگت رو بفرست.",
            reply_markup=remove_keyboard(),
        )

        return

    if seconds > duration:

        await update.message.reply_text(
            "زمان پایان از مدت آهنگ بیشتره 😿\n\n"
            f"مدت آهنگ: {seconds_to_time(duration)}\n"
            "یه زمان کوتاه‌تر وارد کن."
        )

        return

    if seconds <= start:

        await update.message.reply_text(
            "زمان پایان باید بعد از زمان شروع باشه 😺\n\n"
            f"شروع فعلی: {seconds_to_time(start)}\n"
            "یه زمان پایان درست وارد کن."
        )

        return

    cut_duration = seconds - start

    if cut_duration > 120:

        await update.message.reply_text(
            f"این برش {seconds_to_time(cut_duration)} میشه 😿\n\n"
            "حداکثر طول هر برش ۲ دقیقه است.\n"
            "زمان پایان رو کمی نزدیک‌تر به زمان شروع انتخاب کن."
        )

        return

    # =====================================================
    # شروع برش
    # =====================================================

    await update.message.reply_text(
        "همه‌چی آماده‌ست 🎧✂️\n"
        "دارم قسمت انتخابی رو برش می‌زنم...\n\n"
        "یه لحظه صبر کن 😺",
        reply_markup=remove_keyboard(),
    )

    input_file = context.user_data.get("input_file")

    if not input_file or not os.path.exists(input_file):

        clear_user_state(context)

        await update.message.reply_text(
            "فایل آهنگ دیگه در دسترسم نیست 😿\n"
            "لطفاً دوباره آهنگ رو بفرست."
        )

        return

    output_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".ogg",
    ).name

    try:

        command = [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-ss",
            str(start),
            "-to",
            str(seconds),
            "-vn",
            "-c:a",
            "libopus",
            "-b:a",
            "96k",
            output_file,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:

            print(
                "FFmpeg cut error:",
                result.stderr,
            )

            await send_error(update)
            return

        with open(output_file, "rb") as voice_file:

            await update.message.reply_voice(
                voice=voice_file
            )

    except Exception as e:

        print("Cut error:", e)

        await send_error(update)

    finally:

        for file_path in (
            input_file,
            output_file,
        ):

            try:

                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

            except Exception:
                pass

        context.user_data.clear()


# =========================================================
# اجرای ربات
# =========================================================

def main():

    token = os.getenv("BOT_TOKEN")

    if not token:
        print("❌ BOT_TOKEN پیدا نشد!")
        return

    if ADMIN_ID == 0:
        print("⚠️ ADMIN_ID تنظیم نشده!")

    app = (
        Application.builder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    # =====================================================
    # دستورات
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # =====================================================
    # پنل ادمین
    # =====================================================

    app.add_handler(
        CommandHandler(
            "setchannel",
            set_channel,
        )
    )

    app.add_handler(
        CommandHandler(
            "removechannel",
            remove_channel,
        )
    )

    app.add_handler(
        CommandHandler(
            "channel",
            show_channel,
        )
    )

    # =====================================================
    # عضویت
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$",
        )
    )

    # =====================================================
    # فایل‌ها
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            handle_voice,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.AUDIO | filters.Document.AUDIO,
            handle_music,
        )
    )

    # =====================================================
    # متن
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_time,
        )
    )

    print("🐈 Meowfy is running...")

    app.run_polling()


# =========================================================
# اجرا
# =========================================================

if __name__ == "__main__":
    main()
