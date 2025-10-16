import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # ✅ CONEXIÓN DIRECTA A POSTGRESQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print("✅ CONECTADO A POSTGRESQL DE RAILWAY")
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///makeup.db'
        print("⚠️  USANDO SQLITE TEMPORAL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False