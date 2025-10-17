import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, User, Product, Video, Order, OrderItem 
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


# Importar configuración desde config.py
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# ✅ INICIALIZAR DB PRIMERO - CORREGIDO
from models import db
db.init_app(app)
migrate = Migrate(app, db)

# ✅ DIAGNÓSTICO
print("🔍 DIAGNÓSTICO DE PLANTILLAS:")
print(f"Directorio actual: {os.getcwd()}")
print(f"¿Existe templates/? {os.path.exists('templates')}")
print(f"¿Existe templates/login.html? {os.path.exists('templates/login.html')}")

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['VIDEO_UPLOAD_FOLDER'] = 'static/videos'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'wmv', 'webm', 'mkv'}

# Asegurar que las carpetas existan
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

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

# RUTAS DE PRUEBA PARA DIAGNÓSTICO
@app.route('/')
def index():
    try:
        featured_products = Product.query.filter(Product.featured == True).limit(6).all()
        featured_video = Video.query.filter_by(is_featured=True).first()
        other_videos = Video.query.filter_by(is_featured=False).limit(4).all()
        
        print(f"🔍 Página principal - Productos destacados encontrados: {len(featured_products)}")
        
        # DEBUG: Imprimir los productos que se están enviando a la plantilla
        for i, p in enumerate(featured_products):
            print(f"   Producto {i+1}: {p.name} - ${p.price} - {p.category}")
        
        return render_template(
            'index.html',
            featured_products=featured_products,
            featured_video=featured_video,
            other_videos=other_videos
        )
    except Exception as e:
        return f"""
        <h1>Error en la página principal</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <pre>{traceback.format_exc()}</pre>
        """

@app.route('/test')
def test():
    return "✅ Aplicación funcionando correctamente"

@app.route('/test-db')
def test_db():
    try:
        product_count = Product.query.count()
        user_count = User.query.count()
        return f"""
        <h1>✅ Base de datos conectada</h1>
        <p>Productos: {product_count}</p>
        <p>Usuarios: {user_count}</p>
        """
    except Exception as e:
        return f"""
        <h1>❌ Error en base de datos</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <pre>{traceback.format_exc()}</pre>
        """

@app.route('/health')
def health():
    """Ruta simple de verificación"""
    return {
        'status': '✅ OK',
        'message': 'La aplicación está ejecutándose',
        'database': 'PostgreSQL' if 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'SQLite'
    }

@app.route('/check-database')
def check_database():
    try:
        # Verificar conexión a la base de datos
        with app.app_context():
            db.engine.connect()
            return {
                'status': '✅ CONEXIÓN EXITOSA A POSTGRESQL',
                'database_engine': str(db.engine.url)[:50] + '...',
                'message': 'La base de datos está funcionando correctamente'
            }
    except Exception as e:
        return {
            'status': '❌ ERROR DE CONEXIÓN',
            'error': str(e),
            'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', 'No configurada')
        }, 500

@app.route('/init-database')
def init_database():
    """Inicializar base de datos con tablas y datos básicos"""
    try:
        with app.app_context():
            # Crear todas las tablas
            db.create_all()
            print("✅ Tablas creadas en PostgreSQL")
            
            # Crear usuario administrador si no existe
            if not User.query.filter_by(username='master_admin').first():
                master_admin = User(
                    username='master_admin', 
                    email='admin@makeup.com', 
                    role='master_admin'
                )
                master_admin.set_password('admin123')
                db.session.add(master_admin)
                print("✅ Usuario master_admin creado")
            
            if not User.query.filter_by(username='admin').first():
                admin_user = User(
                    username='admin', 
                    email='admin2@makeup.com', 
                    role='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                print("✅ Usuario admin creado")
            
            # Crear algunos productos de ejemplo si no existen
            if Product.query.count() == 0:
                sample_products = [
                    Product(
                        name='Labial Rojo', 
                        description='Labial de larga duración color rojo intenso',
                        price=250.00, 
                        category='labiales',
                        stock=10,
                        image_url=''
                    ),
                    Product(
                        name='Sombras Nude', 
                        description='Paleta de sombras en tonos nude',
                        price=450.00, 
                        category='ojos',
                        stock=15,
                        image_url=''
                    )
                ]
                db.session.add_all(sample_products)
                print("✅ Productos de ejemplo creados")
            
            db.session.commit()
            
            return {
                'status': '✅ Base de datos inicializada',
                'tablas_creadas': True,
                'usuarios_creados': User.query.count(),
                'productos_creados': Product.query.count()
            }
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error inicializando BD: {e}")
        return {'status': '❌ Error', 'error': str(e)}, 500

# Ruta de búsqueda
@app.route('/search')
def search():
    try:
        query = request.args.get('q', '').strip()
        
        if query:
            products = Product.query.filter(
                (Product.name.ilike(f'%{query}%')) |
                (Product.description.ilike(f'%{query}%')) |
                (Product.category.ilike(f'%{query}%'))
            ).all()
        else:
            products = []
        
        return render_template('search_results.html', 
                             products=products, 
                             query=query,
                             search_count=len(products))
    except Exception as e:
        return f"Error en búsqueda: {str(e)}"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        next_page = request.form.get('next', '')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html', next=request.args.get('next', ''))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        next_page = request.form.get('next', '')
        
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
        return redirect(next_page or url_for('index'))
    
    return render_template('register.html', next=request.args.get('next', ''))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('index'))

