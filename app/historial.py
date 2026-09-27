"""Registro de historial compartido por requerimientos y casos de uso.

Todas las rutas que modifican algo visible de un requerimiento o caso de uso
(campos, comentarios, relaciones de trazabilidad, asociaciones entre ellos,
eliminaciones) pasan por aqui, para que el historial no dependa de que cada
ruta se acuerde de escribirlo a mano.
"""
from app import db
from app.models import HistorialCambio, HistorialCasoUso

_MAX_DESC = 255  # largo de la columna `descripcion`


def _texto(valor):
    return str(valor if valor is not None else '')


def registrar_req(req_id, campo, anterior, nuevo, desc=None, forzar=False):
    """Agrega una entrada al historial de un requerimiento.

    Solo registra si el valor cambio, salvo `forzar` (eventos como un
    comentario nuevo, donde no hay "valor anterior" que comparar).
    """
    if not forzar and _texto(anterior) == _texto(nuevo):
        return
    db.session.add(HistorialCambio(
        requerimiento_id=req_id, campo_modificado=campo,
        valor_anterior=_texto(anterior), valor_nuevo=_texto(nuevo),
        descripcion=(desc or f'Campo {campo} modificado')[:_MAX_DESC]))


def registrar_cu(cu_id, campo, anterior, nuevo, desc=None, forzar=False):
    """Agrega una entrada al historial de un caso de uso."""
    if not forzar and _texto(anterior) == _texto(nuevo):
        return
    db.session.add(HistorialCasoUso(
        caso_uso_id=cu_id, campo_modificado=campo,
        valor_anterior=_texto(anterior), valor_nuevo=_texto(nuevo),
        descripcion=(desc or f'Campo {campo} modificado')[:_MAX_DESC]))
