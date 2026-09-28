"""Deja la base de datos al día al arrancar (idempotente, se puede llamar siempre)."""
from sqlalchemy import inspect, text

from app import db


def asegurar_esquema():
    # Tablas nuevas (p. ej. usuarios). create_all no modifica tablas existentes...
    db.create_all()

    # ...así que las columnas agregadas después se añaden a mano.
    columnas = {c['name'] for c in inspect(db.engine).get_columns('proyectos')}
    if 'usuario_id' not in columnas:
        with db.engine.begin() as con:
            con.execute(text('ALTER TABLE proyectos ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)'))
            con.execute(text('CREATE INDEX ix_proyectos_usuario_id ON proyectos (usuario_id)'))

    # En Supabase, las tablas del esquema public quedan expuestas por su API REST
    # a cualquiera con la clave pública del proyecto. Con RLS activado y sin
    # políticas, esa API no puede leer ni escribir nada; la app no se ve
    # afectada porque se conecta como dueña de las tablas.
    if db.engine.dialect.name == 'postgresql':
        with db.engine.begin() as con:
            for tabla in db.metadata.sorted_tables:
                con.execute(text(f'ALTER TABLE {tabla.name} ENABLE ROW LEVEL SECURITY'))
