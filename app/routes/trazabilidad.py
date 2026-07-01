from flask import Blueprint, render_template, request, redirect, url_for, flash
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
        origen_id = request.form.get('origen_id', type=int)
        destino_id = request.form.get('destino_id', type=int)
        tipo = request.form.get('tipo_relacion', '')
        descripcion = request.form.get('descripcion', '').strip()
        errores = []
        if not origen_id or not destino_id:
            errores.append('Debes seleccionar ambos requerimientos.')
        elif origen_id == destino_id:
            errores.append('Un requerimiento no puede relacionarse consigo mismo.')
        if tipo not in TIPOS:
            errores.append('Tipo de relación inválido.')
        if not errores and Trazabilidad.query.filter_by(
                requerimiento_origen_id=origen_id, requerimiento_destino_id=destino_id).first():
            errores.append('Ya existe una relación entre estos requerimientos.')
        if errores:
            for e in errores: flash(e, 'danger')
        else:
            rel = Trazabilidad(requerimiento_origen_id=origen_id, requerimiento_destino_id=destino_id,
                               tipo_relacion=tipo, descripcion=descripcion)
            db.session.add(rel)
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
        reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id).order_by(Requerimiento.identificador).all()
        casos = CasoUso.query.filter_by(proyecto_id=proyecto_id).order_by(CasoUso.identificador).all()
        for req in reqs:
            matriz_data[req.id] = set(cu.id for cu in req.casos_uso)
        req_ids = [r.id for r in reqs]
        contradicciones = Trazabilidad.query.filter(
            Trazabilidad.tipo_relacion == 'contradice',
            Trazabilidad.requerimiento_origen_id.in_(req_ids)).all()
        relaciones_traz = Trazabilidad.query.filter(
            Trazabilidad.requerimiento_origen_id.in_(req_ids)).all()
    return render_template('trazabilidad/matriz.html', proyectos=proyectos, proyecto_id=proyecto_id,
                           reqs=reqs, casos=casos, matriz_data=matriz_data,
                           contradicciones=contradicciones, relaciones_traz=relaciones_traz)