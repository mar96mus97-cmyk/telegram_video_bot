import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
import yt_dlp
import asyncio
from concurrent.futures import ThreadPoolExecutor

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنزيل الفيديو باستخدام yt-dlp
def download_video(url):
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            # إذا كان التنسيق مختلفًا، نغيره
            if not video_path.endswith('.mp4'):
                new_path = video_path.rsplit('.', 1)[0] + '.mp4'
                os.rename(video_path, new_path)
                video_path = new_path
            
            return video_path, info.get('title', 'video')
    except Exception as e:
        logger.error(f"خطأ في التنزيل: {e}")
        return None, None

# معالج أمر /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "مرحبًا! 👋\n"
        "أرسل لي رابط فيديو من أي موقع وسأحاول تنزيله لك.\n"
        "المدعوم: YouTube, Twitter, Instagram, TikTok, وغيرها."
    )

# معالج الروابط
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    
    # تحقق إذا كان الرابط
    if not url.startswith(('http://', 'https://')):
        return
    
    # إرسال رسالة انتظار
    wait_msg = await update.message.reply_text("⏳ جاري تنزيل الفيديو...")
    
    # تنزيل الفيديو في خلفية
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        video_path, video_title = await loop.run_in_executor(pool, download_video, url)
    
    if video_path and os.path.exists(video_path):
        try:
            # إرسال الفيديو
            await update.message.reply_video(
                video=open(video_path, 'rb'),
                caption=f"✅ {video_title}"
            )
            await wait_msg.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في إرسال الفيديو: {str(e)}")
        finally:
            # حذف الملف بعد الإرسال
            os.remove(video_path)
    else:
        await wait_msg.edit_text("❌ لم أستطع تنزيل هذا الفيديو. تأكد من الرابط.")

# معالج الأخطاء
async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"حدث خطأ: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")

def main():
    # الحصول على التوكن
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("لم يتم تعيين التوكن!")
        return
    
    # إنشاء مجلد التنزيلات
    os.makedirs('downloads', exist_ok=True)
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء البوت
    logger.info("البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()