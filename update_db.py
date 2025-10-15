# update_db.py
from app import app, db
from models import Video

with app.app_context():
    try:
        # Agregar la columna is_featured si no existe
        db.engine.execute('ALTER TABLE videos ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE')
        print("✅ Columna 'is_featured' agregada a la tabla videos")
        
        # Actualizar todos los videos existentes para que no sean destacados por defecto
        Video.query.update({Video.is_featured: False})
        db.session.commit()
        print("✅ Todos los videos actualizados con is_featured = False")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()