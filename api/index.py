import os
import sys

# Permite importar el paquete `app` y `config` desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Los proveedores entregan la URL como mysql://, postgres:// o postgresql://;
# SQLAlchemy necesita el driver explícito.
_url_original = os.environ.get('DATABASE_URL', '')  # tal cual se pegó, para diagnosticar
_url = _url_original.strip()
for _prefijo, _driver in (('mysql://', 'mysql+pymysql://'),
                          ('postgres://', 'postgresql+psycopg2://'),
                          ('postgresql://', 'postgresql+psycopg2://')):
    if _url.startswith(_prefijo):
        _url = _driver + _url[len(_prefijo):]
        break
# Supabase (y la mayoría de Postgres en la nube) exige SSL.
if _url.startswith('postgresql') and 'sslmode=' not in _url:
    _url += ('&' if '?' in _url else '?') + 'sslmode=require'
if _url:
    os.environ['DATABASE_URL'] = _url

import config

# En serverless las conexiones se cortan entre invocaciones: se verifican antes de usarlas.
_engine_options = {'pool_pre_ping': True, 'pool_recycle': 280}
# MySQL en la nube (Aiven, TiDB...) suele exigir SSL: activarlo con DB_SSL=true.
if os.environ.get('DB_SSL', '').lower() in ('1', 'true', 'yes') and _url.startswith('mysql'):
    _engine_options['connect_args'] = {'ssl_verify_cert': True, 'ssl_verify_identity': True}
config.Config.SQLALCHEMY_ENGINE_OPTIONS = _engine_options

from markupsafe import escape
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from app import create_app, db

app = create_app('development')
app.config['DEBUG'] = False

_db_configurada = bool(os.environ.get('DATABASE_URL') or os.environ.get('DB_HOST'))

if _db_configurada:
    # Crea las tablas si aún no existen (no toca las que ya están).
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:  # la app arranca igual y muestra el motivo en vez de caerse
        print(f'[TraceReq] No se pudo inicializar la base de datos: {e!r}', file=sys.stderr)


def _pagina_error(titulo, detalle):
    return (f'<!doctype html><meta charset="utf-8"><title>TraceReq</title>'
            f'<div style="font-family:system-ui,sans-serif;max-width:640px;margin:4rem auto;padding:0 1rem;color:#14204a">'
            f'<h1 style="font-size:1.5rem">{titulo}</h1><p style="color:#475569;line-height:1.6">{detalle}</p></div>'), 503


@app.before_request
def _verificar_configuracion():
    if not _db_configurada:
        return _pagina_error('Falta configurar la base de datos',
                             'Define la variable de entorno <code>DATABASE_URL</code> en Vercel '
                             '(Project Settings → Environment Variables) y vuelve a desplegar.')


def _pistas_url():
    """Errores típicos al pegar la URL en Vercel."""
    crudo = _url_original
    pistas = []
    if '[' in crudo or ']' in crudo or 'YOUR-PASSWORD' in crudo:
        pistas.append('La URL todavía tiene <code>[YOUR-PASSWORD]</code> o corchetes: reemplázalos por tu contraseña, sin corchetes.')
    if crudo != crudo.strip() or '"' in crudo or "'" in crudo or ' ' in crudo:
        pistas.append('La URL tiene espacios o comillas: pégala sola, sin comillas.')
    if 'pgbouncer=' in crudo:
        pistas.append('Quita <code>?pgbouncer=true</code> y usa la URL del puerto <b>5432</b> (Session pooler).')
    if 'db.' in crudo and '.supabase.co' in crudo:
        pistas.append('Esa es la <i>Direct connection</i>, que no funciona en Vercel: usa la del <b>Session pooler</b> '
                      '(host <code>...pooler.supabase.com</code>, puerto 5432).')
    if crudo.count('@') > 1:
        pistas.append('Tu contraseña tiene <code>@</code>: cámbiala en Supabase por una solo con letras y números.')
    if not crudo.strip().startswith(('postgres', 'mysql')):
        pistas.append('La URL debe empezar con <code>postgresql://</code>: revisa que la hayas copiado completa.')
    return pistas


def _motivo(e):
    """Primera línea del error del driver, sin la contraseña."""
    texto = str(getattr(e, 'orig', e)).strip().splitlines()[0] if str(getattr(e, 'orig', e)).strip() else repr(e)
    try:
        clave = make_url(os.environ.get('DATABASE_URL', '')).password
        if clave:
            texto = texto.replace(clave, '***')
    except Exception:
        pass
    return escape(texto)


@app.errorhandler(OperationalError)
@app.errorhandler(ProgrammingError)
def _error_bd(e):
    print(f'[TraceReq] Error de base de datos: {e!r}', file=sys.stderr)
    pistas = ''.join(f'<li>{p}</li>' for p in _pistas_url())
    return _pagina_error('No se pudo conectar a la base de datos',
                         f'<b>Motivo:</b> <code>{_motivo(e)}</code>'
                         + (f'<ul style="margin-top:1rem">{pistas}</ul>' if pistas else '')
                         + '<br><br>Corrige <code>DATABASE_URL</code> en Vercel (Settings → Environment Variables) '
                           'y haz <b>Redeploy</b>.')
