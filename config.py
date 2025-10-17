import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # ✅ CORREGIR: Railway usa 'postgres://' no 'postgresql://'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Railway usa 'postgres://' pero SQLAlchemy necesita 'postgresql://'
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            print("✅ CONVERTIDO A POSTGRESQL PARA SQLALCHEMY")
        
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print("✅ CONECTADO A POSTGRESQL DE RAILWAY")
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///makeup.db'
        print("⚠️  USANDO SQLITE TEMPORAL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')