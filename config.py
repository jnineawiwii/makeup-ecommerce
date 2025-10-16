import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    
    # ✅ CONEXIÓN CORRECTA PARA RAILWAY
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if DATABASE_URL:
        # Usar la DATABASE_URL completa de Railway
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
        print(f"✅ Usando PostgreSQL de Railway: {DATABASE_URL[:50]}...")
    else:
        # Si no hay DATABASE_URL, mostrar error claro
        SQLALCHEMY_DATABASE_URI = None
        print("❌ DATABASE_URL no encontrada en Railway")
    
    # ✅ Verificar que la conexión esté configurada
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("""
        ❌ ERROR: No se pudo configurar la base de datos.
        
        Solución:
        1. Ve a Railway → Variables
        2. Verifica que exista DATABASE_URL
        3. Si no existe, agrega servicio PostgreSQL
        """)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')