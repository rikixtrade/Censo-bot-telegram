import os
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("TOKEN")  # Asegúrate de tener esta variable en Railway
PORT = int(os.getenv("PORT", 8443))

async def start(update, context):
    await update.message.reply_text("¡Bot activo!")

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    
    # Registra el comando /start
    application.add_handler(CommandHandler("start", start))
    
    # Modo webhook (para Railway)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://tudominio.railway.app/{TOKEN}"  # Reemplaza con tu URL
    )
