import os, sys
import shutil
import zipfile
import tempfile
import subprocess
import glob
import platform
from pathlib import Path
from GlobalVariables import GPTH_VERSION, EXIF_VERSION


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

def include_extrafiles_and_zip(input_file, output_file):
    extra_files_to_subdir = [
        {
            'subdir': '', # Para indicar que estos ficheros van al directorio raiz del script
            'files': ["../README.md", "../Config.ini"]
        },
        {
            'subdir': 'assets/logos',# Estos ficheros van al subdirectorio 'assets'
            'files': ["../assets/logos/logo_03.jpg"]
        },
        {
            'subdir': 'docs',# Estos ficheros van al subdirectorio 'docs'
            'files': ["../docs/RELEASES-NOTES.md", "../docs/ROADMAP.md"]
        },
        {
            'subdir': 'help',  # Estos ficheros van al subdirectorio 'help'
            'files': ["../help/*.md"]
            # 'files': ["../help/1-command-line-interface.md", "../help/2-automatic-migration.md", "../help/3-google-takeout.md", "../help/4-synology-photos.md", "../help/5-immich-photos.md", "../help/6-other-features.md"]
        }
    ]
    if not input_file or not output_file:
        print("Uso: include_extrafiles_and_zip(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"ERROR   : El archivo de entrada '{input_file}' no existe.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    script_version_dir = os.path.join(temp_dir, SCRIPT_NAME_VERSION)
    print(script_version_dir)
    os.makedirs(script_version_dir, exist_ok=True)
    shutil.copy(input_file, script_version_dir)
    # # Creamos una carpeta vacía llamada 'MyTakeout'
    # takeout_dir = os.path.join(script_version_dir, "MyTakeout")
    # print(takeout_dir)
    # os.makedirs(takeout_dir, exist_ok=True)

    # Ahora copiamos los extra files
    for subdirs_dic in extra_files_to_subdir:
        subdir = subdirs_dic.get('subdir', '')  # Si 'subdir' está vacío, copiará en el directorio raíz
        files = subdirs_dic.get('files', [])  # Garantiza que siempre haya una lista de archivos
        subdir_path = os.path.join(script_version_dir, subdir) if subdir else script_version_dir
        os.makedirs(subdir_path, exist_ok=True)  # Crea la carpeta si no existe
        for file_pattern in files:
            # Convertir la ruta relativa en una ruta absoluta
            absolute_pattern = os.path.abspath(file_pattern)
            # Buscar archivos que coincidan con el patrón
            matched_files = glob.glob(absolute_pattern)
            # Si no se encontraron archivos y la ruta es un archivo válido, tratarlo como tal
            if not matched_files and os.path.isfile(absolute_pattern):
                matched_files = [absolute_pattern]
            # Copiar los archivos al directorio de destino
            for file in matched_files:
                shutil.copy(file, subdir_path)
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


def extract_release_body(download_file, input_file, output_file):
    """Extracts two specific sections from the release notes file, modifies a header, and appends them along with additional content from another file."""
    # Open the file and read its content into a list
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    # Initialize key indices and counter
    release_notes_index = None
    second_release_index = None
    release_count = 0
    # Loop through lines to find the start of the "Release Notes" section and locate the second occurrence of "**Release**"
    for i, line in enumerate(lines):
        if line.strip() == "# Releases Notes:":
            release_notes_index = i
            lines[i] = lines[i].replace("# Releases Notes:", "# Release Notes:")
        if "## **Release**:" in line:
            release_count += 1
            if release_count == 2:
                second_release_index = i
                break
    # Validate that all release notes section exists
    if release_notes_index is None:
        print("Required sections not found in the file.")
        return
    # Extract content from "## Release Notes:" to the second "**Release**"
    if second_release_index is not None:
        release_section = lines[release_notes_index:second_release_index]
    else:
        release_section = lines[release_notes_index:]
    # Read content of download_file
    with open(download_file, 'r', encoding='utf-8') as df:
        download_content = df.readlines()
    # Append both the download file content and the release section to the output file
    # Si el archivo ya existe, lo eliminamos
    if os.path.exists(output_file):
        os.remove(output_file)
    with open(output_file, 'a', encoding='utf-8') as outfile:
        outfile.writelines(release_section)
        outfile.writelines(download_content)


def add_roadmap_to_readme(readme_file, roadmap_file):
    """
    Reemplaza el bloque ROADMAP en el archivo README con el contenido de otro archivo ROADMAP.
    Si el bloque no existe, lo inserta antes de la línea que contiene "## Credits".

    :param readme_file: Ruta al archivo README.md.
    :param roadmap_file: Ruta al archivo ROADMAP.md.
    """
    # Leer el contenido del archivo README
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_lines = f.readlines()
    # Leer el contenido del archivo ROADMAP
    with open(roadmap_file, "r", encoding="utf-8") as f:
        roadmap_content = f.read().strip() + "\n\n"  # Asegurar un salto de línea final
    # Buscar el bloque ROADMAP existente
    start_index, end_index = None, None
    for i, line in enumerate(readme_lines):
        if line.strip() == "## 📅 ROADMAP:":
            start_index = i
        if start_index is not None and line.strip() == "## 🎖️ Credits:":
            end_index = i
            break
    if start_index is not None and end_index is not None:
        # Sustituir el bloque ROADMAP existente
        print("encuentro bloque roadmap")
        updated_readme = readme_lines[:start_index] + [roadmap_content] + readme_lines[end_index:]
    else:
        # Buscar la línea donde comienza "## 🎖️ Credits" para insertar el bloque ROADMAP antes
        credits_index = next((i for i, line in enumerate(readme_lines) if line.strip() == "## 🎖️ Credits:"), None)
        if credits_index is not None:
            print ("encuentro credits pero no roadmap")
            updated_readme = readme_lines[:credits_index] + [roadmap_content] + readme_lines[credits_index:]
        else:
            # Si no se encuentra "## 🎖️ Credits", simplemente añadir al final del archivo
            print ("no encuentro credits")
            updated_readme = readme_lines + [roadmap_content]
    # Escribir el contenido actualizado en el archivo README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.writelines(updated_readme)


def main(compiler='pyinstaller'):
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global ARCHITECTURES
    global SCRIPT_NAME
    global SCRIPT_SOURCE_NAME
    global SCRIPT_VERSION
    global SCRIPT_VERSION_INT
    global SCRIPT_NAME_VERSION
    global COPYRIGHT_TEXT
    global root_dir

    # Detect the operating system and architecture
    OPERATING_SYSTEM = platform.system().lower().replace('darwin', 'macos')
    ARCHITECTURE = platform.machine().lower().replace('x86_64', 'amd64').replace('aarch64', 'arm64')
    SCRIPT_NAME = "PhotoMigrator"
    SCRIPT_SOURCE_NAME = f"{SCRIPT_NAME}.py"
    SCRIPT_VERSION = get_script_version('./src/GlobalVariables.py')
    SCRIPT_VERSION_INT = get_clean_version(SCRIPT_VERSION)
    SCRIPT_NAME_VERSION = f"{SCRIPT_NAME}_{SCRIPT_VERSION}"
    COPYRIGHT_TEXT = "(c) 2024-2025 - Jaime Tur (@jaimetur)"

    # Obtener el directorio raíz un nivel arriba del directorio de trabajo
    # root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    
    # Obtener el directorio de trabajo
    root_dir = os.getcwd()

    # Select Compiler
    # compiler = 'nuitka'
    # compiler = 'pyinstaller'

    clear_screen()
    print("")
    print("============================================================")
    print(f"INFO:    Ejecutando módulo main(compiler={compiler})...")
    print("============================================================")
    print("")

    if SCRIPT_VERSION:
        print(f"SCRIPT_VERSION encontrado: {SCRIPT_VERSION}")
    else:
        print("No se pudo obtener SCRIPT_VERSION.")

    # Borramos los ficheros y directorios temporales de compilaciones previas
    print("Borrando archivos temporales de compilaciones previas...")
    Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)
    print("")
    
    # Extraer el cuerpo de la CURRENT-RELEASE-NOTES y añadir ROADMAP al fichero README.md
    print("Extrayendo el cuerpo de la CURRENT-RELEASE-NOTES y añadiendo ROADMAP al fichero README.md...")

    # Ruta de los archivos RELEASES-NOTES.md, CURRENT-RELEASE.md, README.md y ROADMAP.md
    download_filepath = os.path.join(root_dir, 'docs', 'DOWNLOAD.md')
    releases_filepath = os.path.join(root_dir, 'docs', 'RELEASES-NOTES.md')
    current_release_filepath = os.path.join(root_dir, 'CURRENT-RELEASE.md')
    roadmap_filepath = os.path.join(root_dir, 'docs', 'ROADMAP.md')
    readme_filepath = os.path.join(root_dir,'README.md')

    # Extraer el cuerpo de la Release actual de RELEASES-NOTES.md
    extract_release_body(download_filepath, releases_filepath, current_release_filepath)
    print(f"Archivo {current_release_filepath} creado correctamente.")
    
    # Añadimos el ROADMAP en el fichero README
    add_roadmap_to_readme(readme_filepath, roadmap_filepath)
    print(f"Archivo README.md actualizado correctamente con el ROADMAP.md")

    # Calcular el path relativo
    script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"./PhotoMigrator-builts/{SCRIPT_VERSION_INT}/{script_name_with_version_os_arch}.zip").resolve()
    relative_path = os.path.relpath(script_zip_file, root_dir)

    # Guardar script_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'script_info.txt'), 'w') as file:
        file.write('ROOT_PATH=' + root_dir + '\n')
        file.write('SCRIPT_VERSION=' + SCRIPT_VERSION_INT + '\n')
        file.write('ARCHIVE_PATH=' + relative_path + '\n')
        file.write('COMPILER=' + compiler + '\n')
        print('')
        print(f'ROOT_PATH: {root_dir}')
        print(f'SCRIPT_VERSION: {SCRIPT_VERSION_INT}')
        print(f'ARCHIVE_PATH: {relative_path}')
        print(f'COMPILER: {compiler}')

    # Run Compile
    if compiler:
        ok = compile(compiler=compiler)

    return True


