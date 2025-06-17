from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configurar el logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciales de Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'
credentials = None
spreadsheet_id = 'YOUR_SPREADSHEET_ID'
range_name = 'Sheet1!A:B'

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Bienvenido! Por favor, envíame tu número de cédula.')

def save_cedula(update: Update, context: CallbackContext):
    cedula = update.message.text
    update.message.reply_text(f'Tu número de cédula es: {cedula}. ¿Es correcto? (Si/No)')
    context.user_data['cedula'] = cedula

def confirm(update: Update, context: CallbackContext):
    if update.message.text.lower() == 'si':
        creds = None
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        values = [[context.user_data['cedula']]]
        body = {'values': values}
        result = service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='USER_ENTERED', body=body).execute()
        update.message.reply_text('Número de cédula guardado correctamente.')
    else:
        update.message.reply_text('Por favor, envíame tu número de cédula nuevamente.')

def main():
    global credentials
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    updater = Updater("YOUR_BOT_TOKEN", use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, save_cedula))
    dp.add_handler(MessageHandler(Filters.regex('^(Si|No)$'), confirm))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
