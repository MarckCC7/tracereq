"""Consultas limitadas a los datos del usuario que inició sesión.

Cada usuario solo ve y modifica sus propios proyectos y todo lo que cuelga de
ellos. Las rutas deben obtener los datos por aquí (nunca con Modelo.query
directo) para que un id ajeno en la URL o en un formulario responda 404.
"""
from flask import abort
from flask_login import current_user

from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad


def mis_proyectos():
    return Proyecto.query.filter(Proyecto.usuario_id == current_user.id)


def proyecto_propio(proyecto_id):
    return mis_proyectos().filter(Proyecto.id == proyecto_id).first_or_404()


def validar_proyecto(proyecto_id):
    """Para parámetros opcionales (?proyecto_id=...): None pasa, uno ajeno da 404."""
    if proyecto_id and not mis_proyectos().filter(Proyecto.id == proyecto_id).count():
        abort(404)
    return proyecto_id


def mis_requerimientos():
    return Requerimiento.query.join(Proyecto, Requerimiento.proyecto_id == Proyecto.id) \
        .filter(Proyecto.usuario_id == current_user.id)


def requerimiento_propio(req_id):
    return mis_requerimientos().filter(Requerimiento.id == req_id).first_or_404()


def mis_casos_uso():
    return CasoUso.query.join(Proyecto, CasoUso.proyecto_id == Proyecto.id) \
        .filter(Proyecto.usuario_id == current_user.id)


def caso_uso_propio(cu_id):
    return mis_casos_uso().filter(CasoUso.id == cu_id).first_or_404()


def mis_relaciones():
    return Trazabilidad.query \
        .join(Requerimiento, Trazabilidad.requerimiento_origen_id == Requerimiento.id) \
        .join(Proyecto, Requerimiento.proyecto_id == Proyecto.id) \
        .filter(Proyecto.usuario_id == current_user.id)


def relacion_propia(rel_id):
    return mis_relaciones().filter(Trazabilidad.id == rel_id).first_or_404()
