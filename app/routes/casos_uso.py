from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import CasoUso, Proyecto, Requerimiento, HistorialCasoUso
from app.utils import generar_identificador
from app.historial import registrar_cu, registrar_req
from app.permisos import mis_proyectos, validar_proyecto, mis_casos_uso, caso_uso_propio

bp_cu = Blueprint('casos_uso', __name__)

PREFIJO_CU = 'CU'

def _generar_identificador(proyecto_id):
    existentes = [c.identificador for c in CasoUso.query.filter_by(proyecto_id=proyecto_id).all()]
    return generar_identificador(existentes, PREFIJO_CU)

_registrar_cambio = registrar_cu


def _anotar_asociacion(cu, reqs, asociado, motivo=None):
    """Deja en el historial de cada requerimiento que se (des)asocio al caso de uso."""
    for r in reqs:
        registrar_req(r.id, 'caso de uso', '' if asociado else cu.identificador,
                      cu.identificador if asociado else '',
                      motivo or (f'Asociado al caso de uso {cu.identificador}' if asociado
                                 else f'Desasociado del caso de uso {cu.identificador}'),
                      forzar=True)

@bp_cu.route('/siguiente-id')
def siguiente_id():
    proyecto_id = request.args.get('proyecto_id', type=int)
    if not proyecto_id:
        return jsonify({'identificador': None})
    validar_proyecto(proyecto_id)
    return jsonify({'identificador': _generar_identificador(proyecto_id)})

@bp_cu.route('/')
def lista():
    proyecto_id = validar_proyecto(request.args.get('proyecto_id', type=int))
    proyectos = mis_proyectos().order_by(Proyecto.nombre).all()
    query = mis_casos_uso()
    if proyecto_id:
        query = query.filter(CasoUso.proyecto_id == proyecto_id)
    casos = query.order_by(CasoUso.identificador).all()
    resumen = {'con_reqs': sum(1 for c in casos if c.requerimientos.count()),
               'actores': len({c.actor.strip().lower() for c in casos if c.actor and c.actor.strip()}),
               'proyectos': len({c.proyecto_id for c in casos})}
    return render_template('casos_uso/lista.html', casos=casos, proyectos=proyectos, proyecto_id=proyecto_id,
                           resumen=resumen)

@bp_cu.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    proyectos = mis_proyectos().order_by(Proyecto.nombre).all()
    proyecto_id = validar_proyecto(request.args.get('proyecto_id', type=int))
    if request.method == 'POST':
        proyecto_id = validar_proyecto(request.form.get('proyecto_id', type=int))
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
        registrar_cu(cu.id, 'creacion', '', identificador, 'Caso de uso creado', forzar=True)
        if req_ids:
            reqs = Requerimiento.query.filter(Requerimiento.id.in_(req_ids),
                                              Requerimiento.proyecto_id == proyecto_id).all()
            cu.requerimientos.extend(reqs)
            registrar_cu(cu.id, 'requerimientos asociados', '',
                         ', '.join(sorted(r.identificador for r in reqs)), 'Caso de uso creado')
            _anotar_asociacion(cu, reqs, asociado=True)
        db.session.commit()
        flash(f'Caso de uso {identificador} creado.', 'success')
        return redirect(url_for('casos_uso.detalle', id=cu.id))
    reqs_proy = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').all() if proyecto_id else []
    return render_template('casos_uso/nuevo.html', proyectos=proyectos,
                           proyecto_id=proyecto_id, reqs_proy=reqs_proy)

@bp_cu.route('/<int:id>')
def detalle(id):
    cu = caso_uso_propio(id)
    historial = cu.historial.order_by(HistorialCasoUso.fecha.desc()).all()
    return render_template('casos_uso/detalle.html', cu=cu, historial=historial)

@bp_cu.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    cu = caso_uso_propio(id)
    reqs_proy = Requerimiento.query.filter_by(proyecto_id=cu.proyecto_id, tipo='funcional').all()
    if request.method == 'POST':
        desc_cambio = request.form.get('descripcion_cambio', '').strip() or 'Actualización'
        campos = {'nombre': request.form.get('nombre', '').strip(),
                  'actor': request.form.get('actor', '').strip(),
                  'descripcion': request.form.get('descripcion', '').strip()}
        for campo, nuevo_val in campos.items():
            _registrar_cambio(cu.id, campo, getattr(cu, campo), nuevo_val, desc_cambio)
            setattr(cu, campo, nuevo_val)

        reqs_previos = list(cu.requerimientos)
        anteriores = sorted(r.identificador for r in reqs_previos)
        req_ids = request.form.getlist('requerimientos', type=int)
        for r in reqs_previos:
            cu.requerimientos.remove(r)
        reqs_nuevos = []
        if req_ids:
            reqs_nuevos = Requerimiento.query.filter(Requerimiento.id.in_(req_ids),
                                                      Requerimiento.proyecto_id == cu.proyecto_id).all()
            cu.requerimientos.extend(reqs_nuevos)
        nuevos = sorted(r.identificador for r in reqs_nuevos)
        _registrar_cambio(cu.id, 'requerimientos asociados', ', '.join(anteriores), ', '.join(nuevos), desc_cambio)
        # El cambio tambien se ve desde cada requerimiento afectado, no solo
        # desde el caso de uso.
        ids_previos, ids_nuevos = {r.id for r in reqs_previos}, {r.id for r in reqs_nuevos}
        _anotar_asociacion(cu, [r for r in reqs_nuevos if r.id not in ids_previos], asociado=True)
        _anotar_asociacion(cu, [r for r in reqs_previos if r.id not in ids_nuevos], asociado=False)

        db.session.commit()
        flash('Caso de uso actualizado.', 'success')
        return redirect(url_for('casos_uso.detalle', id=id))
    return render_template('casos_uso/editar.html', cu=cu, reqs_proy=reqs_proy)

@bp_cu.route('/<int:id>/eliminar', methods=['POST'])
def eliminar(id):
    cu = caso_uso_propio(id)
    proyecto_id = cu.proyecto_id
    _anotar_asociacion(cu, list(cu.requerimientos), asociado=False,
                       motivo=f'Se eliminó el caso de uso {cu.identificador}')
    db.session.delete(cu)
    db.session.commit()
    flash('Caso de uso eliminado.', 'info')
    return redirect(url_for('proyectos.detalle', id=proyecto_id))

@bp_cu.route('/reqs-por-proyecto')
def reqs_por_proyecto():
    proyecto_id = validar_proyecto(request.args.get('proyecto_id', type=int))
    reqs = []
    if proyecto_id:
        reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').order_by(Requerimiento.identificador).all()
    return {'reqs': [{'id': r.id, 'identificador': r.identificador, 'descripcion': r.descripcion[:80]} for r in reqs]}
