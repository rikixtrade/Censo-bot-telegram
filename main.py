import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Configuración básica de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

def setup_sheets():
    try:
        creds_json = os.getenv("GOOGLE_CREDS")
        if not creds_json:
            raise ValueError("No se encontró GOOGLE_CREDS")
            
        creds_info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open("Registros_Censo").sheet1
    except Exception as e:
        logger.error(f"Error en Google Sheets: {str(e)}")
        return None

def start(update: Update, context):
    update.message.reply_text("📋 ¡Bot funcionando correctamente! Usa /registro")

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("Falta TELEGRAM_TOKEN")
        return

    # Configuración con parámetros explícitos
    updater = Updater(
        token=TOKEN,
        use_context=True,
        request_kwargs={
            'read_timeout': 20,
            'connect_timeout': 20
        }
    )
    
    dp = updater.dispatcher
    
    # Elimina cualquier job existente para evitar conflictos
    if updater.job_queue:
        updater.job_queue.stop()
    
    dp.add_handler(CommandHandler('start', start))
    
    logger.info("Iniciando bot...")
    
    # Modo producción (Railway)
    if "RAILWAY_ENVIRONMENT" in os.environ:
        PORT = os.getenv("PORT", "8443")
        webhook_url = f"https://{os.getenv('RAILWAY_PROJECT_NAME')}.railway.app/{TOKEN}"
        
        # Configura webhook explícitamente
        updater.bot.delete_webhook()
        updater.bot.set_webhook(url=webhook_url)
        
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url=webhook_url
        )
        logger.info(f"Webhook configurado en: {webhook_url}")
    else:
        # Modo desarrollo (local)
        updater.start_polling(
            timeout=20,
            clean=True  # Limpia updates pendientes
        )
        logger.info("Modo polling activado")
    
    updater.idle()

if __name__ == '__main__':
    main()
