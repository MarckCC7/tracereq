from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Requerimiento, Proyecto, HistorialCambio, Comentario
from app.utils import now_peru, generar_identificador
from flask_login import current_user
from app.historial import registrar_req, registrar_cu
from app.permisos import mis_proyectos, validar_proyecto, mis_requerimientos, requerimiento_propio

bp_reqs = Blueprint('requerimientos', __name__)

CATEGORIAS_NF = ['rendimiento', 'seguridad', 'usabilidad', 'confiabilidad', 'mantenibilidad', 'escalabilidad', 'otro']

PREFIJOS_TIPO = {'funcional': 'RF', 'no_funcional': 'RNF'}

# Ordenamientos disponibles en el listado (clave -> columnas)
ORDENES = {
    'id':        (Requerimiento.identificador,),
    'id_desc':   (Requerimiento.identificador.desc(),),
    'prioridad': (db.case({'alta': 0, 'media': 1, 'baja': 2}, value=Requerimiento.prioridad), Requerimiento.identificador),
    'estado':    (Requerimiento.estado, Requerimiento.identificador),
    'recientes': (Requerimiento.fecha_actualizacion.desc(),),
}

def _generar_identificador(proyecto_id, tipo):
    # Se miran TODOS los identificadores del proyecto, no solo los del mismo
    # tipo: si un requerimiento quedo con un prefijo que no corresponde a su
    # tipo (p. ej. un RNF-010 marcado como funcional), filtrar por tipo lo
    # ignoraba, se volvia a generar RNF-010 y el guardado fallaba por la
    # restriccion unica. generar_identificador ya filtra por prefijo.
    existentes = [ident for (ident,) in
                  db.session.query(Requerimiento.identificador).filter_by(proyecto_id=proyecto_id)]
    return generar_identificador(existentes, PREFIJOS_TIPO[tipo])

def _prefijo_correcto(identificador, tipo):
    return identificador.startswith(PREFIJOS_TIPO[tipo] + '-')

_registrar_cambio = registrar_req

@bp_reqs.route('/')
def lista():
    proyecto_id = request.args.get('proyecto_id', type=int)
    estado = request.args.get('estado', '')
    prioridad = request.args.get('prioridad', '')
    tipo = request.args.get('tipo', '')
    categoria = request.args.get('categoria', '')
    busqueda = request.args.get('q', '').strip()
    proyectos = mis_proyectos().order_by(Proyecto.nombre).all()
    validar_proyecto(proyecto_id)
    query = mis_requerimientos()
    if proyecto_id: query = query.filter(Requerimiento.proyecto_id == proyecto_id)
    if estado:      query = query.filter(Requerimiento.estado == estado)
    if prioridad:   query = query.filter(Requerimiento.prioridad == prioridad)
    if tipo:        query = query.filter(Requerimiento.tipo == tipo)
    if categoria:   query = query.filter(Requerimiento.categoria == categoria)
    if busqueda:
        query = query.filter(db.or_(Requerimiento.identificador.ilike(f'%{busqueda}%'),
                                    Requerimiento.descripcion.ilike(f'%{busqueda}%')))
    orden = request.args.get('orden', 'id')
    orden_sql = ORDENES.get(orden, ORDENES['id'])
    reqs = query.order_by(*orden_sql).all()
    filtros = {'estado': estado, 'prioridad': prioridad, 'tipo': tipo,
               'categoria': categoria, 'q': busqueda, 'proyecto_id': proyecto_id, 'orden': orden}
    return render_template('requerimientos/lista.html', reqs=reqs, proyectos=proyectos,
                           proyecto_id=proyecto_id, categorias=CATEGORIAS_NF, filtros=filtros)

@bp_reqs.route('/siguiente-id')
def siguiente_id():
    proyecto_id = request.args.get('proyecto_id', type=int)
    tipo = request.args.get('tipo', '')
    if not proyecto_id or tipo not in PREFIJOS_TIPO:
        return jsonify({'identificador': None})
    validar_proyecto(proyecto_id)
    return jsonify({'identificador': _generar_identificador(proyecto_id, tipo)})

@bp_reqs.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    proyectos = mis_proyectos().order_by(Proyecto.nombre).all()
    proyecto_id = validar_proyecto(request.args.get('proyecto_id', type=int))
    if request.method == 'POST':
        proyecto_id = validar_proyecto(request.form.get('proyecto_id', type=int))
        tipo = request.form.get('tipo', '')
        descripcion = request.form.get('descripcion', '').strip()
        prioridad = request.form.get('prioridad', 'media')
        estado = request.form.get('estado', 'pendiente')
        categoria = request.form.get('categoria') if tipo == 'no_funcional' else None
        if not proyecto_id or not descripcion or tipo not in ('funcional', 'no_funcional'):
            flash('Todos los campos obligatorios deben completarse.', 'danger')
            return render_template('requerimientos/nuevo.html', proyectos=proyectos,
                                   proyecto_id=proyecto_id, categorias=CATEGORIAS_NF)
        identificador = _generar_identificador(proyecto_id, tipo)
        req = Requerimiento(proyecto_id=proyecto_id, identificador=identificador, tipo=tipo,
                            descripcion=descripcion, prioridad=prioridad, estado=estado, categoria=categoria)
        db.session.add(req)
        db.session.flush()
        db.session.add(HistorialCambio(requerimiento_id=req.id, campo_modificado='creacion',
                                       descripcion='Requerimiento creado', valor_anterior='', valor_nuevo=identificador))
        db.session.commit()
        flash(f'Requerimiento {identificador} creado.', 'success')
        return redirect(url_for('requerimientos.detalle', id=req.id))
    return render_template('requerimientos/nuevo.html', proyectos=proyectos,
                           proyecto_id=proyecto_id, categorias=CATEGORIAS_NF)

