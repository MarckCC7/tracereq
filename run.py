from app import create_app
from app.esquema import asegurar_esquema

app = create_app('development')

if __name__ == '__main__':
    with app.app_context():
        asegurar_esquema()
        print('Base de datos lista.')
    app.run(debug=True, port=5000)