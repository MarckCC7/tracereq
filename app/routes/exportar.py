import csv, json, io
from flask import Blueprint, request, Response
from app.models import Proyecto, Requerimiento, CasoUso, Trazabilidad

bp_export = Blueprint('exportar', __name__)

def _datos(proyecto_id):
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    reqs = Requerimiento.query.filter_by(proyecto_id=proyecto_id).order_by(Requerimiento.identificador).all()
    casos = CasoUso.query.filter_by(proyecto_id=proyecto_id).order_by(CasoUso.identificador).all()
    req_ids = [r.id for r in reqs]
    relaciones = Trazabilidad.query.filter(Trazabilidad.requerimiento_origen_id.in_(req_ids)).all() if req_ids else []
    return proyecto, reqs, casos, relaciones

@bp_export.route('/csv/<int:proyecto_id>')
def exportar_csv(proyecto_id):
    proyecto, reqs, casos, relaciones = _datos(proyecto_id)
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
    out.seek(0)
    nombre = proyecto.nombre.replace(' ', '_')
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="tracereq_{nombre}.csv"'})

@bp_export.route('/json/<int:proyecto_id>')
def exportar_json(proyecto_id):
    proyecto, reqs, casos, relaciones = _datos(proyecto_id)
    data = {
        'proyecto': {'id': proyecto.id, 'nombre': proyecto.nombre, 'descripcion': proyecto.descripcion,
                     'fecha_creacion': proyecto.fecha_creacion.isoformat()},
        'requerimientos': [{'id': r.id, 'identificador': r.identificador, 'tipo': r.tipo,
                             'descripcion': r.descripcion, 'prioridad': r.prioridad, 'estado': r.estado,
                             'categoria': r.categoria, 'casos_uso': [cu.identificador for cu in r.casos_uso],
                             'fecha_creacion': r.fecha_creacion.isoformat()} for r in reqs],
        'casos_uso': [{'id': cu.id, 'identificador': cu.identificador, 'nombre': cu.nombre,
                       'actor': cu.actor, 'requerimientos': [r.identificador for r in cu.requerimientos],
                       'fecha_creacion': cu.fecha_creacion.isoformat()} for cu in casos],
        'relaciones': [{'origen': rel.origen.identificador, 'tipo': rel.tipo_relacion,
                        'destino': rel.destino.identificador, 'descripcion': rel.descripcion} for rel in relaciones]
    }
    nombre = proyecto.nombre.replace(' ', '_')
    return Response(json.dumps(data, ensure_ascii=False, indent=2), mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="tracereq_{nombre}.json"'})
