import psycopg2

try:
    # Intenta conectarte a PostgreSQL - REEMPLAZA 'tu_password' con tu contraseña real
    conn = psycopg2.connect(
        database="makeup_db",
        user="postgres",
        password="janine123",  # ⚠️ CAMBIA ESTO por tu password real
        host="localhost",
        port="5433"
    )
    print("✅ Conexión exitosa a PostgreSQL!")
    conn.close()
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("Posibles soluciones:")
    print("1. Verifica que la contraseña sea correcta")
    print("2. Asegúrate de que la base de datos 'makeup_db' existe")
    print("3. Verifica el archivo pg_hba.conf")