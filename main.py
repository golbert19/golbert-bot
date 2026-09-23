import requests, importlib.util, os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- CONFIG SEGURA - LEE DE VARIABLES DEL VPS ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CF_TOKEN = os.getenv("CF_TOKEN")
ZONE_ID = os.getenv("ZONE_ID")

DOMINIO = "golbertvps.org.pe"
GITHUB_USER = "golbert19"
GITHUB_REPO = "golbert-bot"
GITHUB_BRANCH = "main"
IDS_PERMITIDOS = [7930068210]
# ------------------------------------------------

if not BOT_TOKEN or not CF_TOKEN or not ZONE_ID:
    print("FALTA CONFIGURAR VARIABLES BOT_TOKEN, CF_TOKEN, ZONE_ID")
    exit(1)

HEADERS_CF = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
GITHUB_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/bot/functions"

def load_func(name):
    try:
        url = f"{GITHUB_BASE}/{name}.py"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        path = f"/tmp/gb_{name}.py"
        open(path, "w", encoding="utf-8").write(r.text)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        print(f"Error cargando {name}: {e}")
        return None

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in IDS_PERMITIDOS:
        await update.message.reply_text("No autorizado")
        return
    text = update.message.text or ""
    cmd = text.split()[0].replace("/","").lower().split("@")[0]
    if not cmd:
        return
    mod = load_func(cmd)
    if not mod or not hasattr(mod, "run"):
        await update.message.reply_text(f"Comando /{cmd} no encontrado.\nCrea bot/functions/{cmd}.py en GitHub")
        return
    try:
        await mod.run(update, context, HEADERS_CF, ZONE_ID, DOMINIO)
    except Exception as e:
        await update.message.reply_text(f"Error en {cmd}: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.COMMAND, router))
print("Bot Golbert iniciado - Cargando funciones desde GitHub")
app.run_polling()
