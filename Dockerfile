# ۱. سیستم‌عامل پایه پایتون
FROM python:3.11-slim

# ۲. نصب برنامه ابزار صوتی (ffmpeg)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ۳. مشخص کردن پوشه کاری
WORKDIR /app

# ۴. کپی کردن پیش‌نیازها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ۵. کپی کردن تمام فایل‌های پروژه
COPY . .

# ۶. دستور اجرای ربات
CMD ["python", "bot.py"]
