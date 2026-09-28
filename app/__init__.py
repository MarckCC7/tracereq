from flask import Flask, flash, jsonify, redirect, request, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Rutas que se pueden abrir sin haber iniciado sesión
ENDPOINTS_PUBLICOS = {'static', 'auth.login', 'auth.registro', 'auth.google', 'auth.google_callback'}
# Rutas consultadas por fetch() desde el JS: responden 401 en vez de redirigir al login
ENDPOINTS_JSON = {'requerimientos.siguiente_id', 'casos_uso.siguiente_id',
                  'casos_uso.reqs_por_proyecto', 'trazabilidad.grafo_datos'}


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from app.models import Usuario

    @login_manager.user_loader
    def cargar_usuario(user_id):
        return db.session.get(Usuario, int(user_id))

    from app.routes.auth import bp_auth, oauth, registrar_google
    oauth.init_app(app)
    registrar_google(app)

    from app.routes.dashboard import bp_dashboard
    from app.routes.proyectos import bp_proyectos
    from app.routes.requerimientos import bp_reqs
    from app.routes.casos_uso import bp_cu
    from app.routes.trazabilidad import bp_traz
    from app.routes.exportar import bp_export
    app.register_blueprint(bp_auth, url_prefix='/auth')
    app.register_blueprint(bp_dashboard, url_prefix='/dashboard')
    app.register_blueprint(bp_proyectos, url_prefix='/proyectos')
    app.register_blueprint(bp_reqs, url_prefix='/requerimientos')
    app.register_blueprint(bp_cu, url_prefix='/casos-uso')
    app.register_blueprint(bp_traz, url_prefix='/trazabilidad')
    app.register_blueprint(bp_export, url_prefix='/exportar')

    @app.before_request
    def exigir_login():
        if request.endpoint in ENDPOINTS_PUBLICOS or current_user.is_authenticated:
            return None
        if request.endpoint in ENDPOINTS_JSON:
            return jsonify({'error': 'no autenticado'}), 401
        return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))

    @app.errorhandler(CSRFError)
    def csrf_invalido(e):
        flash('La página estaba desactualizada. Vuelve a intentarlo.', 'warning')
        return redirect(url_for('auth.login') if not current_user.is_authenticated else url_for('dashboard.index'))

    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    return app
