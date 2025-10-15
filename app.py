import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Product, User, Cart, CartItem, Order, OrderItem, Video, Venta
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps
from werkzeug.utils import secure_filename
from PIL import Image
from flask_migrate import Migrate
import requests
import base64
import json
import os

# Importar configuración desde config.py
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['VIDEO_UPLOAD_FOLDER'] = 'static/videos'  # Nueva carpeta específica para videos
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB máximo para videos
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'wmv', 'webm', 'mkv'}

# Asegurar que las carpetas existan
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)  # Crear carpeta de videos

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def allowed_video_file(filename):  # Nueva función para videos
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db.init_app(app)
migrate = Migrate(app, db)

# Cargar variables de entorno
load_dotenv()

# Configuración de PayPal
PAYPAL_CLIENT_ID = app.config['PAYPAL_CLIENT_ID']
PAYPAL_CLIENT_SECRET = app.config['PAYPAL_CLIENT_SECRET']
PAYPAL_MODE = app.config['PAYPAL_MODE']
PAYPAL_BASE_URL = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"

# 🔥 DECORADORES PARA CONTROL DE ACCESO (definidos una sola vez)
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
        raise Exception(f"Error obteniendo access token: {response.text}")

# Agrega esta ruta junto con las otras rutas principales
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    if query:
        # Búsqueda en nombre, descripción y categoría
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
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('register'))
        
        # Crear nuevo usuario con rol de cliente
        new_user = User(username=username, email=email, role='customer')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Iniciar sesión automáticamente después del registro
        login_user(new_user)
        
        flash('¡Registro exitoso! Bienvenido/a', 'success')
        return redirect(next_page or url_for('index'))
    
    return render_template('register.html', next=request.args.get('next', ''))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Esto elimina todos los datos de sesión
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('index'))

# Rutas principales
@app.route('/')
def index():
    featured_products = Product.query.filter_by(featured=True).all()
    featured_video = Video.query.filter_by(is_featured=True).first()
    other_videos = Video.query.filter_by(is_featured=False).all()
    return render_template(
        'index.html',
        featured_products=featured_products,
        featured_video=featured_video,
        other_videos=other_videos
    )

@app.route('/products')
def products():
    category = request.args.get('category', '')
    query = request.args.get('q', '')
    
    # Base query
    if category:
        products_query = Product.query.filter_by(category=category)
    else:
        products_query = Product.query
    
    # Aplicar búsqueda si hay query
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

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not current_user.is_authenticated:
        return jsonify({
            'success': False, 
            'message': 'Debes iniciar sesión',
            'redirect': url_for('login')
        })
    
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

@app.route('/cart')
@login_required
def cart():
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

# 🎯 NUEVAS RUTAS PARA MANEJAR EL CARRITO
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
        
        # Buscar el item en el carrito
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
        return jsonify({'success': False, 'message': f'Error al actualizar cantidad: {str(e)}'})

# 🎯 RUTA PARA ELIMINAR PRODUCTOS DEL CARRITO
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
        
        # Buscar el item en el carrito
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            
            # Recalcular el total del carrito
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
        return jsonify({'success': False, 'message': f'Error al eliminar producto: {str(e)}'})

@app.route('/checkout')
@login_required
def checkout():
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