@bp_reqs.route('/<int:id>')
def detalle(id):
    req = requerimiento_propio(id)
    historial = req.historial.order_by(HistorialCambio.fecha.desc()).all()
    comentarios = req.comentarios.order_by(Comentario.fecha_creacion.asc()).all()
    relaciones_orig = req.relaciones_origen.all()
    relaciones_dest = req.relaciones_destino.all()
    return render_template('requerimientos/detalle.html', req=req, historial=historial,
                           comentarios=comentarios, relaciones_orig=relaciones_orig, relaciones_dest=relaciones_dest)

@bp_reqs.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    req = requerimiento_propio(id)
    proyectos = mis_proyectos().all()
    if request.method == 'POST':
        desc_cambio = request.form.get('descripcion_cambio', '').strip() or 'Actualización'
        nuevo_tipo = request.form.get('tipo', '')
        if nuevo_tipo not in PREFIJOS_TIPO:
            flash('Tipo de requerimiento inválido.', 'danger')
            return redirect(url_for('requerimientos.editar', id=id))
        nueva_categoria = request.form.get('categoria') if nuevo_tipo == 'no_funcional' else None
        nuevo_identificador = req.identificador
        # Se reasigna al cambiar de tipo (RF-X <-> RNF-X) y tambien si el
        # identificador actual no corresponde a su tipo: asi basta con volver a
        # guardar un requerimiento que quedo desalineado para corregirlo.
        if nuevo_tipo != req.tipo or not _prefijo_correcto(req.identificador, nuevo_tipo):
            nuevo_identificador = _generar_identificador(req.proyecto_id, nuevo_tipo)
        campos = {'tipo': nuevo_tipo, 'identificador': nuevo_identificador,
                  'descripcion': request.form.get('descripcion', '').strip(),
                  'prioridad': request.form.get('prioridad', ''), 'estado': request.form.get('estado', ''),
                  'categoria': nueva_categoria}
        for campo, nuevo_val in campos.items():
            _registrar_cambio(req.id, campo, getattr(req, campo), nuevo_val, desc_cambio)
            setattr(req, campo, nuevo_val)
        req.fecha_actualizacion = now_peru()
        db.session.commit()
        flash('Requerimiento actualizado.', 'success')
        return redirect(url_for('requerimientos.detalle', id=id))
    return render_template('requerimientos/editar.html', req=req, proyectos=proyectos, categorias=CATEGORIAS_NF)

@bp_reqs.route('/<int:id>/eliminar', methods=['POST'])
def eliminar(id):
    req = requerimiento_propio(id)
    proyecto_id = req.proyecto_id
    ident = req.identificador
    # El historial del requerimiento se borra con el, asi que la eliminacion
    # queda anotada en lo que SI sobrevive: los requerimientos relacionados y
    # los casos de uso que lo tenian asociado.
    for rel in req.relaciones_origen.all():
        registrar_req(rel.requerimiento_destino_id, 'relación', f'{ident} {rel.tipo_relacion} (entrante)', '',
                      f'Relación eliminada: se eliminó el requerimiento {ident}')
    for rel in req.relaciones_destino.all():
        registrar_req(rel.requerimiento_origen_id, 'relación', f'{rel.tipo_relacion} {ident}', '',
                      f'Relación eliminada: se eliminó el requerimiento {ident}')
    for cu in req.casos_uso.all():
        registrar_cu(cu.id, 'requerimientos asociados', ident, '',
                     f'Se eliminó el requerimiento {ident}')
    db.session.delete(req)
    db.session.commit()
    flash(f'Requerimiento {ident} eliminado.', 'info')
    return redirect(url_for('proyectos.detalle', id=proyecto_id))

@bp_reqs.route('/<int:id>/comentar', methods=['POST'])
def comentar(id):
    req = requerimiento_propio(id)
    texto = request.form.get('texto', '').strip()
    autor = current_user.nombre[:80]
    if texto:
        db.session.add(Comentario(requerimiento_id=id, texto=texto, autor=autor))
        registrar_req(id, 'comentario', '', texto, f'Comentario agregado por {autor}', forzar=True)
        db.session.commit()
        flash('Comentario agregado.', 'success')
    return redirect(url_for('requerimientos.detalle', id=id))

@bp_reqs.route('/sin-cobertura')
def sin_cobertura():
    proyecto_id = request.args.get('proyecto_id', type=int)
    proyectos = mis_proyectos().order_by(Proyecto.nombre).all()
    validar_proyecto(proyecto_id)
    query = mis_requerimientos().filter(Requerimiento.tipo == 'funcional', ~Requerimiento.casos_uso.any())
    if proyecto_id:
        query = query.filter(Requerimiento.proyecto_id == proyecto_id)
    reqs = query.order_by(Requerimiento.identificador).all()
    return render_template('requerimientos/sin_cobertura.html', reqs=reqs, proyectos=proyectos, proyecto_id=proyecto_id)

