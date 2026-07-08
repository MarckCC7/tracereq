import csv, json, io
from flask import Blueprint, request, Response
from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad, HistorialCambio

bp_export = Blueprint('exportar', __name__)

def _datos(proyecto_id, con_historial=False):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id).order_by(Requerimiento.identificador).all()
    casos = CasoUso.query.filter_by(proyecto_id=proyecto_id).order_by(CasoUso.identificador).all()
    req_ids = [r.id for r in reqs]
    relaciones = Trazabilidad.query.filter(Trazabilidad.requerimiento_origen_id.in_(req_ids)).all() if req_ids else []
    historial = {}
    if con_historial and req_ids:
        cambios = HistorialCambio.query.filter(HistorialCambio.requerimiento_id.in_(req_ids)) \
            .order_by(HistorialCambio.requerimiento_id, HistorialCambio.fecha).all()
        for c in cambios:
            historial.setdefault(c.requerimiento_id, []).append(c)
    return proyecto, reqs, casos, relaciones, historial

@bp_export.route('/csv/<int:proyecto_id>')
def exportar_csv(proyecto_id):
    con_historial = request.args.get('version') == 'historial'
    proyecto, reqs, casos, relaciones, historial = _datos(proyecto_id, con_historial)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['=== REQUERIMIENTOS ==='])
    w.writerow(['ID','Identificador','Tipo','Descripcion','Prioridad','Estado','Categoria','Fecha'])
    for r in reqs:
        w.writerow([r.id, r.identificador, r.tipo, r.descripcion,
                    r.prioridad, r.estado, r.categoria or '', r.fecha_creacion.strftime('%Y-%m-%d')])
    w.writerow([])
    w.writerow(['=== CASOS DE USO ==='])
    w.writerow(['ID','Identificador','Nombre','Actor','Requerimientos'])
    for cu in casos:
        w.writerow([cu.id, cu.identificador, cu.nombre, cu.actor or '',
                    ', '.join(r.identificador for r in cu.requerimientos)])
    w.writerow([])
    w.writerow(['=== MATRIZ (Req x CU) ==='])
    w.writerow(['Requerimiento'] + [cu.identificador for cu in casos])
    for r in reqs:
        ids_cu = set(cu.id for cu in r.casos_uso)
        w.writerow([r.identificador] + ['X' if cu.id in ids_cu else '' for cu in casos])
    w.writerow([])
    w.writerow(['=== RELACIONES ==='])
    w.writerow(['Origen','Tipo','Destino','Descripcion'])
    for rel in relaciones:
        w.writerow([rel.origen.identificador, rel.tipo_relacion, rel.destino.identificador, rel.descripcion or ''])
    if con_historial:
        w.writerow([])
        w.writerow(['=== HISTORIAL DE CAMBIOS ==='])
        w.writerow(['Requerimiento','Fecha','Campo','Valor Anterior','Valor Nuevo','Motivo'])
        for r in reqs:
            for h in historial.get(r.id, []):
                w.writerow([r.identificador, h.fecha.strftime('%Y-%m-%d %H:%M'), h.campo_modificado or '',
                            h.valor_anterior or '', h.valor_nuevo or '', h.descripcion or ''])
    out.seek(0)
    nombre = proyecto.nombre.replace(' ', '_')
    sufijo = '_con_historial' if con_historial else ''
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="tracereq_{nombre}{sufijo}.csv"'})

@bp_export.route('/json/<int:proyecto_id>')
def exportar_json(proyecto_id):
    con_historial = request.args.get('version') == 'historial'
    proyecto, reqs, casos, relaciones, historial = _datos(proyecto_id, con_historial)
    data = {
        'proyecto': {'id': proyecto.id, 'nombre': proyecto.nombre, 'descripcion': proyecto.descripcion,
                     'fecha_creacion': proyecto.fecha_creacion.isoformat()},
        'requerimientos': [
            {
                'id': r.id, 'identificador': r.identificador, 'tipo': r.tipo,
                'descripcion': r.descripcion, 'prioridad': r.prioridad, 'estado': r.estado,
                'categoria': r.categoria, 'casos_uso': [cu.identificador for cu in r.casos_uso],
                'fecha_creacion': r.fecha_creacion.isoformat(),
                **({'historial': [
                        {'fecha': h.fecha.isoformat(), 'campo': h.campo_modificado,
                         'valor_anterior': h.valor_anterior, 'valor_nuevo': h.valor_nuevo,
                         'motivo': h.descripcion}
                        for h in historial.get(r.id, [])
                    ]} if con_historial else {})
            } for r in reqs
        ],
        'casos_uso': [{'id': cu.id, 'identificador': cu.identificador, 'nombre': cu.nombre,
                       'actor': cu.actor, 'requerimientos': [r.identificador for r in cu.requerimientos],
                       'fecha_creacion': cu.fecha_creacion.isoformat()} for cu in casos],
        'relaciones': [{'origen': rel.origen.identificador, 'tipo': rel.tipo_relacion,
                        'destino': rel.destino.identificador, 'descripcion': rel.descripcion} for rel in relaciones]
    }
    nombre = proyecto.nombre.replace(' ', '_')
    sufijo = '_con_historial' if con_historial else ''
    return Response(json.dumps(data, ensure_ascii=False, indent=2), mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="tracereq_{nombre}{sufijo}.json"'})
