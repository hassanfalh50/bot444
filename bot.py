import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot token from BotFather
TOKEN = '6627963661:AAGmFD2TvvuXAzEB1S4q0s70xvCmT-egSUE'
# Your channel ID
CHANNEL_ID = '@aqse3'

# Storage for messages
data = {
    'message': '',
    'message_input': False,
    'timer': None
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("إنشاء رسالة", callback_data='create_message')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('مرحباً في لوحة التحكم الخاصة بالبوت. اختر خياراً:', reply_markup=reply_markup)

async def create_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('يرجى إدخال الرسالة التي تريد نشرها في القناة:')
    data['message_input'] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    if data['message_input'] and not data['message']:
        data['message'] = user_message
        preview_message = f"رسالتك: {data['message']}"
        
        keyboard = [
            [InlineKeyboardButton("إضافة مؤقت", callback_data='add_timer')],
            [InlineKeyboardButton("نشر بدون مؤقت", callback_data='confirm_publish')],
            [InlineKeyboardButton("تعديل", callback_data='edit_message')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"معاينة:\n{preview_message}", reply_markup=reply_markup)
        data['message_input'] = False
    elif data['message_input'] and data['message']:
        try:
            timer = datetime.strptime(user_message, '%Y-%m-%d %H:%M')
            data['timer'] = timer
            await show_preview(update, context)
        except ValueError:
            await update.message.reply_text('تنسيق التاريخ والوقت غير صحيح. يرجى استخدام الصيغة YYYY-MM-DD HH:MM.')
    else:
        await update.message.reply_text('يرجى الضغط على زر "إنشاء رسالة" أولاً.')

async def add_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('يرجى إدخال موعد انتهاء المؤقت (صيغة: YYYY-MM-DD HH:MM):')
    data['message_input'] = True

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    preview_message = f"رسالتك: {data['message']}\n"
    if data['timer']:
        preview_message += f"المؤقت ينتهي في: {data['timer'].strftime('%Y-%m-%d %H:%M')}"
    
    keyboard = [
        [InlineKeyboardButton("نشر", callback_data='confirm_publish')],
        [InlineKeyboardButton("تعديل", callback_data='edit_message')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update, Update):
        await update.message.reply_text(preview_message, reply_markup=reply_markup)
    else:
        await update.edit_message_text(preview_message, reply_markup=reply_markup)

async def confirm_publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if data['message']:
        try:
            message_text = data['message']
            sent_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=message_text)
            
            if data['timer']:
                # Schedule the first update
                context.job_queue.run_once(
                    update_timer, 
                    1, 
                    data={'chat_id': CHANNEL_ID, 'message_id': sent_message.message_id, 'timer': data['timer']}
                )
            
            await query.edit_message_text('تم نشر الرسالة بنجاح في القناة.')
            logger.info(f"تم نشر الرسالة: {data['message']}")
        except Exception as e:
            await query.edit_message_text(f'حدث خطأ أثناء نشر الرسالة: {str(e)}')
            logger.error(f"خطأ في نشر الرسالة: {str(e)}")
        finally:
            data['message'] = ''
            data['timer'] = None
            data['message_input'] = False
    else:
        await query.edit_message_text('لم يتم تحديد رسالة للنشر.')

async def update_timer(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.data['chat_id']
    message_id = job.data['message_id']
    timer = job.data['timer']
    
    now = datetime.now()
    time_left = timer - now
    
    if time_left.total_seconds() <= 0:
        # Timer has expired
        await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        return
    
    days, seconds = time_left.days, time_left.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    keyboard = [[InlineKeyboardButton(f"{days} يوم : {hours} ساعة : {minutes} دقيقة", callback_data='timer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
    
    # Schedule the next update
    context.job_queue.run_once(
        update_timer, 
        60, 
        data={'chat_id': chat_id, 'message_id': message_id, 'timer': timer}
    )

async def edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('يرجى إدخال الرسالة التي تريد نشرها في القناة:')
    data['message'] = ''
    data['timer'] = None
    data['message_input'] = True

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(create_message, pattern='create_message'))
    application.add_handler(CallbackQueryHandler(confirm_publish, pattern='confirm_publish'))
    application.add_handler(CallbackQueryHandler(edit_message, pattern='edit_message'))
    application.add_handler(CallbackQueryHandler(add_timer, pattern='add_timer'))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == '__main__':
    main()
