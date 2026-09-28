from flask import Blueprint, render_template
from app import db
from flask_login import current_user
from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad, HistorialCambio
from app.permisos import mis_proyectos, mis_requerimientos, mis_casos_uso, mis_relaciones
from sqlalchemy import func

bp_dashboard = Blueprint('dashboard', __name__)

@bp_dashboard.route('/')
def index():
    total_reqs = mis_requerimientos().count()
    total_cu = mis_casos_uso().count()
    total_proyectos = mis_proyectos().count()
    total_relaciones = mis_relaciones().count()
    reqs_sin_cu = mis_requerimientos().filter(
        Requerimiento.tipo == 'funcional', ~Requerimiento.casos_uso.any()).count()
    contradicciones = mis_relaciones().filter(Trazabilidad.tipo_relacion == 'contradice').count()
    estados = dict(mis_requerimientos().with_entities(Requerimiento.estado, func.count(Requerimiento.id))
                   .group_by(Requerimiento.estado).all())
    prioridades = dict(mis_requerimientos().with_entities(Requerimiento.prioridad, func.count(Requerimiento.id))
                       .group_by(Requerimiento.prioridad).all())
    reqs_funcionales = mis_requerimientos().filter(Requerimiento.tipo == 'funcional').count()
    cobertura_pct = round((reqs_funcionales - reqs_sin_cu) / reqs_funcionales * 100, 1) if reqs_funcionales else 0
    cu_con_reqs = mis_casos_uso().filter(CasoUso.requerimientos.any()).count()
    ultimo_proyecto = mis_proyectos().order_by(Proyecto.fecha_creacion.desc()).first()
    actividad = HistorialCambio.query         .join(Requerimiento, HistorialCambio.requerimiento_id == Requerimiento.id)         .join(Proyecto, Requerimiento.proyecto_id == Proyecto.id)         .filter(Proyecto.usuario_id == current_user.id)         .order_by(HistorialCambio.fecha.desc()).limit(6).all()
    return render_template('dashboard.html', total_reqs=total_reqs,
                           total_cu=total_cu, total_proyectos=total_proyectos, total_relaciones=total_relaciones,
                           reqs_sin_cu=reqs_sin_cu, contradicciones=contradicciones, estados=estados,
                           prioridades=prioridades, cobertura_pct=cobertura_pct,
                           reqs_funcionales=reqs_funcionales, cu_con_reqs=cu_con_reqs,
                           ultimo_proyecto=ultimo_proyecto, actividad=actividad)
