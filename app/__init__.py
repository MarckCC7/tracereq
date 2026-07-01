from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)

    from app.routes.proyectos import bp_proyectos
    from app.routes.requerimientos import bp_reqs
    from app.routes.casos_uso import bp_cu
    app.register_blueprint(bp_proyectos, url_prefix='/proyectos')
    app.register_blueprint(bp_reqs, url_prefix='/requerimientos')
    app.register_blueprint(bp_cu, url_prefix='/casos-uso')

    return app