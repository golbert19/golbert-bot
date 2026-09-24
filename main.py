import requests
import importlib.util
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# --- CONFIGURAR LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CARGAR VARIABLES DEL ENTORNO ---
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8819531441:AAFtc82ROSVnt6taQylLDYpeFwlmCGdFY8Y")
CF_TOKEN = os.getenv("CF_TOKEN", "cfat_nDDCFkURc3Zo46FkM1ROTvFbOBFEhyDVLrqiRmls492440b5")
ZONE_ID = os.getenv("ZONE_ID", "8ae6be4101fd4dc935d65bd34ab23ac7")

DOMINIO = os.getenv("DOMINIO", "golbertvps.org.pe")
GITHUB_USER = os.getenv("GITHUB_USER", "golbert19")
GITHUB_REPO = os.getenv("GITHUB_REPO", "golbert-bot")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# Parsear IDs permitidos
IDS_PERMITIDOS_STR = os.getenv("IDS_PERMITIDOS", "7930068210")
try:
    IDS_PERMITIDOS = [int(id.strip()) for id in IDS_PERMITIDOS_STR.split(",")]
except ValueError:
    logger.error("❌ ERROR: IDS_PERMITIDOS contiene valores no numéricos")
    IDS_PERMITIDOS = [7930068210]

# --- VALIDACIÓN ---
if not BOT_TOKEN or not CF_TOKEN or not ZONE_ID:
    logger.error("❌ FALTA CONFIGURAR VARIABLES BOT_TOKEN, CF_TOKEN, ZONE_ID")
    exit(1)

HEADERS_CF = {
    "Authorization": f"Bearer {CF_TOKEN}",
    "Content-Type": "application/json"
}
GITHUB_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/bot/functions"

# --- DIRECTORIO TEMPORAL ---
TMP_DIR = "/tmp/golbert_bot"
os, exist_ok=True)


def load_func(name):
    """Carga funciones dinámicamente desde GitHub de forma segura"""
    try:
        # Validar nombre: solo letras, números y guiones bajos
        if not all(c.isalnum() or c == "_" for c in name):
            logger.warning(f"⚠️  Nombre de función inválido: {name}")
            return None
        
        if len(name) > 50:
            logger.warning(f"⚠️  Nombre de función demasiado largo: {name}")
            return None
        
        url = f"{GITHUB_BASE}/{name}.py"
        logger.info(f"📥 Descargando función: {url}")
        
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        
        # Guardar en archivo temporal
        path = os.path.join(TMP_DIR, f"{name}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)
        
        # Cargar módulo
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            logger.error(f"❌ No se pudo crear spec para {name}")
            return None
            
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        logger.info(f"✅ Función {name} cargada correctamente")
        return mod
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Función no encontrada en GitHub: {name} (HTTP {e.response.status_code})")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout descargando {name}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Error de conexión descargando {name}")
        return None
    except Exception as e:
        logger.error(f"❌ Error cargando {name}: {type(e).__name__} - {e}")
        return None


