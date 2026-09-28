"""Copia todos los datos de la base local (la de .env) a otra base, p. ej. Supabase.

Uso (desde la raíz del proyecto, con el venv activado):
    python scripts/migrar_datos.py "postgresql://postgres.xxxx:CLAVE@aws-0-....pooler.supabase.com:5432/postgres"
o, sin argumento, con la URL en la variable SUPABASE_URL del archivo .env.

Crea las tablas en el destino si no existen. Si el destino ya tiene datos, no hace nada.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func, select, text
from app import create_app, db


def normalizar(url):
    url = url.strip()
    if '?' in url:  # parámetros que solo entiende Prisma
        base, query = url.split('?', 1)
        query = '&'.join(p for p in query.split('&')
                         if p and not p.startswith(('pgbouncer=', 'connection_limit=', 'pool_timeout=', 'schema=')))
        url = base + ('?' + query if query else '')
    for prefijo, driver in (('postgres://', 'postgresql+psycopg2://'),
                            ('postgresql://', 'postgresql+psycopg2://'),
                            ('mysql://', 'mysql+pymysql://')):
        if url.startswith(prefijo):
            url = driver + url[len(prefijo):]
            break
    if url.startswith('postgresql') and 'sslmode=' not in url:
        url += ('&' if '?' in url else '?') + 'sslmode=require'
    return url


def main():
    app = create_app()  # también carga el .env
    url = sys.argv[1] if len(sys.argv) == 2 else os.environ.get('SUPABASE_URL', '')
    if not url:
        sys.exit(__doc__)
    destino = create_engine(normalizar(url))

    with app.app_context():
        origen = db.engine
        tablas = db.metadata.sorted_tables  # ordenadas para respetar las claves foráneas
        db.metadata.create_all(destino)

        with destino.connect() as dst:
            if any(dst.execute(select(func.count()).select_from(t)).scalar() for t in tablas):
                sys.exit('El destino ya tiene datos; no se copió nada.')

        with origen.connect() as src, destino.begin() as dst:
            for t in tablas:
                filas = [dict(f._mapping) for f in src.execute(select(t))]
                if filas:
                    dst.execute(t.insert(), filas)
                print(f'{t.name}: {len(filas)} fila(s)')

            # En PostgreSQL los ids se insertaron a mano: el contador debe continuar desde el máximo.
            if destino.dialect.name == 'postgresql':
                for t in tablas:
                    if 'id' in t.c and t.c.id.autoincrement:
                        dst.execute(text(
                            f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {t.name}), 0) + 1, false)"))
    print('Listo.')


if __name__ == '__main__':
    main()
