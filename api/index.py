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
# Supabase muestra la URL del pooler con ?pgbouncer=true (y otros parámetros solo de Prisma)
# que psycopg2 rechaza: se quitan (el pooler funciona igual sin ellos).
_SOLO_PRISMA = ('pgbouncer=', 'connection_limit=', 'pool_timeout=', 'schema=')
if '?' in _url:
    _base, _query = _url.split('?', 1)
    _query = '&'.join(p for p in _query.split('&') if p and not p.startswith(_SOLO_PRISMA))
    _url = _base + ('?' + _query if _query else '')
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

from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from werkzeug.middleware.proxy_fix import ProxyFix
from app import create_app
from app.esquema import asegurar_esquema

app = create_app('development')
app.config['DEBUG'] = False
# Vercel atiende por HTTPS delante de la app: sin esto, url_for(_external=True)
# generaría http:// y Google rechazaría la URL de retorno del login.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

_db_configurada = bool(os.environ.get('DATABASE_URL') or os.environ.get('DB_HOST'))
# Con la clave por defecto cualquiera podría falsificar una sesión y entrar como otro usuario.
_clave_segura = len(os.environ.get('SECRET_KEY', '')) >= 16 and os.environ.get('SECRET_KEY') != 'dev-key'

if _db_configurada:
    # Crea tablas/columnas nuevas y protege las tablas en Supabase (idempotente).
    try:
        with app.app_context():
            asegurar_esquema()
    except Exception as e:  # la app arranca igual; el detalle queda en los logs
        print(f'[TraceReq] No se pudo preparar la base de datos: {e!r}', file=sys.stderr)


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
    if not _clave_segura:
        return _pagina_error('Falta configurar SECRET_KEY',
                             'Define en Vercel la variable <code>SECRET_KEY</code> con un texto aleatorio '
                             'de al menos 16 caracteres y vuelve a desplegar.')


def _pistas_url():
    """Errores típicos al pegar la URL en Vercel (solo van a los logs)."""
    crudo = _url_original
    pistas = []
    if '[' in crudo or ']' in crudo or 'YOUR-PASSWORD' in crudo:
        pistas.append('la URL todavía tiene [YOUR-PASSWORD] o corchetes')
    if crudo != crudo.strip() or '"' in crudo or "'" in crudo or ' ' in crudo:
        pistas.append('la URL tiene espacios o comillas')
    if 'db.' in crudo and '.supabase.co' in crudo:
        pistas.append('es la Direct connection (IPv6); usa la del pooler')
    if crudo.count('@') > 1:
        pistas.append('la contraseña tiene @')
    return pistas


def _motivo(e):
    """Primera línea del error del driver, sin la contraseña."""
    texto = (str(getattr(e, 'orig', e)).strip().splitlines() or [repr(e)])[0]
    try:
        clave = make_url(os.environ.get('DATABASE_URL', '')).password
        if clave:
            texto = texto.replace(clave, '***')
    except Exception:
        pass
    return texto


@app.errorhandler(OperationalError)
@app.errorhandler(ProgrammingError)
def _error_bd(e):
    # El detalle (servidor, usuario, motivo) solo va a los logs de Vercel, nunca al visitante.
    print(f'[TraceReq] Error de base de datos: {_motivo(e)} | pistas: {_pistas_url()}', file=sys.stderr)
    return _pagina_error('Servicio no disponible por el momento',
                         'No se pudo conectar a la base de datos. Inténtalo de nuevo en unos minutos.')
