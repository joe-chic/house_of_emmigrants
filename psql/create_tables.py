import psycopg
import sys

# Configuración de la base de datos
DB_NAME = 'house_of_emigrants'
DB_USER = 'postgres'
DB_PASS = '666'
DB_HOST = 'localhost'
DB_PORT = '5432'

def create_tables():
    try:
        conn = psycopg.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # Crear tabla emigrant_stories si no existe
        cur.execute('''
            CREATE TABLE IF NOT EXISTS emigrant_stories (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                summary TEXT,
                main_first VARCHAR(100),
                main_last VARCHAR(100),
                sex VARCHAR(20),
                marital_status VARCHAR(50),
                education_level VARCHAR(50),
                destination_city VARCHAR(100),
                destination_country VARCHAR(100),
                motive VARCHAR(100),
                travel_duration VARCHAR(100),
                return_plans VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Crear tabla admins si no existe
        cur.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id_admin SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Verificar si ya existe un admin, si no, crear uno por defecto
        cur.execute('SELECT COUNT(*) FROM admins')
        admin_count = cur.fetchone()[0]
        
        if admin_count == 0:
            cur.execute('''
                INSERT INTO admins (email, password)
                VALUES ('admin@example.com', 'admin123')
            ''')
            print('✅ Admin por defecto creado: admin@example.com / admin123')
        
        # Verificar si ya existen datos de ejemplo en emigrant_stories, si no, insertar algunos
        cur.execute('SELECT COUNT(*) FROM emigrant_stories')
        story_count = cur.fetchone()[0]
        
        if story_count == 0:
            cur.execute('''
                INSERT INTO emigrant_stories 
                (title, summary, main_first, main_last, sex, marital_status, education_level, 
                 destination_city, destination_country, motive, travel_duration, return_plans)
                VALUES 
                ('Gustaf Johansson''s Journey', 'Story of a young farmer who emigrated to Chicago in 1882.', 
                 'Gustaf', 'Johansson', 'male', 'single', 'basic', 'Chicago', 'United States', 
                 'work', '3 months', 'No'),
                ('The Lindberg Sisters', 'Three sisters who emigrated together to Minnesota to reunite with their uncle in 1895.', 
                 'Astrid', 'Lindberg', 'female', 'single', 'medium', 'Saint Paul', 'United States', 
                 'family reunion', '2 months', 'No'),
                ('Olof Larsson''s American Dream', 'A carpenter who emigrated to Boston looking for better work and fortune in 1878.', 
                 'Olof', 'Larsson', 'male', 'married', 'medium', 'Boston', 'United States', 
                 'economic', '45 days', 'After 5 years')
            ''')
            print('✅ Datos de ejemplo agregados a emigrant_stories.')
        
        conn.commit()
        cur.close()
        conn.close()
        
        print('✅ Tablas creadas exitosamente.')
        return True
        
    except Exception as e:
        print(f'❌ Error al crear tablas: {e}')
        return False

if __name__ == '__main__':
    success = create_tables()
    sys.exit(0 if success else 1) 