# Rutas de productos
@app.route('/products')
def products():
    try:
        category = request.args.get('category', '')
        query = request.args.get('q', '')
        
        if category:
            products_query = Product.query.filter_by(category=category)
        else:
            products_query = Product.query
        
        if query:
            products_query = products_query.filter(
                (Product.name.ilike(f'%{query}%')) |
                (Product.description.ilike(f'%{query}%'))
            )
        
        products = products_query.all()
        
        return render_template('products.html', 
                             products=products, 
                             category=category,
                             search_query=query)
    except Exception as e:
        return f"Error cargando productos: {str(e)}"

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return render_template('product_detail.html', product=product)
    except Exception as e:
        return f"Error cargando producto: {str(e)}"

# Rutas del carrito
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not current_user.is_authenticated:
        return jsonify({
            'success': False, 
            'message': 'Debes iniciar sesión',
            'redirect': url_for('login')
        })
    
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Producto no encontrado'})
        
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.commit()
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Producto agregado al carrito'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

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

@app.route('/update_cart_quantity', methods=['POST'])
@login_required
def update_cart_quantity():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        if not product_id:
            return jsonify({'success': False, 'message': 'ID de producto no proporcionado'})
        
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart:
            return jsonify({'success': False, 'message': 'Carrito no encontrado'})
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if cart_item:
            if quantity <= 0:
                db.session.delete(cart_item)
            else:
                cart_item.quantity = quantity
            db.session.commit()
            return jsonify({'success': True, 'message': 'Cantidad actualizada'})
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado en el carrito'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'message': 'ID de producto no proporcionado'})
        
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart:
            return jsonify({'success': False, 'message': 'Carrito no encontrado'})
        
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            
            cart_items = []
            total = 0
            for item in cart.items:
                item_total = item.product.price * item.quantity
                total += item_total
                cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'total': item_total
                })
            
            return jsonify({
                'success': True, 
                'message': 'Producto eliminado del carrito',
                'total': total,
                'item_count': len(cart.items)
            })
        else:
            return jsonify({'success': False, 'message': 'Producto no encontrado en el carrito'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/checkout')
@login_required
def checkout():
    try:
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        cart_items = []
        subtotal = 0
        tax = 0
        shipping = 0
        total = 0
        
        if cart:
            for item in cart.items:
                item_total = item.product.price * item.quantity
                subtotal += item_total
                cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'total': item_total
                })
        
        tax = subtotal * 0.16
        shipping = 5.00 if subtotal > 0 else 0
        total = subtotal + tax + shipping
        
        return render_template('checkout.html', 
                             cart_items=cart_items, 
                             subtotal=subtotal,
                             tax=tax,
                             shipping=shipping,
                             total=total)
    except Exception as e:
        return f"Error en checkout: {str(e)}"

