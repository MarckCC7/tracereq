from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import CasoUso, Proyecto, Requerimiento
from app.utils import generar_identificador

bp_cu = Blueprint('casos_uso', __name__)

PREFIJO_CU = 'CU'

def _generar_identificador(proyecto_id):
    existentes = [c.identificador for c in CasoUso.query.filter_by(proyecto_id=proyecto_id).all()]
    return generar_identificador(existentes, PREFIJO_CU)

@bp_cu.route('/siguiente-id')
def siguiente_id():
    proyecto_id = request.args.get('proyecto_id', type=int)
    if not proyecto_id:
        return jsonify({'identificador': None})
    return jsonify({'identificador': _generar_identificador(proyecto_id)})

@bp_cu.route('/')
def lista():
    proyecto_id = request.args.get('proyecto_id', type=int)
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    query = CasoUso.query
    if proyecto_id:
        query = query.filter_by(proyecto_id=proyecto_id)
    casos = query.order_by(CasoUso.identificador).all()
    return render_template('casos_uso/lista.html', casos=casos, proyectos=proyectos, proyecto_id=proyecto_id)

@bp_cu.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    proyecto_id = request.args.get('proyecto_id', type=int)
    if request.method == 'POST':
        proyecto_id = request.form.get('proyecto_id', type=int)
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        actor = request.form.get('actor', '').strip()
        req_ids = request.form.getlist('requerimientos', type=int)
        if not proyecto_id or not nombre:
            flash('Proyecto y nombre son obligatorios.', 'danger')
            reqs_proy = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').all() if proyecto_id else []
            return render_template('casos_uso/nuevo.html', proyectos=proyectos,
                                   proyecto_id=proyecto_id, reqs_proy=reqs_proy)
        identificador = _generar_identificador(proyecto_id)
        cu = CasoUso(proyecto_id=proyecto_id, identificador=identificador,
                     nombre=nombre, descripcion=descripcion, actor=actor)
        db.session.add(cu)
        db.session.flush()
        if req_ids:
            reqs = Requerimiento.query.filter(Requerimiento.id.in_(req_ids),
                                              Requerimiento.proyecto_id == proyecto_id).all()
            cu.requerimientos.extend(reqs)
        db.session.commit()
        flash(f'Caso de uso {identificador} creado.', 'success')
        return redirect(url_for('casos_uso.detalle', id=cu.id))
    reqs_proy = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').all() if proyecto_id else []
    return render_template('casos_uso/nuevo.html', proyectos=proyectos,
                           proyecto_id=proyecto_id, reqs_proy=reqs_proy)

@bp_cu.route('/<int:id>')
def detalle(id):
    cu = CasoUso.query.get_or_404(id)
    return render_template('casos_uso/detalle.html', cu=cu)

@bp_cu.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    cu = CasoUso.query.get_or_404(id)
    reqs_proy = Requerimiento.query.filter_by(proyecto_id=cu.proyecto_id, tipo='funcional').all()
    if request.method == 'POST':
        cu.nombre = request.form.get('nombre', '').strip()
        cu.descripcion = request.form.get('descripcion', '').strip()
        cu.actor = request.form.get('actor', '').strip()
        req_ids = request.form.getlist('requerimientos', type=int)
        for r in list(cu.requerimientos):
            cu.requerimientos.remove(r)
        if req_ids:
            reqs = Requerimiento.query.filter(Requerimiento.id.in_(req_ids),
                                              Requerimiento.proyecto_id == cu.proyecto_id).all()
            cu.requerimientos.extend(reqs)
        db.session.commit()
        flash('Caso de uso actualizado.', 'success')
        return redirect(url_for('casos_uso.detalle', id=id))
    return render_template('casos_uso/editar.html', cu=cu, reqs_proy=reqs_proy)

@bp_cu.route('/<int:id>/eliminar', methods=['POST'])
def eliminar(id):
    cu = CasoUso.query.get_or_404(id)
    proyecto_id = cu.proyecto_id
    db.session.delete(cu)
    db.session.commit()
    flash('Caso de uso eliminado.', 'info')
    return redirect(url_for('proyectos.detalle', id=proyecto_id))

@bp_cu.route('/reqs-por-proyecto')
def reqs_por_proyecto():
    from flask import jsonify
    proyecto_id = request.args.get('proyecto_id', type=int)
    reqs = []
    if proyecto_id:
        reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').order_by(Requerimiento.identificador).all()
    return {'reqs': [{'id': r.id, 'identificador': r.identificador, 'descripcion': r.descripcion[:80]} for r in reqs]}
