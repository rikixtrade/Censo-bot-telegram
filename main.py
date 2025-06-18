import os
import logging
from telegram import Update
from telegram.ext import (  # Cambio aquí
    Updater,
    CommandHandler,
    MessageHandler,
    filters,  # Cambiado de Filters a filters
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

# Estados del flujo
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

# Configura Google Sheets
def setup_sheets():
    try:
        creds_json = json.loads(os.getenv("GOOGLE_CREDS"))
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open("Registros_Censo").sheet1
    except Exception as e:
        logger.error(f"Error al configurar Sheets: {e}")
        return None

sheet = setup_sheets()

def start(update: Update, context):
    update.message.reply_text(
        "📋 *Bienvenido a @Censo_DataBot*\n"
        "Usa /registro para comenzar el censo.",
        parse_mode="Markdown"
    )

def registro(update: Update, context):
    context.user_data.clear()
    update.message.reply_text("🔹 Por favor, escribe tu **nombre completo**:")
    return NOMBRE

def nombre(update: Update, context):
    context.user_data['nombre'] = update.message.text
    update.message.reply_text("🔹 Ingresa tu **número de cédula**:")
    return CEDULA

def cedula(update: Update, context):
    if not re.match(r'^\d{6,10}$', update.message.text):
        update.message.reply_text("❌ Cédula inválida. Ingresa solo números (6-10 dígitos):")
        return CEDULA
    context.user_data['cedula'] = update.message.text
    update.message.reply_text("🔹 Escribe la **dirección del negocio**:")
    return DIRECCION

def direccion(update: Update, context):
    context.user_data['direccion'] = update.message.text
    update.message.reply_text("🔹 Sube la **planilla de servicios básicos** (PDF/imagen):")
    return PLANILLA

def planilla(update: Update, context):
    if update.message.document or update.message.photo:
        update.message.reply_text("✅ Documento recibido. Por favor escribe el código único:")
        return NEGOCIO
    else:
        update.message.reply_text("❌ Por favor, sube un archivo PDF o imagen.")
        return PLANILLA

def negocio(update: Update, context):
    context.user_data['codigo_planilla'] = update.message.text
    update.message.reply_text("🔹 Escribe el **nombre del negocio**:")
    return NEGOCIO

def actividad(update: Update, context):
    context.user_data['negocio'] = update.message.text
    update.message.reply_text("🔹 Describe la **actividad económica** (qué venderá):")
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
            sheet.append_row(row)
            update.message.reply_text("✅ *Registro completado*. ¡Gracias!", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error al guardar: {e}")
            update.message.reply_text("❌ Error al guardar los datos. Intenta más tarde.")
    else:
        update.message.reply_text("🔹 Registro cancelado. Usa /registro para comenzar de nuevo.")
    return ConversationHandler.END

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_TOKEN")
        return

    updater = Updater(TOKEN)
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
    else:
        updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