# Rutas de PayPal (simplificadas)
@app.route('/create-paypal-order', methods=['POST'])
@login_required
def create_paypal_order():
    try:
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart or not cart.items:
            return jsonify({'error': 'Carrito vacío'}), 400
        
        subtotal = sum(item.product.price * item.quantity for item in cart.items)
        tax = subtotal * 0.16
        shipping = 5.00
        total = subtotal + tax + shipping
        
        # Para desarrollo, simular orden
        order_id = f"simulated_{random.randint(100000, 999999)}"
        return jsonify({'id': order_id})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/capture-paypal-order', methods=['POST'])
@login_required
def capture_paypal_order():
    try:
        data = request.get_json()
        order_id = data.get('orderID')
        
        if not order_id:
            return jsonify({'error': 'ID de orden inválido'}), 400
        
        session['last_order_total'] = 100.00  # Simulado
        session['paypal_order_id'] = order_id
        
        return jsonify({'success': True})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/payment-cancelled')
def payment_cancelled():
    flash('Has cancelado el proceso de pago', 'info')
    return redirect(url_for('checkout'))

@app.route('/order-confirmation')
@login_required
def order_confirmation():
    total = session.get('last_order_total', 0)
    order_id = session.get('paypal_order_id', '')
    return render_template('order_confirmation.html', 
                         total=total, 
                         order_id=order_id,
                         currency="MXN")

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

# 🎯 RUTAS DE ADMINISTRACIÓN FALTANTES
@app.route('/admin/videos')
@admin_required
def admin_videos():
    """Gestión de videos"""
    try:
        videos = Video.query.all()
        return render_template('admin/videos.html', videos=videos)
    except Exception as e:
        return f"Error cargando videos: {str(e)}"

@app.route('/admin/ventas')
@admin_required
def admin_ventas():
    """Gestión de ventas"""
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
    """Gestión de usuarios"""
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        return f"Error cargando usuarios: {str(e)}"

