import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-temporal-makeup-ecommerce'
    
    # ✅ VERIFICACIÓN SEGURA - Sin bloquear el inicio
   # ✅ FORZAR DETECCIÓN DE DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')

print("🔍 CONFIGURACIÓN DE BASE DE DATOS:")
print(f"DATABASE_URL encontrada: {bool(DATABASE_URL)}")

if DATABASE_URL:
    # Asegurar formato postgresql://
    if DATABASE_URL.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    print("✅ CONECTADO A POSTGRESQL DE RAILWAY")
else:
    # ❌ ERROR CRÍTICO - No usar SQLite
    print("❌ ERROR: DATABASE_URL no encontrada")
    print("Variables de entorno disponibles:", [k for k in os.environ.keys() if 'DATABASE' in k or 'POSTGRES' in k])
    # Usar SQLite temporalmente pero con advertencia clara
    SQLALCHEMY_DATABASE_URI = 'sqlite:///makeup.db'
    print("⚠️  ⚠️  ⚠️  USANDO SQLITE TEMPORAL - CONFIGURAR DATABASE_URL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración PayPal
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')