import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / 'resumes'
UPLOAD_DIR.mkdir(exist_ok=True)
CHROMA_DIR = DATA_DIR / 'chroma_db'


def _resolve_project_path(name: str):
    value = os.getenv(name)
    if not value:
        return
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    os.environ[name] = str(path.resolve())


# Resolve project-owned caches from this checkout so a moved project folder
# does not keep using absolute paths from its previous location.
_resolve_project_path('DOCKER_CONFIG')
_resolve_project_path('HF_HOME')

DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://interviewace:interviewace@127.0.0.1:3306/interviewace')
if not DATABASE_URL.startswith('mysql+pymysql://') and os.getenv('INTERVIEWACE_TESTING') != '1':
    raise RuntimeError('InterviewAce requires MySQL. Set DATABASE_URL in .env (see .env.example). SQLite is allowed only in automated tests.')
JWT_SECRET = os.getenv('JWT_SECRET', 'local-development-only-change-before-sharing')
if len(JWT_SECRET) < 32 or JWT_SECRET.startswith(('local-development', 'REPLACE_')):
    raise RuntimeError('Set a private random JWT_SECRET of at least 32 characters in .env.')
SESSION_COOKIE = 'interviewace_session'
SESSION_SECONDS = int(os.getenv('SESSION_HOURS', '8')) * 3600
SESSION_IDLE_SECONDS = int(os.getenv('SESSION_IDLE_MINUTES', '30')) * 60
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
TRUSTED_HOSTS = [host.strip() for host in os.getenv('TRUSTED_HOSTS', '127.0.0.1,localhost,testserver').split(',')]
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
CHAT_MODEL = os.getenv('CHAT_MODEL', 'qwen2.5:1.5b')
EMBED_MODEL = os.getenv('EMBED_MODEL', 'nomic-embed-text')
