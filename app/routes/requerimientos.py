import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Requerimiento, Proyecto, HistorialCambio, Comentario
from app.utils import now_peru

bp_reqs = Blueprint('requerimientos', __name__)

CATEGORIAS_NF = ['rendimiento', 'seguridad', 'usabilidad', 'confiabilidad', 'mantenibilidad', 'escalabilidad', 'otro']

PREFIJOS_TIPO = {'funcional': 'RF', 'no_funcional': 'RNF'}

def _generar_identificador(proyecto_id, tipo):
    prefijo = PREFIJOS_TIPO[tipo]
    patron = re.compile(rf'^{prefijo}-(\d+)$')
    max_num = 0
    reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id, tipo=tipo).all()
    for r in reqs:
        m = patron.match(r.identificador)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f'{prefijo}-{max_num + 1:03d}'

def _registrar_cambio(req_id, campo, anterior, nuevo, desc=None):
    if str(anterior or '') != str(nuevo or ''):
        db.session.add(HistorialCambio(
            requerimiento_id=req_id, campo_modificado=campo,
            valor_anterior=str(anterior or ''), valor_nuevo=str(nuevo or ''),
            descripcion=desc or f'Campo {campo} modificado'))

@bp_reqs.route('/')
def lista():
    proyecto_id = request.args.get('proyecto_id', type=int)
    estado = request.args.get('estado', '')
    prioridad = request.args.get('prioridad', '')
    tipo = request.args.get('tipo', '')
    categoria = request.args.get('categoria', '')
    busqueda = request.args.get('q', '').strip()
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    query = Requerimiento.query
    if proyecto_id: query = query.filter_by(proyecto_id=proyecto_id)
    if estado:      query = query.filter_by(estado=estado)
    if prioridad:   query = query.filter_by(prioridad=prioridad)
    if tipo:        query = query.filter_by(tipo=tipo)
    if categoria:   query = query.filter_by(categoria=categoria)
    if busqueda:
        query = query.filter(db.or_(Requerimiento.identificador.ilike(f'%{busqueda}%'),
                                    Requerimiento.descripcion.ilike(f'%{busqueda}%')))
    reqs = query.order_by(Requerimiento.identificador).all()
    filtros = {'estado': estado, 'prioridad': prioridad, 'tipo': tipo,
               'categoria': categoria, 'q': busqueda, 'proyecto_id': proyecto_id}
    return render_template('requerimientos/lista.html', reqs=reqs, proyectos=proyectos,
                           proyecto_id=proyecto_id, categorias=CATEGORIAS_NF, filtros=filtros)

@bp_reqs.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    proyecto_id = request.args.get('proyecto_id', type=int)
    if request.method == 'POST':
        proyecto_id = request.form.get('proyecto_id', type=int)
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
    req = Requerimiento.query.get_or_404(id)
    historial = req.historial.order_by(HistorialCambio.fecha.desc()).all()
    comentarios = req.comentarios.order_by(Comentario.fecha_creacion.asc()).all()
    relaciones_orig = req.relaciones_origen.all()
    relaciones_dest = req.relaciones_destino.all()
    return render_template('requerimientos/detalle.html', req=req, historial=historial,
                           comentarios=comentarios, relaciones_orig=relaciones_orig, relaciones_dest=relaciones_dest)

@bp_reqs.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    req = Requerimiento.query.get_or_404(id)
    proyectos = Proyecto.query.all()
    if request.method == 'POST':
        desc_cambio = request.form.get('descripcion_cambio', '').strip() or 'Actualización'
        campos = {'tipo': request.form.get('tipo', ''), 'descripcion': request.form.get('descripcion', '').strip(),
                  'prioridad': request.form.get('prioridad', ''), 'estado': request.form.get('estado', '')}
        for campo, nuevo_val in campos.items():
            _registrar_cambio(req.id, campo, getattr(req, campo), nuevo_val, desc_cambio)
            setattr(req, campo, nuevo_val)
        req.categoria = request.form.get('categoria') if req.tipo == 'no_funcional' else None
        req.fecha_actualizacion = now_peru()
        db.session.commit()
        flash('Requerimiento actualizado.', 'success')
        return redirect(url_for('requerimientos.detalle', id=id))
    return render_template('requerimientos/editar.html', req=req, proyectos=proyectos, categorias=CATEGORIAS_NF)

@bp_reqs.route('/<int:id>/eliminar', methods=['POST'])
def eliminar(id):
    req = Requerimiento.query.get_or_404(id)
    proyecto_id = req.proyecto_id
    ident = req.identificador
    db.session.delete(req)
    db.session.commit()
    flash(f'Requerimiento {ident} eliminado.', 'info')
    return redirect(url_for('proyectos.detalle', id=proyecto_id))

@bp_reqs.route('/<int:id>/comentar', methods=['POST'])
def comentar(id):
    req = Requerimiento.query.get_or_404(id)
    texto = request.form.get('texto', '').strip()
    autor = request.form.get('autor', 'Anónimo').strip() or 'Anónimo'
    if texto:
        db.session.add(Comentario(requerimiento_id=id, texto=texto, autor=autor))
        db.session.commit()
        flash('Comentario agregado.', 'success')
    return redirect(url_for('requerimientos.detalle', id=id))

@bp_reqs.route('/sin-cobertura')
def sin_cobertura():
    proyecto_id = request.args.get('proyecto_id', type=int)
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    query = Requerimiento.query.filter(Requerimiento.tipo == 'funcional', ~Requerimiento.casos_uso.any())
    if proyecto_id:
        query = query.filter_by(proyecto_id=proyecto_id)
    reqs = query.order_by(Requerimiento.identificador).all()
    return render_template('requerimientos/sin_cobertura.html', reqs=reqs, proyectos=proyectos, proyecto_id=proyecto_id)

