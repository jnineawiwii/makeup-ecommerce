import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:janine123@localhost:5433/makeup_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de PayPal - MODO PRODUCCIÓN
    PAYPAL_MODE = 'sanbox'  # Cambiado a 'live' para producción
    
    # REEMPLAZA ESTO CON TUS CREDENCIALES REALES
    PAYPAL_CLIENT_ID = 'AYujnXtepsxbrazDJZFCgbVpqiCNYfc5UalANOiFe6KKRUOxxLG0Ypr0Iy2orRpkOU75COKXs1cHDOSa'  # ← ¡ESTE ES EL PROBLEMA!
    PAYPAL_CLIENT_SECRET = 'EHRo6iJTv3DvibwMPN4MjQqRrEIrhzexYB9JoEBYFt2UB_o86dy9KVhOzMQkacNnzEtcU1N-0XnoQs3F'