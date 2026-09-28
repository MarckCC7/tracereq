import os
import sys

# Permite importar el paquete `app` y `config` desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

app = create_app('development')
app.config['DEBUG'] = False

# Crea las tablas si aún no existen (no toca las que ya están).
with app.app_context():
    db.create_all()
