from datetime import datetime, timezone, timedelta

# Peru no observa horario de verano: UTC-5 todo el año.
PERU_TZ = timezone(timedelta(hours=-5))

def now_peru():
    """Hora actual de Peru (UTC-5) como datetime naive."""
    return datetime.now(PERU_TZ).replace(tzinfo=None)
