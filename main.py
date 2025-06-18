import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
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

# Configuración de Google Sheets
def setup_google_sheets():
    try:
        # Obtener credenciales desde variables de entorno
        creds_json = json.loads(os.getenv("GOOGLE_CREDS"))
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Registros_Censo").sheet1
        return sheet
    except Exception as e:
        logger.error(f"Error al configurar Google Sheets: {e}")
        return None

# Inicialización de la hoja de cálculo
sheet = setup_google_sheets()

def start(update: Update, context):
    update.message.reply_text(
        "📋 Bienvenido al Censo Bot\n"
        "Usa /registro para comenzar el proceso de registro.\n\n"
        "⚠️ Aviso de privacidad: Los datos proporcionados "
        "se almacenarán de forma segura para fines censales."
    )

def registro(update: Update, context):
    context.user_data.clear()
    update.message.reply_text("🔹 Por favor, escribe tu nombre completo:")
    return NOMBRE

def nombre(update: Update, context):
    context.user_data['nombre'] = update.message.text
    update.message.reply_text("🔹 Ingresa tu número de cédula (6-10 dígitos):")
    return CEDULA

def cedula(update: Update, context):
    if not update.message.text.isdigit() or len(update.message.text) < 6 or len(update.message.text) > 10:
        update.message.reply_text("❌ Cédula inválida. Ingresa solo números (6-10 dígitos):")
        return CEDULA
    context.user_data['cedula'] = update.message.text
    update.message.reply_text("🔹 Escribe la dirección del negocio:")
    return DIRECCION

def direccion(update: Update, context):
    context.user_data['direccion'] = update.message.text
    update.message.reply_text("🔹 Sube la planilla de servicios básicos (PDF/imagen):")
    return PLANILLA

def planilla(update: Update, context):
    if update.message.document or update.message.photo:
        update.message.reply_text("✅ Documento recibido. Por favor escribe el código único de la planilla:")
        return NEGOCIO
    else:
        update.message.reply_text("❌ Por favor, sube un archivo PDF o imagen.")
        return PLANILLA

def negocio(update: Update, context):
    context.user_data['codigo_planilla'] = update.message.text
    update.message.reply_text("🔹 Escribe el nombre del negocio:")
    return NEGOCIO

def actividad(update: Update, context):
    context.user_data['negocio'] = update.message.text
    update.message.reply_text("🔹 Describe la actividad económica (qué venderá):")
    return ACTIVIDAD

def confirmar(update: Update, context):
    context.user_data['actividad'] = update.message.text
    
    if update.message.text.lower() in ['sí', 'si', 's']:
        try:
            # Guardar en Google Sheets
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
            update.message.reply_text("✅ Registro completado correctamente!")
        except Exception as e:
            logger.error(f"Error al guardar: {e}")
            update.message.reply_text("❌ Error al guardar los datos. Por favor, inténtalo más tarde.")
    else:
        update.message.reply_text("❌ Registro cancelado. Usa /registro para comenzar de nuevo.")
    
    return ConversationHandler.END

def cancel(update: Update, context):
    update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

def error_handler(update: Update, context):
    logger.error(f'Error: {context.error}')
    update.message.reply_text('❌ Ocurrió un error inesperado.')

def main():
    # Cargar variables de entorno
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_TOKEN en las variables de entorno")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', registro)],
        states={
            NOMBRE: [MessageHandler(Filters.text & ~Filters.command, nombre)],
            CEDULA: [MessageHandler(Filters.text & ~Filters.command, cedula)],
            DIRECCION: [MessageHandler(Filters.text & ~Filters.command, direccion)],
            PLANILLA: [MessageHandler(Filters.document | Filters.photo, planilla)],
            NEGOCIO: [MessageHandler(Filters.text & ~Filters.command, negocio)],
            ACTIVIDAD: [MessageHandler(Filters.text & ~Filters.command, actividad)],
            CONFIRMAR: [MessageHandler(Filters.text & ~Filters.command, confirmar)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('start', start))
    dp.add_error_handler(error_handler)
    
    # Modo Railway o local
    if "RAILWAY_ENVIRONMENT" in os.environ:
        PORT = os.getenv("PORT", "8443")
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url=f"https://{os.getenv('RAILWAY_PROJECT_NAME')}.railway.app/{TOKEN}"
        )
        logger.info("Bot iniciado en modo webhook (Railway)")
    else:
        updater.start_polling()
        logger.info("Bot iniciado en modo polling (local)")

    updater.idle()

if __name__ == '__main__':
    main()
