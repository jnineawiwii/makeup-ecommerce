import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    
    # ✅ CORREGIDO: Usar DATABASE_URL de Railway en producción
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://'
    ) or 'postgresql://postgres:janine123@localhost:5433/makeup_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ✅ CORREGIDO: Configuración de PayPal
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # Corregido 'sanbox' a 'sandbox'
    
    # ✅ CORREGIDO: Usar variables de entorno para credenciales seguras
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', 'AYujnXtepsxbrazDJZFCgbVpqiCNYfc5UalANOiFe6KKRUOxxLG0Ypr0Iy2orRpkOU75COKXs1cHDOSa')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', 'EHRo6iJTv3DvibwMPN4MjQqRrEIrhzexYB9JoEBYFt2UB_o86dy9KVhOzMQkacNnzEtcU1N-0XnoQs3F')

    