@app.route('/admin/videos/add', methods=['GET', 'POST'])
@admin_required
def admin_add_video():
    """Agregar video"""
    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form['description']
            category = request.form['category']
            is_featured = 'is_featured' in request.form
            
            file_path = None
            if 'video_file' in request.files:
                file = request.files['video_file']
                if file and file.filename != '' and allowed_video_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    file_path = f"videos/{unique_filename}"
            
            if not file_path:
                flash('Debes subir un archivo de video', 'error')
                return render_template('admin/add_video.html')
            
            new_video = Video(
                title=title,
                description=description,
                category=category,
                url=None,
                file_path=file_path,
                is_featured=is_featured,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_video)
            db.session.commit()
            flash('Video agregado correctamente', 'success')
            return redirect(url_for('admin_videos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar video: {str(e)}', 'error')
    
    return render_template('admin/add_video.html')

@app.route('/admin/user/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Agregar usuario"""
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya existe', 'danger')
                return redirect(url_for('admin_add_user'))
            
            if User.query.filter_by(email=email).first():
                flash('El email ya está registrado', 'danger')
                return redirect(url_for('admin_add_user'))
            
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Usuario agregado exitosamente', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar usuario: {str(e)}', 'danger')
    
    return render_template('admin/add_user.html')

@app.route('/admin/products')
@admin_required
def admin_products():
    try:
        products = Product.query.all()
        return render_template('admin/products.html', products=products)
    except Exception as e:
        return f"Error cargando productos admin: {str(e)}"

# 🎯 RUTAS CRÍTICAS FALTANTES - AGREGAR PRODUCTO
@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    """Agregar producto - RUTA CRÍTICA FALTANTE"""
    if request.method == 'POST':
        try:
            # Procesar la imagen
            image_filename = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Redimensionar si es necesario
                    try:
                        img = Image.open(filepath)
                        if img.width > 800 or img.height > 800:
                            img.thumbnail((800, 800))
                            img.save(filepath)
                    except:
                        pass
                    
                    image_filename = f"/static/uploads/{unique_filename}"
            
            # Crear el producto
            new_product = Product(
                name=request.form['name'],
                description=request.form['description'],
                price=float(request.form['price']),
                category=request.form['category'],
                image_url=image_filename if image_filename else '',
                stock=int(request.form['stock'])
            )
            
            db.session.add(new_product)
            db.session.commit()
            flash('Producto agregado exitosamente', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar producto: {str(e)}', 'danger')
    
    return render_template('admin/agregar.html')

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    """Editar producto - RUTA FALTANTE"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Procesar nueva imagen si se subió
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    # Eliminar imagen anterior si existe
                    if product.image_url and product.image_url.startswith('/static/uploads/'):
                        old_image_path = product.image_url.replace('/static/', '')
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    # Guardar nueva imagen
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Redimensionar si es necesario
                    try:
                        img = Image.open(filepath)
                        if img.width > 800 or img.height > 800:
                            img.thumbnail((800, 800))
                            img.save(filepath)
                    except:
                        pass
                    
                    product.image_url = f"/static/uploads/{unique_filename}"
            
            # Actualizar otros campos
            product.name = request.form['name']
            product.description = request.form['description']
            product.price = float(request.form['price'])
            product.category = request.form['category']
            product.stock = int(request.form['stock'])
            
            db.session.commit()
            flash('Producto actualizado exitosamente', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar producto: {str(e)}', 'danger')
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    """Eliminar producto - RUTA FALTANTE"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash('Producto eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar producto: {str(e)}', 'danger')
    
    return redirect(url_for('admin_products'))

@app.route('/admin/video/edit/<int:video_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_video(video_id):
    """Editar video - RUTA FALTANTE"""
    video = Video.query.get_or_404(video_id)
    
    if request.method == 'POST':
        try:
            # Procesar nuevo archivo de video si se subió
            if 'video_file' in request.files:
                file = request.files['video_file']
                if file and file.filename != '' and allowed_video_file(file.filename):
                    # Eliminar video anterior si existe
                    if video.file_path:
                        old_video_path = os.path.join('static', video.file_path)
                        if os.path.exists(old_video_path):
                            os.remove(old_video_path)
                    
                    # Guardar nuevo video
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    video.file_path = f"videos/{unique_filename}"
                    video.url = None
            
            # Actualizar otros campos
            video.title = request.form['title']
            video.description = request.form['description']
            video.category = request.form['category']
            video.is_featured = 'is_featured' in request.form
            
            db.session.commit()
            flash('Video actualizado exitosamente', 'success')
            return redirect(url_for('admin_videos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar video: {str(e)}', 'danger')
    
    return render_template('admin/edit_video.html', video=video)

@app.route('/admin/video/delete/<int:video_id>', methods=['POST'])
@admin_required
def admin_delete_video(video_id):
    """Eliminar video - RUTA FALTANTE"""
    try:
        video = Video.query.get_or_404(video_id)
        
        # Eliminar archivo si existe
        if video.file_path:
            video_path = os.path.join('static', video.file_path)
            if os.path.exists(video_path):
                os.remove(video_path)
        
        db.session.delete(video)
        db.session.commit()
        flash('Video eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar video: {str(e)}', 'danger')
    
    return redirect(url_for('admin_videos'))

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Editar usuario - RUTA FALTANTE"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            user.email = request.form['email']
            user.role = request.form['role']
            
            if request.form['password']:
                user.set_password(request.form['password'])
            
            db.session.commit()
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'danger')
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Eliminar usuario - RUTA FALTANTE"""
    try:
        user = User.query.get_or_404(user_id)
        
        # No permitir eliminarse a sí mismo
        if user.id == current_user.id:
            flash('No puedes eliminar tu propio usuario', 'danger')
            return redirect(url_for('admin_users'))
        
        db.session.delete(user)
        db.session.commit()
        flash('Usuario eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/debug-database-connection')
def debug_database_connection():
    try:
        # 1. Verificar conexión
        db.engine.connect()
        
        # 2. Verificar tablas existentes
        inspector = db.inspect(db.engine)
        tablas = inspector.get_table_names()
        
        # 3. Verificar columnas de la tabla products
        columnas = inspector.get_columns('products')
        
        resultado = f"""
        <h1>🔍 Diagnóstico de Base de Datos</h1>
        
        <h2>✅ Conexión: OK</h2>
        
        <h2>📊 Tablas en la BD:</h2>
        <ul>
        """
        for tabla in tablas:
            resultado += f"<li>{tabla}</li>"
        
        resultado += "</ul>"
        
        resultado += "<h2>📋 Columnas de 'products':</h2><ul>"
        for columna in columnas:
            resultado += f"<li>{columna['name']} - {columna['type']}</li>"
        resultado += "</ul>"
        
        # 4. Intentar consulta directa
        resultado += "<h2>🔍 Consulta directa:</h2>"
        with db.engine.connect() as conn:
            productos_directo = conn.execute(db.text("SELECT * FROM products")).fetchall()
            resultado += f"<p>Productos encontrados (consulta directa): {len(productos_directo)}</p>"
            
            for producto in productos_directo:
                resultado += f"<div style='border:1px solid #ccc; margin:5px; padding:5px;'>"
                resultado += f"ID: {producto.id} | Name: {producto.name} | Price: {producto.price}"
                resultado += f" | Featured: {producto.featured}</div>"
        
        return resultado
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/db-connection-info')
def db_connection_info():
    import os
    from urllib.parse import urlparse
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        parsed = urlparse(db_url)
        info = f"""
        <h1>Información para DBeaver</h1>
        <p><strong>Host:</strong> {parsed.hostname}</p>
        <p><strong>Puerto:</strong> {parsed.port}</p>
        <p><strong>Base de datos:</strong> {parsed.path[1:]}</p>
        <p><strong>Usuario:</strong> {parsed.username}</p>
        <p><strong>Contraseña:</strong> {parsed.password}</p>
        """
    else:
        info = "<h1>DATABASE_URL no configurada</h1>"
    
    return info
@app.route('/db-info')
def db_info():
    import os
    from urllib.parse import urlparse
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        parsed = urlparse(db_url)
        info = f"""
        <h1>Configuración para DBeaver</h1>
        <div style='background:#f5f5f5; padding:20px; border-radius:10px;'>
            <h3>📋 Datos de conexión:</h3>
            <p><strong>Host:</strong> {parsed.hostname}</p>
            <p><strong>Port:</strong> {parsed.port}</p>
            <p><strong>Database:</strong> {parsed.path[1:]}</p>
            <p><strong>Username:</strong> {parsed.username}</p>
            <p><strong>Password:</strong> {parsed.password}</p>
        </div>
        <p><em>⚠️ Esta información es sensible. No la compartas.</em></p>
        """
    else:
        info = "<h1>❌ DATABASE_URL no encontrada</h1>"
    
    return info    

@app.route('/update-db-relations')
def update_db_relations():
    from app import db
    try:
        # Esto forzará la actualización de las relaciones
        db.drop_all()
        db.create_all()
        return "<h1>✅ Base de datos actualizada con relaciones correctas</h1>"
    except Exception as e:
        return f"<h1>❌ Error actualizando BD:</h1><p>{str(e)}</p>"

@app.route('/check-database-url')
def check_database_url():
    return f"""
    <h1>Configuración de BD</h1>
    <p>DATABASE_URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'No configurada')}</p>
    <p>¿Usando PostgreSQL?: {'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '')}</p>
    """        

@app.route('/debug-model-error')
def debug_model_error():
    try:
        # Intentar acceder a los productos
        productos = Product.query.all()
        return f"✅ Productos encontrados: {len(productos)}"
    except Exception as e:
        return f"""
        <h1>❌ Error en el modelo</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p>El problema es que el modelo busca 'nombre' pero la BD tiene 'name'</p>
        """


@app.route('/fix-featured-products')
def fix_featured_products():
    try:
        # Forzar que todos los productos con featured=true se muestren
        featured_products = Product.query.filter(Product.featured == True).limit(6).all()
        
        resultado = f"<h1>Productos con featured (FIX): {len(featured_products)}</h1>"
        
        for i, p in enumerate(featured_products):
            resultado += f"""
            <div style='border: 1px solid green; margin: 10px; padding: 10px; background: #f0fff0;'>
                <strong>✅ Producto {i+1}:</strong><br>
                ID: {p.id}<br>
                Nombre: {p.name}<br>
                Precio: ${p.price}<br>
                Categoría: {p.category}<br>
                Stock: {p.stock}<br>
                Featured: {p.featured}<br>
                Image: {p.image_url}
            </div>
            """
        
        return resultado
    except Exception as e:
        return f"Error: {str(e)}"
@app.route('/add-sample-products')
def add_sample_products():
    from app import db, Product
    
    sample_products = [
        Product(name="Labial Rojo Mate", price=25.99, category="labios", description="Labial mate color rojo intenso", image_url="/static/images/labial-rojo.jpg"),
        Product(name="Paleta Sombras Nude", price=35.50, category="ojos", description="Paleta de sombras en tonos nude", image_url="/static/images/sombras-nude.jpg"),
        Product(name="Base Líquida Cover", price=42.00, category="rostro", description="Base de cobertura media", image_url="/static/images/base-liquida.jpg"),
        Product(name="Máscara de Pestañas", price=18.75, category="ojos", description="Máscara volumen extra", image_url="/static/images/mascara-pestanas.jpg"),
        Product(name="Rubor en Polvo", price=28.30, category="rostro", description="Rubor mate color melocotón", image_url="/static/images/rubor-polvo.jpg"),
        Product(name="Delineador Líquido", price=22.50, category="ojos", description="Delineador de precisión negro", image_url="/static/images/delineador.jpg")
    ]
    
    for product in sample_products:
        db.session.add(product)
    
    db.session.commit()
    
    # Verificar que se guardaron
    product_count = Product.query.count()
    return f"<h1>✅ {len(sample_products)} productos de ejemplo agregados</h1><p>Total en base de datos: {product_count} productos</p>"

@app.route('/check-products')
def check_products():
    from app import Product
    try:
        products = Product.query.all()
        result = f"<h1>Productos en la base de datos: {len(products)}</h1>"
        
        for p in products:
            result += f"""
            <div style='border: 1px solid #ccc; margin: 10px; padding: 10px;'>
                <h3>{p.name}</h3>
                <p>Precio: ${p.price}</p>
                <p>Categoría: {p.category}</p>
                <p>Descripción: {p.description}</p>
            </div>
            """
        
        return result
    except Exception as e:
        return f"<h1>❌ Error leyendo productos:</h1><p>{str(e)}</p>"

@app.route('/restore-my-products')
def restore_my_products():
    try:
        # TUS PRODUCTOS ORIGINALES
        mis_productos = [
            Product(
                name="Labial Mate Ruby Woo",
                description="Labial de larga duración color rojo intenso",
                price=5.00,
                category="labios", 
                image_url="/static/images/labial2.png",
                stock=2,
                featured=True
            ),
            Product(
                name="Base Studio Fix Fluid", 
                description="Base de cobertura media a completa",
                price=12.00,
                category="rostro",
                image_url="/static/uploads/20250912_160045_basemac.jpg", 
                stock=30,
                featured=True
            ),
            Product(
                name="Sombra de Ojos",
                description="Paleta de sombras con 9 tonos neutros", 
                price=8.00,
                category="ojos",
                image_url="/static/uploads/20250912_160100_sombras.png",
                stock=10,
                featured=True
            ),
            Product(
                name="base",
                description="base de alta cobertura",
                price=223.00,
                category="labios",
                image_url="/static/uploads/20250922_204131_basemac.jpg", 
                stock=34,
                featured=False
            )
        ]
        
        db.session.bulk_save_objects(mis_productos)
        db.session.commit()
        
        return "✅ Tus 4 productos originales restaurados<br><a href='/debug-productos'>Ver productos</a> | <a href='/'>Ir a página principal</a>"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


                

@app.route('/debug-featured-products')
def debug_featured_products():
    try:
        # Verificar qué productos tienen featured=true
        featured_products = Product.query.filter_by(featured=True).all()
        
        resultado = f"<h1>Productos con featured=True: {len(featured_products)}</h1>"
        
        for i, p in enumerate(featured_products):
            resultado += f"""
            <div style='border: 1px solid green; margin: 10px; padding: 10px; background: #f0fff0;'>
                <strong>✅ Producto {i+1}:</strong><br>
                ID: {p.id}<br>
                Nombre: {p.name}<br>
                Precio: ${p.price}<br>
                Categoría: {p.category}<br>
                Stock: {p.stock}<br>
                Featured: {p.featured}<br>
                Image: {p.image_url}
            </div>
            """
        
        # También verificar la consulta exacta que usa tu página principal
        resultado += f"<h2>Consulta SQL:</h2>"
        resultado += f"<code>Product.query.filter_by(featured=True).limit(6).all()</code>"
        
        return resultado
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/create-tables')
def create_tables():
    from app import db
    try:
        db.create_all()
        return """
        <h1>✅ Tablas creadas en PostgreSQL</h1>
        <p>Ahora puedes:</p>
        <ol>
            <li><a href="/add-sample-products">Agregar productos de ejemplo</a></li>
            <li><a href="/">Ver la página principal</a></li>
        </ol>
        """
    except Exception as e:
        return f"<h1>❌ Error creando tablas:</h1><p>{str(e)}</p>"

@app.route('/debug-productos')
def debug_productos():
    try:
        productos = Product.query.all()
        resultado = f"<h1>Productos en la BD: {len(productos)}</h1><br>"
        
        for i, p in enumerate(productos):
            resultado += f"Producto {i+1}: {p.name} - ${p.price} - {p.category}<br>"
        
        return resultado
    except Exception as e:
        return f"Error al consultar productos: {str(e)}"      
"""
# Inicialización de base de datos
@app.route('/init_db')
def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            if User.query.count() == 0:
                master_admin = User(username='master_admin', email='master@example.com', role='master_admin')
                master_admin.set_password('master123')
                db.session.add(master_admin)
                
                admin_user = User(username='admin', email='admin@example.com', role='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                
                print("✅ Usuarios administradores creados")
            
            db.session.commit()
            return '✅ Base de datos inicializada correctamente'
            
        except Exception as e:
            db.session.rollback()
            return f'❌ Error al inicializar base de datos: {str(e)}'

# MANTÉN ESTA RUTA (es importante para las tablas y usuarios)


# === AGREGA ESTAS NUEVAS RUTAS DESPUÉS ===

@app.route('/debug-productos')
def debug_productos():
    try:
        from models import Product
        productos = Product.query.all()
        resultado = f"Total productos en BD: {len(productos)}<br><br>"
        
        for i, p in enumerate(productos):
            resultado += f"Producto {i+1}: {p.nombre} - ${p.precio} - {p.categoria}<br>"
        
        return resultado
    except Exception as e:
        return f"Error al consultar productos: {str(e)}"

@app.route('/add-sample-products')
def add_sample_products():
    try:
        from models import Product, db
        
        # Verificar si ya hay productos
        if Product.query.count() == 0:
            # Agregar productos de prueba
            productos_ejemplo = [
                Product(
                    nombre="Labial MAC Rojo", 
                    precio=25.99, 
                    categoria="labios", 
                    imagen="/static/images/labial1.jpg",
                    descripcion="Labial de larga duración color rojo intenso",
                    stock=10
                ),
                Product(
                    nombre="Paleta de Sombras", 
                    precio=32.50, 
                    categoria="ojos", 
                    imagen="/static/images/sombras1.jpg",
                    descripcion="Paleta profesional con 12 colores",
                    stock=15
                ),
                Product(
                    nombre="Base Líquida Natural", 
                    precio=28.75, 
                    categoria="rostro", 
                    imagen="/static/images/base1.jpg",
                    descripcion="Base de cobertura media para todo tipo de piel",
                    stock=8
                ),
                Product(
                    nombre="Gloss Brillante", 
                    precio=18.99, 
                    categoria="labios", 
                    imagen="/static/images/gloss1.jpg",
                    descripcion="Gloss labial con efecto brillo",
                    stock=12
                )
            ]
            
            db.session.bulk_save_objects(productos_ejemplo)
            db.session.commit()
            return "✅ Productos de ejemplo agregados (4 productos)<br><a href='/debug-productos'>Ver productos</a> | <a href='/'>Ir a página principal</a>"
        else:
            return f"✅ Ya existen {Product.query.count()} productos en la BD<br><a href='/debug-productos'>Ver productos</a> | <a href='/'>Ir a página principal</a>"
            
    except Exception as e:
        return f"❌ Error al agregar productos: {str(e)}"
"""
@app.route('/debug-routes')
def debug_routes():
    """Muestra todas las rutas disponibles"""
    routes = []
    for rule in app.url_map.iter_rules():
        if 'static' not in rule.rule:
            routes.append(f"{rule.endpoint}: {rule.rule}")
    return "<br>".join(sorted(routes))

# Manejo de errores
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

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ✅ CREAR TABLAS SI NO EXISTEN
with app.app_context():
    try:
        db.create_all()
        print("✅ Tablas verificadas/creadas en PostgreSQL")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)