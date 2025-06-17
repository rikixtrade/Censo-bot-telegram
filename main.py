import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
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
        creds_json = json.loads(os.getenv("GOOGLE_CREDS"))
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        return client.open("Registros_Censo").sheet1
    except Exception as e:
        logger.error(f"Error al configurar Sheets: {e}")
        return None

sheet = setup_sheets()

# Handlers del bot (igual que en tu código original)
def start(update: Update, context):
    update.message.reply_text(
        "📋 Bienvenido al Censo Bot\n"
        "Usa /registro para comenzar."
    )

def registro(update: Update, context):
    context.user_data.clear()
    update.message.reply_text("🔹 Nombre completo:")
    return NOMBRE

# ... (Añade aquí las demás funciones como nombre(), cedula(), etc.)

def confirmar(update: Update, context):
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
            update.message.reply_text("✅ Registro completado!")
        except Exception as e:
            logger.error(f"Error al guardar: {e}")
            update.message.reply_text("❌ Error al guardar. Intenta más tarde.")
    else:
        update.message.reply_text("❌ Registro cancelado.")
    return ConversationHandler.END

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("Falta TELEGRAM_TOKEN")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', registro)],
        states={
            NOMBRE: [MessageHandler(Filters.text & ~Filters.command, nombre)],
            CEDULA: [MessageHandler(Filters.text & ~Filters.command, cedula)],
            # ... (añade todos los estados)
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('start', start))

    # Modo Railway o local
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
