from app import app, db
from models import User, Product, Video

def init_database():
    with app.app_context():
        print("🗑️  Eliminando tablas existentes...")
        db.drop_all()
        
        print("🔄 Creando nuevas tablas...")
        db.create_all()
        
        print("👥 Creando usuarios de ejemplo...")
        # Crear administrador maestro
        master_admin = User(username='master_admin', email='master@example.com', role='master_admin')
        master_admin.set_password('master123')
        db.session.add(master_admin)
        
        # Crear administrador regular
        admin_user = User(username='admin', email='admin@example.com', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Crear usuario normal
        customer = User(username='cliente', email='cliente@example.com', role='customer')
        customer.set_password('cliente123')
        db.session.add(customer)
        
        print("🛍️ Creando productos de ejemplo...")
        sample_products = [
            Product(
                name='Labial Mate Ruby Woo', 
                description='Labial de larga duración color rojo intenso', 
                price=25.00, 
                category='labios', 
                image_url='/static/images/lipstick.jpg', 
                stock=50,
                featured=True
            ),
            Product(
                name='Base Studio Fix Fluid', 
                description='Base de cobertura media a completa', 
                price=35.00, 
                category='rostro', 
                image_url='/static/images/foundation.jpg', 
                stock=30,
                featured=True
            ),
            Product(
                name='Sombra de Ojos', 
                description='Paleta de sombras con 9 tonos neutros', 
                price=45.00, 
                category='ojos', 
                image_url='/static/images/eyeshadow.jpg', 
                stock=25,
                featured=False
            )
        ]
        
        for product in sample_products:
            db.session.add(product)
        
        print("🎥 Creando videos de ejemplo...")
        sample_videos = [
            Video(
                title='Tutorial de Maquillaje Básico',
                description='Aprende las técnicas básicas de maquillaje para principiantes',
                category='Tutorial',
                url='https://www.youtube.com/embed/6C8O6H-ZY5c',
                is_featured=True
            ),
            Video(
                title='Review de Productos MAC',
                description='Análisis de los mejores productos de MAC Cosmetics',
                category='Review',
                url='https://www.youtube.com/embed/otro_video',
                is_featured=False
            )
        ]
        
        for video in sample_videos:
            db.session.add(video)
        
        db.session.commit()
        print("✅ Base de datos inicializada exitosamente!")
        print("📋 Datos creados:")
        print(f"   - Usuarios: {User.query.count()}")
        print(f"   - Productos: {Product.query.count()}")
        print(f"   - Videos: {Video.query.count()}")
        print("\n🔑 Credenciales de acceso:")
        print("   Master Admin: usuario=master_admin, contraseña=master123")
        print("   Admin: usuario=admin, contraseña=admin123")
        print("   Cliente: usuario=cliente, contraseña=cliente123")

if __name__ == '__main__':
    init_database()