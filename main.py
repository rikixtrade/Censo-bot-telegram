import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Configuración básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

# Configura Google Sheets
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

    # Configuración simple sin webhook para pruebas
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler('start', start))
    
    logger.info("Iniciando bot en modo polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
