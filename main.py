import os
import re
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

# Carga variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Estados del flujo
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

# Configuración de Google Sheets
def setup_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(os.getenv("GOOGLE_CREDS"))
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
        "📋 *Bienvenido a @Censo_DataBot*\n"
        "Usa /registro para comenzar el censo.\n\n"
        "⚠️ *Aviso de privacidad*: Los datos proporcionados se almacenarán "
        "en una base de datos segura para fines censales.",
        parse_mode="Markdown"
    )

def registro(update: Update, context):
    # Reiniciar datos de usuario
    context.user_data.clear()
    update.message.reply_text("🔹 Por favor, escribe tu **nombre completo**:")
    return NOMBRE

def nombre(update: Update, context):
    context.user_data['nombre'] = update.message.text
    update.message.reply_text("🔹 Ingresa tu **número de cédula** (6-10 dígitos):")
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
    update.message.reply_text(
        "🔹 Sube la **planilla de servicios básicos** (PDF/imagen):\n"
        "Asegúrate que el código único sea visible."
    )
    return PLANILLA

def planilla(update: Update, context):
    try:
        if update.message.document or update.message.photo:
            file_id = update.message.document.file_id if update.message.document else update.message.photo[-1].file_id
            file = context.bot.get_file(file_id)
            file.download("planilla_temp.pdf")
            
            # Extraer código (simulación - en producción usar PyPDF2 o similar)
            codigo = "COD-" + re.search(r"\d{6}", update.message.caption or "").group(0) if update.message.caption else "NO_ENCONTRADO"
            context.user_data['codigo_planilla'] = codigo
            
            update.message.reply_text(f"✅ Documento recibido. Código asignado: {codigo}\n🔹 Escribe el **nombre del negocio**:")
            return NEGOCIO
        else:
            update.message.reply_text("❌ Por favor, sube un archivo PDF o imagen.")
            return PLANILLA
    except Exception as e:
        logger.error(f"Error al procesar planilla: {e}")
        update.message.reply_text("❌ Error al procesar el documento. Intenta nuevamente.")
        return PLANILLA

def negocio(update: Update, context):
    context.user_data['negocio'] = update.message.text
    update.message.reply_text("🔹 Describe la **actividad económica** (qué venderá):")
    return ACTIVIDAD

def actividad(update: Update, context):
    context.user_data['actividad'] = update.message.text
    
    resumen = (
        "📝 *Resumen de Registro*\n"
        f"▪ Nombre: {context.user_data['nombre']}\n"
        f"▪ Cédula: {context.user_data['cedula']}\n"
        f"▪ Dirección: {context.user_data['direccion']}\n"
        f"▪ Código Planilla: {context.user_data.get('codigo_planilla', 'N/A')}\n"
        f"▪ Negocio: {context.user_data['negocio']}\n"
        f"▪ Actividad: {context.user_data['actividad']}\n\n"
        "¿Los datos son correctos? Responde *Sí* o *No*"
    )
    update.message.reply_text(resumen, parse_mode="Markdown")
    return CONFIRMAR

def confirmar(update: Update, context):
    try:
        if update.message.text.lower() in ['sí', 'si', 's']:
            # Guardar en Google Sheets
            if sheet:
                sheet.append_row([
                    context.user_data['nombre'],
                    context.user_data['cedula'],
                    context.user_data['direccion'],
                    context.user_data.get('codigo_planilla', 'N/A'),
                    context.user_data['negocio'],
                    context.user_data['actividad'],
                    str(update.message.date)  # Fecha de registro
                ])
                update.message.reply_text("✅ *Registro completado*. ¡Gracias por participar!", parse_mode="Markdown")
            else:
                update.message.reply_text("⚠️ Error al guardar los datos. Por favor, inténtalo más tarde.")
        else:
            update.message.reply_text("🔹 Registro cancelado. Usa /registro para comenzar de nuevo.")
    except Exception as e:
        logger.error(f"Error al guardar datos: {e}")
        update.message.reply_text("❌ Error al guardar los datos. Por favor, inténtalo nuevamente.")
    
    return ConversationHandler.END

def cancel(update: Update, context):
    update.message.reply_text('Registro cancelado.')
    return ConversationHandler.END

def error_handler(update: Update, context):
    logger.error(f'Update {update} caused error {context.error}')
    update.message.reply_text('❌ Ocurrió un error inesperado. Por favor, intenta nuevamente.')

def main():
    # Verificar configuración esencial
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_TOKEN en las variables de entorno")
        return
    
    if not sheet:
        logger.error("No se pudo configurar la conexión con Google Sheets")

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
        webhook_url = f"https://{os.getenv('RAILWAY_PROJECT_NAME')}.railway.app/{TOKEN}"
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url=webhook_url
        )
        logger.info(f"Bot iniciado en modo webhook: {webhook_url}")
    else:
        updater.start_polling()
        logger.info("Bot iniciado en modo polling")

    updater.idle()

if __name__ == '__main__':
    main()