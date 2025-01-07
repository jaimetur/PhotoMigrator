import os
import shutil
import zipfile
import tempfile
import subprocess
import sys
import platform
from pathlib import Path

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def comprimir_directorio(temp_dir, output_file):
    print(f"Creando el archivo comprimido: {output_file}...")
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                # Añade al zip respetando la estructura de carpetas
                zipf.write(file_path, file_path.relative_to(temp_dir))
            for dir in dirs:
                dir_path = Path(root) / dir
                # Añade directorios vacíos al zip
                if not os.listdir(dir_path):
                    zipf.write(dir_path, dir_path.relative_to(temp_dir))
    print(f"Archivo comprimido correctamente: {output_file}")


def include_file_and_folders_and_compress(input_file, output_file):
    extra_files = ["./Synology.config", "../README.md"]
    if not input_file or not output_file:
        print("Uso: compress_file_and_folders(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"Error: El archivo de entrada '{input_file}' no existe.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    script_version_dir = os.path.join(temp_dir, SCRIPT_NAME_VERSION)
    print(script_version_dir)
    zip_dir = os.path.join(script_version_dir, "Zip_files")
    print(zip_dir)
    os.makedirs(script_version_dir, exist_ok=True)
    os.makedirs(zip_dir, exist_ok=True)
    shutil.copy(input_file, script_version_dir)
    for file in extra_files:
        shutil.copy(file, script_version_dir)
    # Comprimimos el directorio temporal y después lo borramos
    comprimir_directorio(temp_dir, output_file)
    shutil.rmtree(temp_dir)


def get_script_version(file):
    if not Path(file).is_file():
        print(f"Error: El archivo {file} no existe.")
        return None
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("SCRIPT_VERSION"):
                return line.split('"')[1]
    print("Error: No se encontró un valor entre comillas después de SCRIPT_VERSION.")
    return None


def get_clean_version(version: str):
    # Elimina la 'v' si existe al principio
    clean_version = version.lstrip('v')
    return clean_version


def compile_all_so_all_architectures():
    global SCRIPT_NAME
    global SCRIPT_NAME_VERSION
    global OS
    global ARCHITECTURE
    global ARCHITECTURES
    global SCRIPT_SOURCE_NAME
    global COMPILER

    clear_screen()

    # Select Compiler
    COMPILER = 'nuitka'
    COMPILER = 'pyinstaller'

    # Detect the operating system and architecture
    OPERATING_SYSTEM = platform.system().lower().replace('darwin','macos')
    ARCHITECTURE = platform.machine().lower().replace('x86_64','amd64').replace('aarch64', 'arm64')
    SCRIPT_NAME = "OrganizeTakeoutPhotos"
    SCRIPT_SOURCE_NAME = f"{SCRIPT_NAME}.py"
    SCRIPT_VERSION = get_script_version(SCRIPT_SOURCE_NAME)
    SCRIPT_VERSION_INT = get_clean_version(SCRIPT_VERSION)
    SCRIPT_NAME_VERSION = f"{SCRIPT_NAME}_{SCRIPT_VERSION}"
    COPYRIGHT_TEXT = "(c) 2025 - Jaime Tur (@jaimetur)"

    if SCRIPT_VERSION:
        print(f"SCRIPT_VERSION encontrado: {SCRIPT_VERSION}")
    else:
        print("No se pudo obtener SCRIPT_VERSION.")

    print("Borrando archivos temporales de compilaciones previas...")
    Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)
    print("")

    if COMPILER=='pyinstaller':
        print("Añadiendo paquetes necesarios al entorno Python antes de compilar...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("")
        print(f"Compilando para OS: '{OPERATING_SYSTEM}' y arquitectura: '{ARCHITECTURE}'...")
        subprocess.run([
            'pyinstaller',
            '--runtime-tmpdir', '/var/tmp',
            '--onefile',
            '--hidden-import', 'os,sys,tqdm,argparse,platform,shutil,re,textwrap,logging,collections,csv,time,datetime,hashlib,fnmatch,requests,urllib3',
            '--add-data', f"../gpth_tool_{OPERATING_SYSTEM}:gpth_tool",
            '--add-data', f"../exif_tool_{OPERATING_SYSTEM}:exif_tool",
            f'{SCRIPT_SOURCE_NAME}'
        ])

        # Inicializamos variables
        script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
        script_zip_file = Path(f"../_built_versions/{script_name_with_version_os_arch}.zip").resolve()
        if OPERATING_SYSTEM=='windows':
            script_compiled = f'{SCRIPT_NAME}.exe'
            script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.exe"
        else:
            script_compiled = f'{SCRIPT_NAME}'
            script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.run"
        # Movemos el fichero compilado a la carpeta padre
        print(f"\nMoviendo script compilado '{script_compiled_with_version_os_arch_extension}'...")
        shutil.move(f'./dist/{script_compiled}', f'../{script_compiled_with_version_os_arch_extension}')
        # Comprimimos la carpeta con el script compilado y los ficheros y directorios a incluir
        include_file_and_folders_and_compress(f'../{script_compiled_with_version_os_arch_extension}', script_zip_file)
        # Borramos los ficheros y directorios temporales de la compilación
        print("Borrando archivos temporales de la compilación...")
        Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree('build', ignore_errors=True)
        shutil.rmtree('dist', ignore_errors=True)
        print(f"Compilación para OS: '{OPERATING_SYSTEM}' y arquitectura: '{ARCHITECTURE}' concluida con éxito.")
        print(f"Script compilado: {script_compiled_with_version_os_arch_extension}")
        print(f"Script comprimido: {script_zip_file}")

    elif COMPILER=='nuitka':
        ARCHITECTURES = ["amd64", "arm64"]
        ARCHITECTURES = ["amd64"]
        for ARCHITECTURE in ARCHITECTURES:
            script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
            if OPERATING_SYSTEM=='windows':
                script_compiled = f'{SCRIPT_NAME}.exe'
                script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.exe"
            else:
                script_compiled = f'{SCRIPT_NAME}.bin'
                script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.run"
            script_zip_file = Path(f"../_built_versions/{script_name_with_version_os_arch}.zip").resolve()
            print("")
            print(f"Compilando para OS: '{OPERATING_SYSTEM}' y arquitectura: '{ARCHITECTURE}'...")
            if ARCHITECTURE in ["amd64", "x86_64", "x64"]:
                os.environ['CC'] = 'gcc'
            elif ARCHITECTURE in ["arm64", "aarch64"]:
                os.environ['CC'] = 'aarch64-linux-gnu-gcc'
            else:
                print(f"Arquitectura desconocida: {ARCHITECTURE}")
                sys.exit(1)
            subprocess.run([
                'nuitka',
                f'{SCRIPT_SOURCE_NAME}',
                # '--standalone',
                '--onefile',
                '--onefile-no-compression',
                f'--onefile-tempdir-spec=/var/tmp/{script_name_with_version_os_arch}',
                '--jobs=4',
                '--static-libpython=yes',
                '--lto=yes',
                '--remove-output',
                '--output-dir=./dist',
                f'--file-version={SCRIPT_VERSION_INT}',
                f'--copyright={COPYRIGHT_TEXT}',
                '--include-raw-dir=../gpth_tool=gpth_tool',
                '--include-raw-dir=../exif_tool=exif_tool',
                # '--include-data-dir=../gpth_tool=gpth_tool',
                # '--include-data-dir=../exif_tool=exif_tool',
                '--include-data-file=Synology.config=Synology.config',
                '--include-data-file=README.md=README.md'
            ])
            # Movemos el fichero compilado a la carpeta padre
            print(f"\nMoviendo script compilado '{script_compiled_with_version_os_arch_extension}'...")
            shutil.move(f'./dist/{script_compiled}', f'../{script_compiled_with_version_os_arch_extension}')
            # Comprimimos la carpeta con el script compilado y los ficheros y directorios a incluir
            include_file_and_folders_and_compress(f'../{script_compiled_with_version_os_arch_extension}', script_zip_file)
            # Borramos los ficheros y directorios temporales de la compilación
            print("Borrando archivos temporales de la compilación...")
            Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
            shutil.rmtree('build', ignore_errors=True)
            shutil.rmtree('dist', ignore_errors=True)
            print(f"Compilación para OS: '{OPERATING_SYSTEM}' y arquitectura: '{ARCHITECTURE}' concluida con éxito.")
            print(f"Script compilado: {script_compiled}")
            print(f"Script comprimido: {script_zip_file}")

    print("Todas las compilaciones han finalizado correctamente.")
    return script_zip_file

if __name__ == "__main__":
    compile_all_so_all_architectures()