from datetime import datetime
from app import db

class Proyecto(db.Model):
    __tablename__ = 'proyectos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    requerimientos = db.relationship('Requerimiento', backref='proyecto', lazy='dynamic', cascade='all, delete-orphan')
    casos_uso = db.relationship('CasoUso', backref='proyecto', lazy='dynamic', cascade='all, delete-orphan')


class Requerimiento(db.Model):
    __tablename__ = 'requerimientos'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyectos.id'), nullable=False)
    identificador = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.Enum('funcional', 'no_funcional'), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    prioridad = db.Column(db.Enum('alta', 'media', 'baja'), nullable=False, default='media')
    estado = db.Column(db.Enum('pendiente', 'activo', 'completado', 'cancelado'), nullable=False, default='pendiente')
    categoria = db.Column(db.String(80))  # para no funcionales: rendimiento, seguridad, usabilidad, etc.
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('proyecto_id', 'identificador', name='uq_req_identificador'),)

    historial = db.relationship('HistorialCambio', backref='requerimiento', lazy='dynamic', cascade='all, delete-orphan')
    comentarios = db.relationship('Comentario', backref='requerimiento', lazy='dynamic', cascade='all, delete-orphan')

    # relaciones de trazabilidad como origen
    relaciones_origen = db.relationship(
        'Trazabilidad',
        foreign_keys='Trazabilidad.requerimiento_origen_id',
        backref='origen',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    # relaciones de trazabilidad como destino
    relaciones_destino = db.relationship(
        'Trazabilidad',
        foreign_keys='Trazabilidad.requerimiento_destino_id',
        backref='destino',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )


# Tabla asociativa casos_uso <-> requerimientos
caso_uso_requerimiento = db.Table(
    'caso_uso_requerimiento',
    db.Column('caso_uso_id', db.Integer, db.ForeignKey('casos_uso.id'), primary_key=True),
    db.Column('requerimiento_id', db.Integer, db.ForeignKey('requerimientos.id'), primary_key=True)
)


class CasoUso(db.Model):
    __tablename__ = 'casos_uso'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyectos.id'), nullable=False)
    identificador = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    actor = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('proyecto_id', 'identificador', name='uq_cu_identificador'),)

    requerimientos = db.relationship(
        'Requerimiento',
        secondary=caso_uso_requerimiento,
        backref=db.backref('casos_uso', lazy='dynamic'),
        lazy='dynamic'
    )


class Trazabilidad(db.Model):
    __tablename__ = 'trazabilidad'
    id = db.Column(db.Integer, primary_key=True)
    requerimiento_origen_id = db.Column(db.Integer, db.ForeignKey('requerimientos.id'), nullable=False)
    requerimiento_destino_id = db.Column(db.Integer, db.ForeignKey('requerimientos.id'), nullable=False)
    tipo_relacion = db.Column(db.Enum('depende_de', 'refina', 'contradice'), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('requerimiento_origen_id', 'requerimiento_destino_id', name='uq_trazabilidad'),
    )


class HistorialCambio(db.Model):
    __tablename__ = 'historial_cambios'
    id = db.Column(db.Integer, primary_key=True)
    requerimiento_id = db.Column(db.Integer, db.ForeignKey('requerimientos.id'), nullable=False)
    campo_modificado = db.Column(db.String(80))
    valor_anterior = db.Column(db.Text)
    valor_nuevo = db.Column(db.Text)
    descripcion = db.Column(db.String(255))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Comentario(db.Model):
    __tablename__ = 'comentarios'
    id = db.Column(db.Integer, primary_key=True)
    requerimiento_id = db.Column(db.Integer, db.ForeignKey('requerimientos.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    autor = db.Column(db.String(80), default='Sistema')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
