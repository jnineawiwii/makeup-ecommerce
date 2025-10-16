import os
from flask import Flask, jsonify
from config import Config

# Crear aplicación Flask
app = Flask(__name__)
app.config.from_object(Config)

# RUTAS MÍNIMAS PARA PRUEBA
@app.route('/')
def index():
    return "✅ ¡Aplicación funcionando!"

@app.route('/health')
def health():
    return jsonify({
        'status': 'OK', 
        'message': 'La aplicación está ejecutándose',
        'database': 'PostgreSQL' if 'postgresql' in str(app.config.get('SQLALCHEMY_DATABASE_URI', '')) else 'SQLite'
    })

@app.route('/test')
def test():
    return "✅ Test exitoso"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)