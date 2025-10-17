import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # Obtener DATABASE_URL de Railway
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Asegurar formato correcto para SQLAlchemy
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            print("✅ URL convertida a formato PostgreSQL")
        
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print(f"🎯 CONECTADO A: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    else:
        raise RuntimeError("🚫 DATABASE_URL no configurada en Railway")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')