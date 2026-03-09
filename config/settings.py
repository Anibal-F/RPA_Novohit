"""
Configuración general del RPA Novohit.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / ".env.Novohit"
load_dotenv(dotenv_path=env_path)

# URLs
NOVOHIT_URL = os.getenv("NOVOHIT_URL", "https://grupopetroil.novohit.com/ccgen/user_login.php")

# Credenciales
NOVOHIT_USERNAME = os.getenv("NOVOHIT_USERNAME")
NOVOHIT_PASSWORD = os.getenv("NOVOHIT_PASSWORD")

# Selectores del login
NOVOHIT_USER_SELECTOR = os.getenv("NOVOHIT_USER_SELECTOR", "#s_username")
NOVOHIT_PASS_SELECTOR = os.getenv("NOVOHIT_PASS_SELECTOR", "#s_passwd")
NOVOHIT_LOGIN_SELECTOR = os.getenv("NOVOHIT_LOGIN_SELECTOR", "#btn-login")

# Rutas
BASE_DIR = Path(__file__).parent.parent
DATA_INPUT_DIR = BASE_DIR / "data" / "input"
DATA_OUTPUT_DIR = BASE_DIR / "data" / "output"

# Configuración de procesamiento
BATCH_SIZE = 10  # Registros a procesar antes de pausa
DELAY_BETWEEN_OPERATIONS = 1.5  # Segundos entre cada registro (optimizado)
HEADLESS = False  # True para ejecución sin navegador visible

# Configuración de logging
LOG_FILE = DATA_OUTPUT_DIR / "rpa_novohit.log"
