import re
from urllib.parse import urlsplit

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.models import Usuario

bp_auth = Blueprint('auth', __name__)
oauth = OAuth()

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD = 8


def google_habilitado():
    return bool(current_app.config.get('GOOGLE_CLIENT_ID') and current_app.config.get('GOOGLE_CLIENT_SECRET'))


def registrar_google(app):
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            'google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )


def _destino_seguro(url):
    """Solo rutas internas: evita que ?next= mande a otro sitio."""
    if url and url.startswith('/') and not url.startswith('//') and not urlsplit(url).netloc:
        return url
    return url_for('dashboard.index')


def _entrar(usuario):
    session.clear()  # nueva sesión al autenticarse
    login_user(usuario, remember=True)


@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    siguiente = request.values.get('next', '')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and not usuario.password_hash and usuario.google_id:
            flash('Esta cuenta se creó con Google: usa "Continuar con Google".', 'warning')
        elif usuario and usuario.check_password(password):
            _entrar(usuario)
            return redirect(_destino_seguro(siguiente))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    return render_template('auth/login.html', siguiente=siguiente, google=google_habilitado())


@bp_auth.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    datos = {'nombre': '', 'email': ''}
    if request.method == 'POST':
        datos = {'nombre': request.form.get('nombre', '').strip()[:120],
                 'email': request.form.get('email', '').strip().lower()[:255]}
        password = request.form.get('password', '')
        errores = []
        if not datos['nombre']:
            errores.append('El nombre es obligatorio.')
        if not EMAIL_RE.match(datos['email']):
            errores.append('Ingresa un email válido.')
        if len(password) < MIN_PASSWORD:
            errores.append(f'La contraseña debe tener al menos {MIN_PASSWORD} caracteres.')
        if password != request.form.get('password2', ''):
            errores.append('Las contraseñas no coinciden.')
        if not errores and Usuario.query.filter_by(email=datos['email']).first():
            errores.append('Ya existe una cuenta con ese email. Inicia sesión.')
        if errores:
            for e in errores:
                flash(e, 'danger')
        else:
            usuario = Usuario(nombre=datos['nombre'], email=datos['email'])
            usuario.set_password(password)
            db.session.add(usuario)
            db.session.commit()
            _entrar(usuario)
            flash(f'¡Bienvenido, {usuario.nombre}!', 'success')
            return redirect(url_for('dashboard.index'))
    return render_template('auth/registro.html', datos=datos, google=google_habilitado())


@bp_auth.route('/logout', methods=['POST'])
def logout():
    # Primero se vacía la sesión y después logout_user(): este deja la marca que
    # borra la cookie "recordarme"; al revés, el usuario seguiría logueado.
    session.clear()
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))


@bp_auth.route('/google')
def google():
    if not google_habilitado():
        flash('El inicio de sesión con Google no está configurado.', 'warning')
        return redirect(url_for('auth.login'))
    session['next_tras_google'] = _destino_seguro(request.args.get('next', ''))
    return oauth.google.authorize_redirect(url_for('auth.google_callback', _external=True))


@bp_auth.route('/google/callback')
def google_callback():
    if not google_habilitado():
        return redirect(url_for('auth.login'))
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:  # cancelado por el usuario, estado inválido, etc.
        current_app.logger.warning('Login con Google fallido: %r', e)
        flash('No se pudo iniciar sesión con Google. Inténtalo de nuevo.', 'danger')
        return redirect(url_for('auth.login'))

    info = token.get('userinfo') or {}
    email = (info.get('email') or '').strip().lower()
    if not info.get('sub') or not email or not info.get('email_verified'):
        flash('Tu cuenta de Google no tiene un email verificado.', 'danger')
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.filter_by(google_id=info['sub']).first()
    if not usuario:
        # Si ya existe una cuenta con ese email (creada con contraseña), se vincula:
        # Google garantiza que el email es de quien inició sesión.
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.google_id = info['sub']
            flash('Tu cuenta quedó vinculada a Google.', 'success')
        else:
            usuario = Usuario(nombre=(info.get('name') or email.split('@')[0])[:120],
                              email=email, google_id=info['sub'])
            db.session.add(usuario)
    if info.get('picture'):
        usuario.avatar_url = info['picture'][:500]
    db.session.commit()

    siguiente = session.pop('next_tras_google', None)
    _entrar(usuario)
    return redirect(_destino_seguro(siguiente))
