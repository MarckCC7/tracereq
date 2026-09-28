import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

def build_db_uri():
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    return URL.create(
        drivername='mysql+pymysql',
        username=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        database=os.environ.get('DB_NAME', 'tracereq'),
    )

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Inicio de sesión con Google (opcional: sin estas variables solo hay email y contraseña)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # Cookies de sesión: no accesibles desde JS, no enviadas desde otros sitios,
    # y solo por HTTPS cuando corre en Vercel.
    _EN_PRODUCCION = bool(os.environ.get('VERCEL'))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _EN_PRODUCCION
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = _EN_PRODUCCION
    WTF_CSRF_TIME_LIMIT = None  # el token dura lo que dura la sesión

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = build_db_uri()

config = {'development': DevelopmentConfig, 'default': DevelopmentConfig}