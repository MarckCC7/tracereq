import os
import sys

# Permite importar el paquete `app` y `config` desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Los proveedores entregan la URL como mysql://, postgres:// o postgresql://;
# SQLAlchemy necesita el driver explícito.
_url = os.environ.get('DATABASE_URL', '').strip()
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


@app.errorhandler(OperationalError)
@app.errorhandler(ProgrammingError)
def _error_bd(e):
    print(f'[TraceReq] Error de base de datos: {e!r}', file=sys.stderr)
    return _pagina_error('No se pudo conectar a la base de datos',
                         'Revisa <code>DATABASE_URL</code> (usuario, clave, host, puerto y nombre de la base), '
                         'que la base acepte conexiones externas y, si tu proveedor exige SSL, '
                         'agrega la variable <code>DB_SSL=true</code>. El detalle está en los logs de Vercel.')
