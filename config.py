import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # ✅ USAR LAS VARIABLES INDIVIDUALES DE RAILWAY
    db_host = os.environ.get('PGHOST')
    db_port = os.environ.get('PGPORT')
    db_name = os.environ.get('PGDATABASE')
    db_user = os.environ.get('PGUSER')
    db_password = os.environ.get('PGPASSWORD')
    
    if all([db_host, db_port, db_name, db_user, db_password]):
        SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print("✅ CONECTADO A POSTGRESQL DE RAILWAY (variables individuales)")
    else:
        # Fallback a DATABASE_URL directa
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
            print("✅ CONECTADO A POSTGRESQL DE RAILWAY (URL directa)")
        else:
            SQLALCHEMY_DATABASE_URI = 'sqlite:///makeup.db'
            print("⚠️  USANDO SQLITE TEMPORAL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')