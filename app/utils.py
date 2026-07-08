import re
from datetime import datetime, timezone, timedelta

# Peru no observa horario de verano: UTC-5 todo el año.
PERU_TZ = timezone(timedelta(hours=-5))

def now_peru():
    """Hora actual de Peru (UTC-5) como datetime naive."""
    return datetime.now(PERU_TZ).replace(tzinfo=None)

def generar_identificador(identificadores_existentes, prefijo):
    """Siguiente identificador secuencial (PREFIJO-001, PREFIJO-002, ...) dada una lista de identificadores ya usados."""
    patron = re.compile(rf'^{re.escape(prefijo)}-(\d+)$')
    max_num = 0
    for ident in identificadores_existentes:
        m = patron.match(ident)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f'{prefijo}-{max_num + 1:03d}'
