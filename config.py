import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    
    # ✅ USAR SOLO DATABASE_URL DE RAILWAY
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://'
    )
    
    # ✅ Si no hay DATABASE_URL, mostrar error claro
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("❌ DATABASE_URL no está configurada en Railway")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')