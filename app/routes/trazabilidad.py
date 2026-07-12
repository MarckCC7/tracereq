from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Trazabilidad, Requerimiento, Proyecto, CasoUso

bp_traz = Blueprint('trazabilidad', __name__)
TIPOS = ['depende_de', 'refina', 'contradice']

@bp_traz.route('/nueva', methods=['GET', 'POST'])
def nueva():
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    proyecto_id = request.args.get('proyecto_id', type=int)
    if request.method == 'POST':
        proyecto_id = request.form.get('proyecto_id', type=int)
        origen_id  = request.form.get('origen_id', type=int)
        destino_id = request.form.get('destino_id', type=int)
        tipo       = request.form.get('tipo_relacion', '')
        descripcion = request.form.get('descripcion', '').strip()
        errores = []
        if not origen_id or not destino_id: errores.append('Debes seleccionar ambos requerimientos.')
        elif origen_id == destino_id: errores.append('Un requerimiento no puede relacionarse consigo mismo.')
        if tipo not in TIPOS: errores.append('Tipo de relación inválido.')
        if not errores and Trazabilidad.query.filter_by(
                requerimiento_origen_id=origen_id, requerimiento_destino_id=destino_id).first():
            errores.append('Ya existe una relación entre estos requerimientos.')
        if errores:
            for e in errores: flash(e, 'danger')
        else:
            db.session.add(Trazabilidad(requerimiento_origen_id=origen_id, requerimiento_destino_id=destino_id,
                                        tipo_relacion=tipo, descripcion=descripcion))
            db.session.commit()
            flash('Relación creada.', 'success')
            return redirect(url_for('trazabilidad.matriz', proyecto_id=proyecto_id))
    reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id).order_by(Requerimiento.identificador).all() if proyecto_id else []
    return render_template('trazabilidad/nueva.html', proyectos=proyectos,
                           proyecto_id=proyecto_id, reqs=reqs, tipos=TIPOS)

@bp_traz.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    rel = Trazabilidad.query.get_or_404(id)
    proyecto_id = rel.origen.proyecto_id
    db.session.delete(rel)
    db.session.commit()
    flash('Relación eliminada.', 'info')
    return redirect(url_for('trazabilidad.matriz', proyecto_id=proyecto_id))

@bp_traz.route('/matriz')
def matriz():
    proyecto_id = request.args.get('proyecto_id', type=int)
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    reqs, casos, matriz_data, contradicciones, relaciones_traz = [], [], {}, [], []
    if proyecto_id:
        # La matriz de cobertura solo aplica a requerimientos funcionales: los casos
        # de uso nunca se asocian a requerimientos no funcionales (ver RF3).
        reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo='funcional').order_by(Requerimiento.identificador).all()
        casos = CasoUso.query.filter_by(proyecto_id=proyecto_id).order_by(CasoUso.identificador).all()
        for req in reqs:
            matriz_data[req.id] = set(cu.id for cu in req.casos_uso)
        # Las relaciones de trazabilidad sí aplican a RF y RNF por igual.
        todos_ids = [r.id for r in Requerimiento.query.filter_by(proyecto_id=proyecto_id).all()]
        contradicciones = Trazabilidad.query.filter(Trazabilidad.tipo_relacion == 'contradice',
                                                     Trazabilidad.requerimiento_origen_id.in_(todos_ids)).all()
        relaciones_traz = Trazabilidad.query.filter(Trazabilidad.requerimiento_origen_id.in_(todos_ids)).all()
    return render_template('trazabilidad/matriz.html', proyectos=proyectos, proyecto_id=proyecto_id,
                           reqs=reqs, casos=casos, matriz_data=matriz_data,
                           contradicciones=contradicciones, relaciones_traz=relaciones_traz)

@bp_traz.route('/grafo')
def grafo():
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    proyecto_id = request.args.get('proyecto_id', type=int)
    return render_template('trazabilidad/grafo.html', proyectos=proyectos, proyecto_id=proyecto_id)

@bp_traz.route('/grafo-datos')
def grafo_datos():
    proyecto_id = request.args.get('proyecto_id', type=int)
    nodes, edges = [], []
    if proyecto_id:
        reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id).all()
        req_ids = [r.id for r in reqs]
        color_tipo = {'funcional': '#1a237e', 'no_funcional': '#1b5e20'}
        for r in reqs:
            nodes.append({'id': r.id, 'label': r.identificador, 'title': r.descripcion[:100],
                          'color': color_tipo.get(r.tipo, '#546e7a'), 'group': r.tipo})
        relaciones = Trazabilidad.query.filter(Trazabilidad.requerimiento_origen_id.in_(req_ids)).all()
        color_rel = {'depende_de': '#1565c0', 'refina': '#1b5e20', 'contradice': '#b71c1c'}
        for rel in relaciones:
            edges.append({'from': rel.requerimiento_origen_id, 'to': rel.requerimiento_destino_id,
                          'label': rel.tipo_relacion.replace('_', ' '),
                          'color': {'color': color_rel.get(rel.tipo_relacion, '#546e7a')},
                          'arrows': 'to', 'dashes': rel.tipo_relacion == 'contradice'})
    return jsonify({'nodes': nodes, 'edges': edges})
