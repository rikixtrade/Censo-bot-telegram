import os
from telegram.ext import Application

PORT = int(os.environ.get("PORT", 8443))  # Railway asigna el puerto automáticamente
TOKEN = "TU_TOKEN_DE_TELEGRAM"

async def start(update, context):
    await update.message.reply_text("¡Bot activo!")

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://tudominio.railway.app/{TOKEN}"
    )
