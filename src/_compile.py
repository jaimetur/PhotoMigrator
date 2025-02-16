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

    # Convertir output_file a un objeto Path
    output_path = Path(output_file)

    # Crear los directorios padres si no existen
    if not output_path.parent.exists():
        print(f"Creando directorios necesarios para: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
    extra_files = ["./Config.ini", "../README.md", "../RELEASES-NOTES.md", "../ROADMAP.md"]
    if not input_file or not output_file:
        print("Uso: compress_file_and_folders(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"ERROR   : El archivo de entrada '{input_file}' no existe.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    script_version_dir = os.path.join(temp_dir, SCRIPT_NAME_VERSION)
    print(script_version_dir)
    zip_dir = os.path.join(script_version_dir, "Takeout")
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
        print(f"ERROR   : El archivo {file} no existe.")
        return None
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("SCRIPT_VERSION"):
                return line.split('"')[1]
    print("ERROR   : No se encontró un valor entre comillas después de SCRIPT_VERSION.")
    return None

def get_clean_version(version: str):
    # Elimina la 'v' si existe al principio
    clean_version = version.lstrip('v')
    return clean_version

def extract_release_body(input_file, output_file):
    """Extracts two specific sections from the release notes file, modifies a header, and rearranges them."""
    # Open the file and read its content into a list
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    # Initialize key indices and counter
    release_notes_index = None
    second_release_index = None
    download_section_index = None
    release_count = 0
    # Loop through lines to find the start of the "Release Notes" section and locate the second occurrence of "**Release**"
    for i, line in enumerate(lines):
        if line.strip() == "## Release Notes:":
            release_notes_index = i
        if "**Release**" in line:
            release_count += 1
            if release_count == 2:
                second_release_index = i
                break
    # Loop through lines to find the "Download Latest Version" section
    for i, line in enumerate(lines):
        if line.strip().startswith("## Download Latest Version"):
            download_section_index = i
            break
    # Validate that all required sections exist
    if release_notes_index is None or second_release_index is None or download_section_index is None:
        print("Required sections not found in the file.")
        return
    # Extract content from "## Release Notes:" to the second "**Release**"
    release_section = lines[release_notes_index:second_release_index]
    # Extract content from "## Download Latest Version" to "## Release Notes:"
    download_section = lines[download_section_index:release_notes_index]
    # Replace "Download Latest Version" with "Download this Release"
    download_section = [line.replace("Download Latest Version", "Download this Release") for line in download_section]
    # Rearrange sections: first the extracted release notes, then the modified download section
    new_content = release_section + ["\n"] + download_section
    # Write the modified content to the output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.writelines(new_content)


# def extract_release_body(input_file, output_file):
#     with open(input_file, 'r', encoding='utf-8') as infile:
#         lines = infile.readlines()
#     count = 0
#     extracted_lines = []
#     for line in lines:
#         extracted_lines.append(line)
#         if '**Release**' in line:
#             count += 1
#             if count == 2:
#                 break
#     with open(output_file, 'w', encoding='utf-8') as outfile:
#         outfile.writelines(extracted_lines)


def compile():
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
    SCRIPT_NAME = "CloudPhotoMigrator"
    SCRIPT_SOURCE_NAME = f"{SCRIPT_NAME}.py"
    SCRIPT_VERSION = get_script_version('GlobalVariables.py')
    SCRIPT_VERSION_INT = get_clean_version(SCRIPT_VERSION)
    SCRIPT_NAME_VERSION = f"{SCRIPT_NAME}_{SCRIPT_VERSION}"
    COPYRIGHT_TEXT = "(c) 2024-2025 - Jaime Tur (@jaimetur)"

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
        # Inicializamos variables
        script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
        script_zip_file = Path(f"../_built_versions/{SCRIPT_VERSION_INT}/{script_name_with_version_os_arch}.zip").resolve()
        if OPERATING_SYSTEM=='windows':
            script_compiled = f'{SCRIPT_NAME}.exe'
            script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.exe"
            add_gpth_command = f"../gpth_tool/gpth_{OPERATING_SYSTEM}.exe:gpth_tool"
        else:
            script_compiled = f'{SCRIPT_NAME}'
            script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.run"
            add_gpth_command = f"../gpth_tool/gpth_{OPERATING_SYSTEM}.bin:gpth_tool"

        print("Añadiendo paquetes necesarios al entorno Python antes de compilar...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', '../requirements.txt'])
        if OPERATING_SYSTEM=='windows':
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'windows-curses'])
        print("")
        print(f"Compilando para OS: '{OPERATING_SYSTEM}' y arquitectura: '{ARCHITECTURE}'...")
        subprocess.run([
            'pyinstaller',
            '--runtime-tmpdir', '/var/tmp',
            '--onefile',
            '--add-data', add_gpth_command,
            # '--add-data', f"../exif_tool_{OPERATING_SYSTEM}:exif_tool",
            f'{SCRIPT_SOURCE_NAME}'
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
                add_gpth_command = f'../gpth_tool/gpth_{OPERATING_SYSTEM}.exe=gpth_tool/gpth_{OPERATING_SYSTEM}.exe'
            else:
                script_compiled = f'{SCRIPT_NAME}.bin'
                script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.run"
                add_gpth_command = f'../gpth_tool/gpth_{OPERATING_SYSTEM}.bin=gpth_tool/gpth_{OPERATING_SYSTEM}.bin'
                                
            script_zip_file = Path(f"../_built_versions/{SCRIPT_VERSION_INT}/{script_name_with_version_os_arch}.zip").resolve()
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
                f'--include-data-file={add_gpth_command}',
                #f'--include-raw-dir=../gpth_tool=gpth_tool',
                # '--include-raw-dir=../exif_tool=exif_tool',
                # '--include-data-dir=../gpth_tool=gpth_tool',
                # '--include-data-dir=../exif_tool=exif_tool',
                '--include-data-file=Synology.config=Synology.config',
                '--include-data-file=../README.md=README.md'
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
    # Obtener el directorio raíz un nivel arriba del directorio de trabajo
    root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    # Calcular el path relativo
    relative_path = os.path.relpath(script_zip_file, root_dir)
    # Ruta del archivo de RELEASES-NOTES.md y CURRENT-RELEASE.md
    releases_filepath = os.path.join(root_dir,'RELEASES-NOTES.md')
    current_release_filepath = os.path.join(root_dir,'CURRENT-RELEASE.md')
    # Extraer el cuerpo de la Release actual de RELEASES-NOTES.md
    extract_release_body(releases_filepath, current_release_filepath)
    print(f"Archivo {current_release_filepath} creado correctamente.")
    # Guardar script_info.txt en un fichero de texto
    with open(os.path.join(root_dir,'script_info.txt'), 'w') as file:
        file.write(SCRIPT_VERSION_INT + '\n')
        file.write(relative_path + '\n')
    print(f'El path relativo es: {relative_path}')
    return relative_path

if __name__ == "__main__":
    result = compile()
    sys.exit(0)
