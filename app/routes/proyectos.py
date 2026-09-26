from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad

bp_proyectos = Blueprint('proyectos', __name__)

@bp_proyectos.route('/')
def lista():
    proyectos = Proyecto.query.order_by(Proyecto.fecha_creacion.desc()).all()
    resumen = {'reqs': Requerimiento.query.count(), 'casos': CasoUso.query.count(),
               'relaciones': Trazabilidad.query.count()}
    return render_template('proyectos/lista.html', proyectos=proyectos, resumen=resumen)

@bp_proyectos.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        if not nombre:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('proyectos/nuevo.html')
        p = Proyecto(nombre=nombre, descripcion=descripcion)
        db.session.add(p)
        db.session.commit()
        flash(f'Proyecto "{nombre}" creado.', 'success')
        return redirect(url_for('proyectos.detalle', id=p.id))
    return render_template('proyectos/nuevo.html')

@bp_proyectos.route('/<int:id>')
def detalle(id):
    p = Proyecto.query.get_or_404(id)
    reqs = Requerimiento.query.filter_by(proyecto_id=id).order_by(Requerimiento.identificador).all()
    casos = CasoUso.query.filter_by(proyecto_id=id).order_by(CasoUso.identificador).all()
    funcionales = [r for r in reqs if r.tipo == 'funcional']
    cubiertos = sum(1 for r in funcionales if r.casos_uso.count())
    req_ids = [r.id for r in reqs]
    relaciones = Trazabilidad.query.filter(Trazabilidad.requerimiento_origen_id.in_(req_ids)).count() if req_ids else 0
    resumen = {'funcionales': len(funcionales), 'cubiertos': cubiertos, 'relaciones': relaciones,
               'cobertura': round(cubiertos / len(funcionales) * 100, 1) if funcionales else 0}
    return render_template('proyectos/detalle.html', proyecto=p, reqs=reqs, casos=casos, resumen=resumen)

@bp_proyectos.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    p = Proyecto.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('proyectos/editar.html', proyecto=p)
        p.nombre = nombre
        p.descripcion = request.form.get('descripcion', '').strip()
        db.session.commit()
        flash('Proyecto actualizado.', 'success')
        return redirect(url_for('proyectos.detalle', id=id))
    return render_template('proyectos/editar.html', proyecto=p)

@bp_proyectos.route('/<int:id>/eliminar', methods=['POST'])
def eliminar(id):
    p = Proyecto.query.get_or_404(id)
    nombre = p.nombre
    db.session.delete(p)
    db.session.commit()
    flash(f'Proyecto "{nombre}" eliminado.', 'info')
    return redirect(url_for('proyectos.lista'))