# 🎯 RUTAS DE PAYPAL
@app.route('/save-shipping', methods=['POST'])
@login_required
def save_shipping():
    """Guardar datos de envío en la sesión"""
    try:
        shipping_data = request.get_json()
        session['shipping_data'] = shipping_data
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/create-paypal-order', methods=['POST'])
@login_required
def create_paypal_order():
    """Crear orden de pago en PayPal - EN PESOS MEXICANOS"""
    try:
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart or not cart.items:
            return jsonify({'error': 'Carrito vacío'}), 400
        
        # Calcular totales
        subtotal = sum(item.product.price * item.quantity for item in cart.items)
        tax = subtotal * 0.16  # IVA mexicano
        shipping = 5.00  # Envío en MXN (ajusta según necesites)
        total = subtotal + tax + shipping
        
        # Obtener access token
        access_token = get_paypal_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # 🎯 CAMBIO IMPORTANTE: currency_code a "MXN"
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "MXN",  # ← CAMBIADO A MXN
                        "value": f"{total:.2f}",
                        "breakdown": {
                            "item_total": {
                                "currency_code": "MXN",  # ← MXN
                                'value': f"{subtotal:.2f}"
                            },
                            "tax_total": {
                                "currency_code": "MXN",  # ← MXN
                                "value": f"{tax:.2f}"
                            },
                            "shipping": {
                                "currency_code": "MXN",  # ← MXN
                                "value": f"{shipping:.2f}"
                            }
                        }
                    },
                    "description": "Compra en Tienda de Maquillaje"
                }
            ],
            "application_context": {
                "return_url": url_for('order_confirmation', _external=True),
                "cancel_url": url_for('payment_cancelled', _external=True),
                "locale": "es-MX"  # ← Agregar locale mexicano
            }
        }
        
        response = requests.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders",
            headers=headers,
            data=json.dumps(order_data)
        )
        
        if response.status_code == 201:
            order_id = response.json()["id"]
            return jsonify({'id': order_id})
        else:
            return jsonify({'error': f'Error creando orden: {response.text}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/capture-paypal-order', methods=['POST'])
@login_required
def capture_paypal_order():
    """Capturar el pago de PayPal - CORREGIDO"""
    try:
        data = request.get_json()
        order_id = data.get('orderID')
        
        if not order_id:
            return jsonify({'error': 'ID de orden inválido'}), 400
        
        # Obtener access token
        access_token = get_paypal_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # Capturar el pago
        response = requests.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
            headers=headers)
        
        if response.status_code == 201:
            # Procesar el pedido en tu sistema
            capture_data = response.json()
            
            # Guardar información del pago
            session['last_order_total'] = float(capture_data['purchase_units'][0]['payments']['captures'][0]['amount']['value'])
            session['paypal_order_id'] = order_id
            
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Error capturando pago: {response.text}'}), 400
            
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
                         currency="MXN")  # ← Agregar moneda
