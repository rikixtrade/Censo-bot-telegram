import os
import logging
import re
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# Configura logging
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
            raise ValueError("Variable GOOGLE_CREDS no encontrada")
            
        creds_info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open("Registros_Censo").sheet1
    except Exception as e:
        logger.error(f"Error en Google Sheets: {str(e)}")
        return None

sheet = setup_sheets()

def start(update: Update, context):
    update.message.reply_text(
        "📋 Bienvenido al Censo Bot\n"
        "Usa /registro para comenzar."
    )

def registro(update: Update, context):
    context.user_data.clear()
    update.message.reply_text("🔹 Nombre completo:")
    return NOMBRE

def nombre(update: Update, context):
    context.user_data['nombre'] = update.message.text
    update.message.reply_text("🔹 Ingresa tu cédula (6-10 dígitos):")
    return CEDULA

def cedula(update: Update, context):
    if not re.match(r'^\d{6,10}$', update.message.text):
        update.message.reply_text("❌ Cédula inválida. Ingresa solo números (6-10 dígitos):")
        return CEDULA
    context.user_data['cedula'] = update.message.text
    update.message.reply_text("🔹 Dirección del negocio:")
    return DIRECCION

def direccion(update: Update, context):
    context.user_data['direccion'] = update.message.text
    update.message.reply_text("🔹 Sube la planilla (PDF/imagen):")
    return PLANILLA

def planilla(update: Update, context):
    if update.message.document or update.message.photo:
        update.message.reply_text("✅ Documento recibido. Escribe el código único:")
        return NEGOCIO
    else:
        update.message.reply_text("❌ Por favor, sube un archivo.")
        return PLANILLA

def negocio(update: Update, context):
    context.user_data['codigo_planilla'] = update.message.text
    update.message.reply_text("🔹 Nombre del negocio:")
    return NEGOCIO

def actividad(update: Update, context):
    context.user_data['negocio'] = update.message.text
    update.message.reply_text("🔹 Actividad económica:")
    return ACTIVIDAD

def confirmar(update: Update, context):
    context.user_data['actividad'] = update.message.text
    
    if update.message.text.lower() in ['sí', 'si', 's']:
        try:
            row = [
                context.user_data['nombre'],
                context.user_data['cedula'],
                context.user_data['direccion'],
                context.user_data.get('codigo_planilla', 'N/A'),
                context.user_data['negocio'],
                context.user_data['actividad'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            if sheet:
                sheet.append_row(row)
                update.message.reply_text("✅ Registro completado!")
            else:
                update.message.reply_text("❌ Error al guardar (Sheet no configurado)")
        except Exception as e:
            logger.error(f"Error al guardar: {str(e)}")
            update.message.reply_text("❌ Error al guardar datos")
    else:
        update.message.reply_text("❌ Registro cancelado")
    
    return ConversationHandler.END

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_TOKEN")
        return

    # Versión CORRECTA para python-telegram-bot 13.x
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', registro)],
        states={
            NOMBRE: [MessageHandler(Filters.text, nombre)],
            CEDULA: [MessageHandler(Filters.text, cedula)],
            DIRECCION: [MessageHandler(Filters.text, direccion)],
            PLANILLA: [MessageHandler(Filters.document | Filters.photo, planilla)],
            NEGOCIO: [MessageHandler(Filters.text, negocio)],
            ACTIVIDAD: [MessageHandler(Filters.text, actividad)],
            CONFIRMAR: [MessageHandler(Filters.text, confirmar)],
        },
        fallbacks=[]
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
        logger.info("Modo Webhook activado")
    else:
        updater.start_polling()
        logger.info("Modo Polling activado")

    updater.idle()

if __name__ == '__main__':
    main()