def compile(compiler='pyinstaller'):
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global ARCHITECTURES
    global SCRIPT_NAME
    global SCRIPT_SOURCE_NAME
    global SCRIPT_VERSION
    global SCRIPT_VERSION_INT
    global SCRIPT_NAME_VERSION
    global COPYRIGHT_TEXT
    global root_dir

    INCLUDE_EXIFTOOL = True

    # Inicializamos variables
    script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"./PhotoMigrator-builts//{SCRIPT_VERSION_INT}/{script_name_with_version_os_arch}.zip").resolve()
    gpth_tool = f"./gpth_tool/gpth-{GPTH_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext"
    # exif_tool = f"../exif_tool/exif-{EXIF_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext:exif_tool"
    if OPERATING_SYSTEM == 'windows':
        script_compiled = f'{SCRIPT_NAME}.exe'
        script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.exe"
        gpth_tool = gpth_tool.replace(".ext", ".exe")
        exif_folder = "./exif_tool/windows"
    else:
        if compiler=='pyinstaller':
            script_compiled = f'{SCRIPT_NAME}'
        else:
            script_compiled = f'{SCRIPT_NAME}.bin'
        script_compiled_with_version_os_arch_extension = f"{script_name_with_version_os_arch}.run"
        gpth_tool = gpth_tool.replace(".ext", ".bin")
        exif_folder = "./exif_tool/image"

    # Guardar script_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'script_info.txt'), 'a') as file:
        file.write('SCRIPT_COMPILED=' + script_compiled + '\n')
        file.write('GPTH_TOOL=' + gpth_tool + '\n')
        file.write('EXIF_FOLDER=' + exif_folder + '\n')
        print('')
        print(f'SCRIPT_COMPILED: {script_compiled}')
        print(f'GPTH_TOOL: {gpth_tool}')
        print(f'EXIF_FOLDER: {exif_folder}')

    print('')
    print("Adding neccesary packets to Python environment before to compile...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', './requirements.txt'])
    if OPERATING_SYSTEM == 'windows':
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'windows-curses'])
    print("")

    print(f"Compiling for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}'...")

    if compiler=='pyinstaller':
        print("")
        print("Compiling with Pyinstaller...")
        # subprocess.run([
        #     'pyinstaller',
        #     '--runtime-tmpdir', '/var/tmp',
        #     '--onefile',
        #     '--add-data', gpth_tool,
        #     # '--add-data', exif_tool,
        #     f'{SCRIPT_SOURCE_NAME}'
        # ])

        # Prepare PyInstaller for Compilation
        import PyInstaller.__main__
        pyi_args = ['./src/' + SCRIPT_SOURCE_NAME]
        pyi_args.extend(("--runtime-tmpdir", '/var/tmp'))
        pyi_args.extend(["--onefile"])
        pyi_args.extend(("--add-data", gpth_tool+':gpth_tool'))

        if INCLUDE_EXIFTOOL:
            # Now add exif_folder recursively into gpth_tool/exif_tool
            exif_folder_dest = "gpth_tool/exif_tool"
            # Añadir los archivos directamente en la carpeta raíz
            pyi_args.extend(("--add-data", f"{exif_folder}/*:{exif_folder_dest}"))
            # Recorrer todas las carpetas recursivamente
            for path in Path(exif_folder).rglob('*'):
                if path.is_dir():
                    # Verificar si contiene al menos un archivo
                    has_files = any(f.is_file() for f in path.iterdir())
                    if not has_files:
                        continue  # Saltar carpetas sin archivos
                    relative_path = path.relative_to(exif_folder).as_posix()
                    dest_path = f"{exif_folder_dest}/{relative_path}"
                    src_path = path.as_posix()
                    # Añadir todos los archivos directamente dentro de esa carpeta
                    pyi_args.extend(("--add-data", f"{src_path}/*:{dest_path}"))

        # Now Run PyInstaller with previous settings
        PyInstaller.__main__.run(pyi_args)


    elif compiler=='nuitka':
        print("")
        print("Compiling with Nuitka...")
        if ARCHITECTURE in ["amd64", "x86_64", "x64"]:
            os.environ['CC'] = 'gcc'
        elif ARCHITECTURE in ["arm64", "aarch64"]:
            os.environ['CC'] = 'aarch64-linux-gnu-gcc'
        else:
            print(f"Arquitectura desconocida: {ARCHITECTURE}")
            return False

        print("")

        command = [
            sys.executable, '-m', 'nuitka',
            f"{'./src/' + SCRIPT_SOURCE_NAME}",
            # '--standalone',
            '--onefile',
            '--onefile-no-compression',
            '--assume-yes-for-downloads',
            '--jobs=4',
            # '--mingw64',
            # '--msvc=latest', # Sorry, non-MSVC is not currently supported with Python 3.13. Newer Nuitka will work to solve this. Use Python 3.12 or option "--msvc=latest" as a workaround for now and wait
            # '--static-libpython=yes',
            '--lto=yes',
            '--remove-output',
            '--output-dir=./dist',
            f"--file-version={SCRIPT_VERSION_INT.split('-')[0]}",
            f'--copyright={COPYRIGHT_TEXT}',
            f'--include-data-file={gpth_tool}={gpth_tool}',
        ]

        if OPERATING_SYSTEM == 'linux':
            command.append(f'--onefile-tempdir-spec=/var/tmp/{script_name_with_version_os_arch}')

        if INCLUDE_EXIFTOOL:
            command.append(f'--include-data-dir={exif_folder}=./gpth_tool/exif_tool')
            # command.append('--include-data-dir=../exif_tool=exif_tool')

        # Execute Nuitka Commans
        subprocess.run(command)


    else:
        print(f"Compiler '{compiler}' not supported. Valid options are 'pyinstaller' or 'nuitka'. Compilation skipped.")
        return False

    # Move the compiled script to the parent folder
    print('')
    print(f"Moving compiled script '{script_compiled_with_version_os_arch_extension}'...")
    shutil.move(f'./dist/{script_compiled}', f'./{script_compiled_with_version_os_arch_extension}')

    # Compress the folder with the compiled script and the files/directories to include
    include_extrafiles_and_zip(f'./{script_compiled_with_version_os_arch_extension}', script_zip_file)

    # Delete temporary files and folders created during compilation
    print('')
    print("Deleting temporary compilation files...")
    Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)

    print('')
    print(f"Compilation for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}' completed successfully.")
    print(f"SCRIPT_COMPILED: {script_compiled_with_version_os_arch_extension}")
    print(f"SCRIPT_ZIPPED  : {script_zip_file}")
    print("All compilations have finished successfully.")
    print('')
    return True


if __name__ == "__main__":
    # Obtener argumento si existe
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    # Convertir a booleano
    if arg is not None:
        arg_lower = arg.lower() 
        if arg_lower in ['false', '0', 'no', 'n', 'None']:
            compiler = False
        else:
            compiler = arg
    else:
        compiler = False  # valor por defecto

    ok = main(compiler=compiler)
    if ok:
        print('COMPILATION FINISHED SUCCESSFULLY!')
    sys.exit(0)