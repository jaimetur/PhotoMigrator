import os
import platform
import subprocess
import shutil

def detect_and_execute():
    # Verificar el directorio actual
    current_path = os.getcwd()

    # Detect the operating system
    current_os = platform.system()
    script_name = ""
    script_path = ""

    # Determine the script name based on the OS
    if current_os == "Linux":
        script_path = r'/mnt/dev/Python_Scripts_jaimetur/PycharmProjects/OrganizeTakeoutPhotos/src'
        script_name = "compile_python_linux.sh"
    elif current_os == "Darwin":
        script_path = r'//Volumes/Dev/Python_Scripts_jaimetur/PycharmProjects/OrganizeTakeoutPhotos/src'
        script_name = "compile_python_macos.sh"
    elif current_os == "Windows":
        script_path = r'P:\Python_Scripts_jaimetur\PycharmProjects\OrganizeTakeoutPhotos\src'
        script_name = "compile_python_win64.bat"
    else:
        print(f"Unsupported operating system: {current_os}")
        return

    # Cambiamos al directorio del src
    os.chdir(script_path)

    # Construct the script path
    script_fullname = os.path.join(os.path.abspath(script_path), script_name)

    # Check if the script exists
    if not os.path.isfile(script_fullname):
        print(f"Script not found: {script_fullname}")
        return

    # Execute the script
    try:
        if current_os == "Windows":
            subprocess.run([script_fullname], shell=True, check=True)
        else:  # Linux and macOS
            subprocess.run(["bash", script_fullname], check=True)
        print(f"Successfully executed: {script_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing the script: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    # Volvemos al directorio original
    os.chdir(current_path)

    # Recorremos los archivos en la carpeta origen para buscar las extensiones ejecutables y traerlas a la carpeta destino
    extensiones = (".run", ".exe")
    for archivo in os.listdir(script_path):
        # Verificar si el archivo tiene una de las extensiones deseadas
        if archivo.endswith(extensiones):
            archivo_origen = os.path.join(script_path, archivo)
            archivo_destino = os.path.join('.', archivo)
            # Copiar el archivo
            shutil.move(archivo_origen, archivo_destino)
            print(f"Ejecutable Movido: {archivo_origen} -> {archivo_destino}")
    print("Compilación finalizada.")

if __name__ == "__main__":
    detect_and_execute()
