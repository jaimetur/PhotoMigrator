import os
def change_working_dir():
    """ Definir la ruta de trabajo deseada """
    WORKING_DIR = r"R:\jaimetur\CloudPhotoMigrator"
    WORKING_DIR = r"R:\jaimetur\CloudPhotoMigrator_|@#~€"
    # Verificar si la carpeta existe y cambiar a ella si existe
    if os.path.exists(WORKING_DIR) and os.path.isdir(WORKING_DIR):
        os.chdir(WORKING_DIR)
        current_directory = os.getcwd()
        print(f"INFO    : Directorio cambiado a: {os.getcwd()}")