import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from PIL import Image
from flask_migrate import Migrate
import requests
import base64
import json
import os
import traceback

# Importar configuración primero
from config import Config

# Crear aplicación Flask
app = Flask(__name__)
app.config.from_object(Config)

# ✅ INICIALIZAR EXTENSIONES INMEDIATAMENTE
from models import db  # ✅ Importar db desde models

# Inicializar db con la app
db.init_app(app)
migrate = Migrate(app, db)

# Configuración adicional
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['VIDEO_UPLOAD_FOLDER'] = 'static/videos'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'wmv', 'webm', 'mkv'}

# Asegurar que las carpetas existan
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ✅ IMPORTAR MODELOS DESPUÉS DE INICIALIZAR DB
from models import Product, User, Cart, CartItem, Order, OrderItem, Video, Venta

# Cargar variables de entorno
def load_environment():
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key, value)
            print("✅ Variables cargadas desde .env")
        else:
            print("🌐 Usando variables de entorno del sistema")
    except Exception as e:
        print(f"⚠️ Error cargando entorno: {e}")

load_environment()

# Configuración de PayPal
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_BASE_URL = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"

# 🔥 DECORADORES PARA CONTROL DE ACCESO
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def master_admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_master_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Función para obtener access token de PayPal
def get_paypal_access_token():
    try:
        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}"
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", headers=headers, data=data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Error PayPal: {response.text}")
            return None
    except Exception as e:
        print(f"Error obteniendo token PayPal: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ✅ RUTAS SIMPLES DE PRUEBA PRIMERO
@app.route('/')
def index():
    return "✅ ¡Aplicación funcionando! Visita /health para verificar"

@app.route('/health')
def health():
    return jsonify({
        'status': 'OK', 
        'message': 'La aplicación está ejecutándose',
        'database': 'PostgreSQL' if 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'SQLite'
    })

@app.route('/test-db')
def test_db():
    try:
        with app.app_context():
            db.engine.connect()
            return "✅ Base de datos conectada correctamente"
    except Exception as e:
        return f"❌ Error en base de datos: {str(e)}"

# ✅ CREAR TABLAS AL INICIO
with app.app_context():
    try:
        db.create_all()
        print("✅ Tablas verificadas/creadas en PostgreSQL")
        
        # Crear usuario admin si no existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@makeup.com', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Usuario admin creado")
            
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

# RUTAS DE AUTENTICACIÓN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email, role='customer')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('¡Registro exitoso! Bienvenido/a', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('index'))

# RUTAS DE PRODUCTOS
@app.route('/products')
def products():
    try:
        products = Product.query.all()
        return render_template('products.html', products=products)
    except Exception as e:
        return f"Error cargando productos: {str(e)}"

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return render_template('product_detail.html', product=product)
    except Exception as e:
        return f"Error cargando producto: {str(e)}"

# RUTAS DEL CARRITO (simplificadas)
@app.route('/cart')
@login_required
def cart():
    try:
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        cart_items = []
        total = 0
        
        if cart:
            for item in cart.items:
                item_total = item.product.price * item.quantity
                total += item_total
                cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'total': item_total
                })
        
        return render_template('cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        return f"Error cargando carrito: {str(e)}"

# RUTAS DE ADMINISTRACIÓN
@app.route('/admin')
@admin_required
def admin_dashboard():
    try:
        stats = {
            'product_count': Product.query.count(),
            'user_count': User.query.count(),
            'order_count': Order.query.count(),
            'video_count': Video.query.count(),
            'venta_count': Venta.query.count()
        }
        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        return f"Error en dashboard admin: {str(e)}"

@app.route('/admin/products')
@admin_required
def admin_products():
    try:
        products = Product.query.all()
        return render_template('admin/products.html', products=products)
    except Exception as e:
        return f"Error cargando productos admin: {str(e)}"

@app.route('/admin/videos')
@admin_required
def admin_videos():
    try:
        videos = Video.query.all()
        return render_template('admin/videos.html', videos=videos)
    except Exception as e:
        return f"Error cargando videos: {str(e)}"

@app.route('/admin/ventas')
@admin_required
def admin_ventas():
    try:
        ventas = Venta.query.order_by(Venta.fecha.desc()).all()
        total_general = sum(venta.producto.price * venta.cantidad for venta in ventas)
        return render_template('admin/ventas.html', 
                             ventas=ventas,
                             total_general=total_general)
    except Exception as e:
        return f"Error cargando ventas: {str(e)}"

@app.route('/admin/users')
@admin_required
def admin_users():
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        return f"Error cargando usuarios: {str(e)}"

# MANEJO DE ERRORES
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return f"""
    <h1>Error 500 - Error Interno del Servidor</h1>
    <p><strong>Error:</strong> {str(e)}</p>
    <pre>{traceback.format_exc()}</pre>
    """, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)