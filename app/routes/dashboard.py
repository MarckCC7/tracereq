from flask import Blueprint, render_template
from app import db
from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad
from sqlalchemy import func

bp_dashboard = Blueprint('dashboard', __name__)

@bp_dashboard.route('/')
def index():
    proyectos = Proyecto.query.order_by(Proyecto.fecha_creacion.desc()).all()
    total_reqs = Requerimiento.query.count()
    total_cu = CasoUso.query.count()
    total_proyectos = Proyecto.query.count()
    total_relaciones = Trazabilidad.query.count()
    reqs_sin_cu = Requerimiento.query.filter(
        Requerimiento.tipo == 'funcional', ~Requerimiento.casos_uso.any()).count()
    contradicciones = Trazabilidad.query.filter_by(tipo_relacion='contradice').count()
    estados = db.session.query(Requerimiento.estado, func.count(Requerimiento.id)).group_by(Requerimiento.estado).all()
    prioridades = db.session.query(Requerimiento.prioridad, func.count(Requerimiento.id)).group_by(Requerimiento.prioridad).all()
    tipos = db.session.query(Requerimiento.tipo, func.count(Requerimiento.id)).group_by(Requerimiento.tipo).all()
    reqs_funcionales = Requerimiento.query.filter_by(tipo='funcional').count()
    cobertura_pct = round((reqs_funcionales - reqs_sin_cu) / reqs_funcionales * 100, 1) if reqs_funcionales else 0
    return render_template('dashboard.html', proyectos=proyectos, total_reqs=total_reqs,
                           total_cu=total_cu, total_proyectos=total_proyectos, total_relaciones=total_relaciones,
                           reqs_sin_cu=reqs_sin_cu, contradicciones=contradicciones, estados=estados,
                           prioridades=prioridades, tipos=tipos, cobertura_pct=cobertura_pct,
                           reqs_funcionales=reqs_funcionales)