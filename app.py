import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
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

# ✅ DIAGNÓSTICO DE VARIABLES - Agrega esto
print("🔍 DIAGNÓSTICO DE VARIABLES:")
print(f"DATABASE_URL en entorno: {'DATABASE_URL' in os.environ}")
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    print(f"DATABASE_URL: {db_url[:50]}...")  # Mostrar solo parte por seguridad
else:
    print("❌ DATABASE_URL NO ENCONTRADA en variables de entorno")
    print("Variables disponibles:", list(os.environ.keys()))

app.config.from_object(Config)
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

# Importar db después de crear app para evitar importación circular
from models import db, Product, User, Cart, CartItem, Order, OrderItem, Video, Venta



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
        featured_products = Product.query.filter_by(featured=True).limit(6).all()
        featured_video = Video.query.filter_by(is_featured=True).first()
        other_videos = Video.query.filter_by(is_featured=False).limit(4).all()
        
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

@app.route('/create-tables')
def create_tables():
    try:
        with app.app_context():
            db.create_all()
        return {'status': '✅ Tablas creadas exitosamente'}
    except Exception as e:
        return {'status': '❌ Error', 'error': str(e)}, 500

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

# ✅ MUEVE ESTAS RUTAS AQUÍ - ANTES del manejo de errores
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

# ... todo tu código anterior ...
db.init_app(app)
migrate = Migrate(app, db)

# ✅ CREAR TABLAS SI NO EXISTEN
with app.app_context():
    try:
        db.create_all()
        print("✅ Tablas verificadas/creadas en PostgreSQL")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")

  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)