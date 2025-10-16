import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    
    # ✅ DEBE USAR POSTGRESQL DE RAILWAY
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
        print("✅ Usando PostgreSQL de Railway")
    else:
        # ❌ NO usar SQLite en producción
        SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:janine123@host:5432/makeup_db'
        print("⚠️  Usando PostgreSQL directo")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')