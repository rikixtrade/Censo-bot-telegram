import os
import logging
import re
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext
)
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# Configuración básica de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados del flujo
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

# Configuración de Google Sheets CORREGIDA
def setup_sheets():
    try:
        creds_json = os.getenv("GOOGLE_CREDS")
        if not creds_json:
            raise ValueError("Faltan credenciales de Google Sheets")
            
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Registros_Censo").sheet1
    except Exception as e:
        logger.error(f"Error crítico al configurar Sheets: {str(e)}")
        return None

sheet = setup_sheets()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📋 Bienvenido al Censo Bot\n"
        "Usa /registro para comenzar."
    )

def registro(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text("🔹 Nombre completo:")
    return NOMBRE

# [...] (Añade aquí el resto de tus handlers)

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("Falta TELEGRAM_TOKEN")
        return

    # CORRECCIÓN DEL UPDATER (versión 20.x)
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', registro)],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
            CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, cedula)],
            DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, direccion)],
            PLANILLA: [MessageHandler(filters.DOCUMENT | filters.PHOTO, planilla)],
            NEGOCIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, negocio)],
            ACTIVIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, actividad)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('start', start))
    
    # Modo Railway
    if "RAILWAY_ENVIRONMENT" in os.environ:
        PORT = os.getenv("PORT", "8443")
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url=f"https://{os.getenv('RAILWAY_PROJECT_NAME')}.railway.app/{TOKEN}"
        )
        logger.info("Bot iniciado en modo Webhook (Railway)")
    else:
        updater.start_polling()
        logger.info("Bot iniciado en modo Polling (Local)")

    updater.idle()

if __name__ == '__main__':
    main()
