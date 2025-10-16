import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    
    # ✅ DEBE USAR POSTGRESQL DE RAILWAY
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
        print("✅ Conectado a PostgreSQL de Railway")
    else:
        # ❌ NO usar SQLite - esto causa el error
        raise ValueError("❌ DATABASE_URL no encontrada. Verifica que PostgreSQL esté conectado en Railway")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')