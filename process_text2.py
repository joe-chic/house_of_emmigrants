import os
from dataExtraction import (process_interview_file, connect_db, log_message)

def process_text2_files():
    """
    Procesa solo los archivos de texto de la carpeta "text 2" y los agrega
    a la base de datos normalizada.
    """
    text2_files_dir = os.path.join("multimedia", "text 2")
    if not os.path.isdir(text2_files_dir):
        log_message(f"Error: No se encontró el directorio: {text2_files_dir}")
        return False

    log_message(f"Procesando archivos en directorio: {text2_files_dir}")
    db_conn = connect_db()
    if not db_conn:
        log_message("Error: No se pudo conectar a la base de datos")
        return False

    files_processed = 0
    files_skipped = 0
    
    try:
        for filename in os.listdir(text2_files_dir):
            if filename.lower().endswith(".txt"):
                filepath = os.path.join(text2_files_dir, filename)
                log_message(f"Procesando archivo: {filename}")
                process_interview_file(filepath, db_conn)
                files_processed += 1
            else:
                log_message(f"Omitiendo archivo no-txt: {filename}")
                files_skipped += 1
        
        log_message(f"Procesamiento completado. Archivos procesados: {files_processed}, Omitidos: {files_skipped}")
        return True
    except Exception as e:
        log_message(f"Error durante el procesamiento: {e}")
        return False
    finally:
        if db_conn:
            db_conn.close()
            log_message("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    log_message("Iniciando script de extracción para los archivos de 'text 2'...")
    success = process_text2_files()
    if success:
        log_message("Procesamiento de archivos 'text 2' completado con éxito.")
    else:
        log_message("Procesamiento de archivos 'text 2' finalizó con errores.") 