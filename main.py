import os
import re
import pandas as pd
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv

# Carga variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Estados del flujo
NOMBRE, CEDULA, DIRECCION, PLANILLA, NEGOCIO, ACTIVIDAD, CONFIRMAR = range(7)

# Inicializar DataFrame global (o conexión a Google Sheets)
try:
    df = pd.read_excel("registros_censo.xlsx")
except FileNotFoundError:
    df = pd.DataFrame(columns=[
        "Nombre", "Cédula", "Dirección", "Código Planilla", 
        "Nombre Negocio", "Actividad Económica"
    ])

def start(update: Update, context):
    update.message.reply_text(
        "📋 *Bienvenido a @Censo_DataBot*\n"
        "Usa /registro para comenzar el censo.",
        parse_mode="Markdown"
    )

def registro(update: Update, context):
    update.message.reply_text("🔹 Por favor, escribe tu **nombre completo**:")
    return NOMBRE

def nombre(update: Update, context):
    context.user_data['nombre'] = update.message.text
    update.message.reply_text("🔹 Ingresa tu **número de cédula**:")
    return CEDULA

def cedula(update: Update, context):
    if not re.match(r'^\d{6,10}$', update.message.text):  # Validar formato
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
        # Descargar archivo (simplificado)
        file_id = update.message.document.file_id if update.message.document else update.message.photo[-1].file_id
        file = context.bot.get_file(file_id)
        file.download("planilla_usuario.pdf")
        
        # Extraer código único (ejemplo: patrón "COD-123ABC")
        codigo = extraer_codigo_planilla("planilla_usuario.pdf")
        if codigo:
            context.user_data['codigo_planilla'] = codigo
            update.message.reply_text(f"✅ Código detectado: {codigo}\n🔹 Escribe el **nombre del negocio**:")
            return NEGOCIO
        else:
            update.message.reply_text("❌ No se encontró un código válido. Sube la planilla nuevamente:")
            return PLANILLA
    else:
        update.message.reply_text("❌ Por favor, sube un archivo PDF o imagen.")
        return PLANILLA

def extraer_codigo_planilla(archivo_path):
    # Simulación: Extraer código de un PDF (requiere PyPDF2 o OCR real)
    with open(archivo_path, "rb") as f:
        texto = f.read().decode("latin-1")  # Solo ejemplo
        codigo = re.search(r"COD-(\w{6})", texto)
        return codigo.group(1) if codigo else "NO_ENCONTRADO"

def negocio(update: Update, context):
    context.user_data['negocio'] = update.message.text
    update.message.reply_text("🔹 Describe la **actividad económica** (qué venderá):")
    return ACTIVIDAD

def actividad(update: Update, context):
    context.user_data['actividad'] = update.message.text
    
    # Mostrar resumen y confirmación
    resumen = (
        "📝 *Resumen de Registro*\n"
        f"▪ Nombre: {context.user_data['nombre']}\n"
        f"▪ Cédula: {context.user_data['cedula']}\n"
        f"▪ Dirección: {context.user_data['direccion']}\n"
        f"▪ Código Planilla: {context.user_data.get('codigo_planilla', 'N/A')}\n"
        f"▪ Negocio: {context.user_data['negocio']}\n"
        f"▪ Actividad: {context.user_data['actividad']}\n\n"
        "¿Los datos son correctos? (Sí/No)"
    )
    update.message.reply_text(resumen, parse_mode="Markdown")
    return CONFIRMAR

def confirmar(update: Update, context):
    if update.message.text.lower() == "sí":
        # Guardar en Excel
        global df
        nuevo_registro = pd.DataFrame([{
            "Nombre": context.user_data['nombre'],
            "Cédula": context.user_data['cedula'],
            "Dirección": context.user_data['direccion'],
            "Código Planilla": context.user_data.get('codigo_planilla', 'N/A'),
            "Nombre Negocio": context.user_data['negocio'],
            "Actividad Económica": context.user_data['actividad']
        }])
        df = pd.concat([df, nuevo_registro], ignore_index=True)
        df.to_excel("registros_censo.xlsx", index=False)
        
        update.message.reply_text("✅ *Registro completado*. ¡Gracias!", parse_mode="Markdown")
    else:
        update.message.reply_text("🔹 Usa /registro para comenzar de nuevo.")
    return ConversationHandler.END

def main():
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
        fallbacks=[]
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