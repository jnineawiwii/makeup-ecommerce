import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # ✅ VERIFICACIÓN SEGURA - Sin bloquear el inicio
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Convierte postgres:// a postgresql:// si es necesario
        if DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print("✅ Conectado a PostgreSQL de Railway")
    else:
        # ⚠️ TEMPORAL: Usar SQLite para diagnóstico
        SQLALCHEMY_DATABASE_URI = 'sqlite:///makeup.db'
        print("⚠️  Usando SQLite temporal para diagnóstico")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración PayPal
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')