async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enruta comandos a funciones dinámicas"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "desconocido"
        
        # Validar permisos
        if user_id not in IDS_PERMITIDOS:
            logger.warning(f"⚠️  Acceso denegado para @{username} (ID: {user_id})")
            await update.message.reply_text(
                "❌ No tienes permiso para usar este bot.\n"
                f"Tu ID: `{user_id}`",
                parse_mode="Markdown"
            )
            return
        
        # Obtener comando
        text = (update.message.text or "").strip()
        if not text.startswith("/"):
            return
        
        parts = text.split()
        cmd_raw = parts[0].replace("/", "").lower().split("@")[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if not cmd_raw or len(cmd_raw) > 50:
            logger.warning(f"⚠️  Comando inválido de @{username}: {cmd_raw}")
            return
        
        logger.info(f"📨 Comando /{cmd_raw} de @{username} (ID: {user_id}) | Args: {args}")
        
        # Cargar función
        mod = load_func(cmd_raw)
        if not mod or not hasattr(mod, "run"):
            await update.message.reply_text(
                f"❌ Comando `/{cmd_raw}` no encontrado.\n\n"
                f"📝 Crea el archivo `bot/functions/{cmd_raw}.py` en GitHub:\n"
                f"`{GITHUB_USER}/{GITHUB_REPO}`"
            )
            return
        
        # Ejecutar función
        await mod.run(
            update=update,
            context=context,
            headers_cf=HEADERS_CF,
            zone_id=ZONE_ID,
            dominio=DOMINIO,
            args=args
        )
        
    except Exception as e:
        logger.error(f"❌ Error en router: {type(e).__name__} - {e}")
        try:
            await update.message.reply_text(
                f"❌ Error interno: `{str(e)[:100]}`",
                parse_mode="Markdown"
            )
        except Exception as send_error:
            logger.error se pudo enviar mensaje de error: {send_error}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Usuario"
    
    if user_id not in IDS_PERMITIDOS:
        await update.message.reply_text("❌ No autorizado")
        return
    
    await update.message.reply_text(
        f"🤖 *Bienvenido {username}*\n\n"
        "Bot Golbert iniciado correctamente\n\n"
        "📋 Comandos disponibles:\n"
        "• `/help` - Ver ayuda\n"
        "• `/status` - Estado del bot\n"
        f"• Tu ID: `{user_id}`",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    user_id = update.effective_user.id
    
    if user_id not in IDS_PERMITIDOS:
        await update.message.reply_text("❌ No autorizado")
        return
    
    await update.message.reply_text(
        "📚 *Ayuda Bot Golbert*\n\n"
        "Este bot carga funciones dinámicamente desde GitHub.\n\n"
        "🔧 *Cómo usar:*\n"
        "1. Crea un archivo en `bot/functions/micomando.py`\n"
        "2. Implementa una función `async def run(update, context, headers_cf, zone_id, dominio, args)`\n"
        "3. Usa `/micomando` en el chat\n\n"
        "📖 *Ejemplo:*\n"
        "```python\n"
        "async def run(update, context, headers_cf, zone_id, dominio, args):\n"
        "    await update.message.reply_text('¡Hola!')\n"
        "```",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    user_id = update.effective_user.id
    
    if user_id not in IDS_PERMITIDOS:
        await update.message.reply_text
        return
    
    status_text = (
        "✅ *Estado del Bot Golbert*\n\n"
        f"🌐 Dominio: `{DOMINIO}`\n"
        f"📦 GitHub: `{GITHUB_USER}/{GITHUB_REPO}`\n"
        f"🌳 Branch: `{GITHUB_BRANCH}`\n"
        f"👥 Usuarios permitidos: {len(IDS_PERMITIDOS)}\n"
        f"📁 Funciones path: `{GITHUB_BASE}`"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ping - Verificar conexión"""
    user_id = update.effective_user.id
    
    if user_id not in IDS_PERMITIDOS:
        await update.message.reply_text("❌ No autorizado")
        return
    
    await update.message.reply_text("🏓 *PONG* - Bot activo y respondiendo")


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /test - Comando de prueba"""
    user_id = update.effective_user.id
    
    if user_id not in IDS_PERMITIDOS:
        await update.message.reply_text("❌ No autorizado")
        return
    
    test_text = (
        "✅ *Test de Configuración*\n\n"
        f"BOT_TOKEN: {'✓' if BOT_TOKEN else '✗'}\n"
        f"CF_TOKEN: {'✓' if CF_TOKEN else '✗'}\n"
        f"ZONE_ID: {'✓' if ZONE_ID else '✗'}\n"
        f"IDS_PERMITIDOS: {IDS_PERMITIDOS}\n"
        f"GITHUB_BASE: `{GITHUB_BASE}`"
    )
    await update.message.reply_text(test_text, parse_mode="Markdown")


def main():
    """Función principal"""
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO BOT GOLBERT")
    logger.info("=" * 60)
    
    logger.info(f"🌐 Dominio: {DOMINIO}")
    logger.info(f"📦 GitHub: {GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}")
    logger.info(f"👥 Usuarios permitidos: {IDS_PERMITIDOS}")
     Funciones path: {GITHUB_BASE}")
    logger.info("=" * 60)
    
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Agregar handlers en orden específico
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/start$"), start))
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/help$"), help_cmd))
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/status$"), status))
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/ping$"), ping))
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/test$"), test))
        app.add_handler(MessageHandler(filters.COMMAND, router))  # Catchall para otros comandos
        
        logger.info("✅ Bot listo - Escuchando comandos...")
        logger.info("=" * 60)
        
        app.run_polling(allowed_updates=['message'])
        
    except Exception as e:
        logger.error(f"❌ Error crítico: {type(e).__name__} - {e}")
        exit(1)


if __name__ == "__main__":
    main()
```

---

## 📄 Archivo `.env` (CREAR EN LA RAÍZ DEL PROYECTO)

```env
# Telegram Bot
BOT_TOKEN=8819531441:AAFtc82ROSVnt6taQylLDYpeFwlmCGdFY8Y

# Cloudflare
CF_TOKEN=cfat_nDDCFkURc3Zo46FkM1ROTvFbOBFEhyDVLrqiRmls492440b5
ZONE_ID=8ae6be4101fd4dc935d65bd34ab23ac7

# Configuración
DOMINIO=golbertvps.org.pe
GITHUB_USER=golbert19
GITHUB_REPO=golbert-bot
GITHUB_BRANCH=main

# IDs permitidos (separados por comas)
IDS_PERMITIDOS=7930068210
```

---

## 📝 `.gitignore`

```gitignore
# Archivos de configuración
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*.sublime-workspace

# Temporal
/tmp/
*.tmp
*.log
```

---

## 📦 `requirements.txt`

```
python-telegram-bot==20.7
python-dotenv==1.0.0
requests==2.31.0
```

---

## 🚀 INSTALACIÓN Y EJECUCIÓN

### **1️⃣ En Linux/Mac**

```bash
# Clonar repositorio
git clone https://github.com/golbert19/golbert-bot.git
cd golbert-bot

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env
cat > .env << EOF
