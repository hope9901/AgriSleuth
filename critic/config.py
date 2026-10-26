"""One repository-root .env. Explicit process variables always take precedence."""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

def load_environment():
    load_dotenv(ENV_PATH, override=False)

load_environment()