@app.route('/simulate-payment', methods=['POST'])
@login_required
def simulate_payment():
    try:
        shipping_data = {
            'full_name': request.form.get('full_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'zip_code': request.form.get('zip_code'),
            'country': request.form.get('country')
        }
        
        cart = Cart.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not cart or not cart.items:
            flash('Tu carrito está vacío', 'danger')
            return redirect(url_for('checkout'))
        
        # Calcular en MXN
        subtotal = sum(item.product.price * item.quantity for item in cart.items)
        tax = subtotal * 0.16  # IVA mexicano
        shipping = 50.00  # Envío en MXN
        total = subtotal + tax + shipping
        
        order = Order(
            user_id=current_user.id,
            total=total,
            status='completed',
            payment_id=f'simulated_{random.randint(100000, 999999)}',
            payer_id=f'simulated_{current_user.id}',
            shipping_address=f"{shipping_data.get('address')}, {shipping_data.get('city')}, {shipping_data.get('state')} {shipping_data.get('zip_code')}",
            shipping_name=shipping_data.get('full_name')
        )
        db.session.add(order)
        
        for item in cart.items:
            order_item = OrderItem(
                order=order,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)
        
        cart.is_active = False
        db.session.commit()
        
        session['last_order_total'] = round(total, 2)
        
        flash('¡Pago simulado exitoso! Pedido procesado correctamente.', 'success')
        return redirect(url_for('order_confirmation'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error al procesar el pago simulado: ' + str(e), 'danger')
        return redirect(url_for('checkout'))

# 🎯 RUTAS DE ADMINISTRACIÓN (solo UNA definición por ruta)
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Obtener estadísticas y pasarlas a la plantilla
    stats = {
        'product_count': Product.query.count(),
        'user_count': User.query.count(),
        'order_count': Order.query.count(),
        'video_count': Video.query.count(),
        'venta_count': Venta.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

# Gestión de productos
@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        try:
            # Procesar la imagen
            image_filename = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    # Generar nombre seguro para el archivo
                    filename = secure_filename(file.filename)
                    # Crear nombre único para evitar colisiones
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # Guardar la imagen
                    file.save(filepath)
                    
                    # Opcional: Redimensionar la imagen si es muy grande
                    try:
                        img = Image.open(filepath)
                        if img.width > 800 or img.height > 800:
                            img.thumbnail((800, 800))
                            img.save(filepath)
                    except:
                        pass  # Si falla el redimensionado, mantener la imagen original
                    
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
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash('Producto eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar producto: {str(e)}', 'danger')
    
    return redirect(url_for('admin_products'))

# Gestión de videos
@app.route('/admin/videos')
@admin_required
def admin_videos():
    videos = Video.query.all()
    return render_template('admin/videos.html', videos=videos)

@app.route('/admin/videos/add', methods=['GET', 'POST'])
@admin_required
def admin_add_video():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        is_featured = 'is_featured' in request.form
        
        # Solo permitir subida de archivos, no URLs externas
        file_path = None
        if 'video_file' in request.files:
            file = request.files['video_file']
            if file and file.filename != '' and allowed_video_file(file.filename):
                filename = secure_filename(file.filename)
                # Guardar en la carpeta de videos específica
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file_path = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Guardar solo la ruta relativa en la base de datos
                file_path = f"videos/{unique_filename}"
            else:
                flash('Formato de video no permitido o archivo inválido', 'error')
                return render_template('admin/add_video.html')
        
        if not file_path:
            flash('Debes subir un archivo de video', 'error')
            return render_template('admin/add_video.html')
        
        # Crear nuevo video (solo con archivo, sin URL externa)
        new_video = Video(
            title=title,
            description=description,
            category=category,
            url=None,  # No permitir URLs externas
            file_path=file_path,  # Solo archivos locales
            is_featured=is_featured,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_video)
            db.session.commit()
            flash('Video agregado correctamente', 'success')
            return redirect(url_for('admin_videos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar video: {str(e)}', 'error')
    
    return render_template('admin/add_video.html')

@app.route('/admin/video/edit/<int:video_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_video(video_id):
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
                    
                    # Guardar nuevo video en carpeta de videos
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    video.file_path = f"videos/{unique_filename}"
                    video.url = None  # Eliminar cualquier URL externa
            
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
    try:
        video = Video.query.get_or_404(video_id)
        
        # Eliminar el archivo de video si existe en la carpeta de videos
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

# Gestión de ventas
@app.route('/admin/ventas')
@admin_required
def sales_record():
    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    
    # Calcular total general
    total_general = sum(venta.producto.price * venta.cantidad for venta in ventas)
    
    return render_template('admin/ventas.html', 
                         ventas=ventas,
                         total_general=total_general)




# Gestión de usuarios (solo para master admin)
@app.route('/admin/users')
@master_admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/add', methods=['GET', 'POST'])
@master_admin_required
def admin_add_user():
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

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@master_admin_required
def admin_edit_user(user_id):
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
@master_admin_required
def admin_delete_user(user_id):
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

@app.route('/init_db')
def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            if User.query.count() == 0:
                # Crear administrador maestro
                master_admin = User(username='master_admin', email='master@example.com', role='master_admin')
                master_admin.set_password('master123')
                db.session.add(master_admin)
                
                # Crear administrador regular
                admin_user = User(username='admin', email='admin@example.com', role='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                
                print("✅ Usuarios administradores creados")
            
            if Product.query.count() == 0:
                sample_products = [
                    Product(name='Labial Mate Ruby Woo', description='Labial de larga duración color rojo intenso', price=25.00, category='labios', image_url='/static/images/lipstick.jpg', stock=50),
                    Product(name='Base Studio Fix Fluid', description='Base de cobertura media a completa', price=35.00, category='rostro', image_url='/static/images/foundation.jpg', stock=30),
                    Product(name='Sombra de Ojos', description='Paleta de sombras con 9 tonos neutros', price=45.00, category='ojos', image_url='/static/images/eyeshadow.jpg', stock=25)
                ]
                
                for product in sample_products:
                    db.session.add(product)
                print("✅ Productos de ejemplo creados")
            
            db.session.commit()
            return 'Base de datos verificada correctamente'
            
        except Exception as e:
            db.session.rollback()
            return f'Error al verificar la base de datos: {str(e)}'

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404

@app.after_request
def add_header(response):
    # Evita que el navegador guarde en caché las páginas privadas
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(port=5001, debug=True)