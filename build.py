import os, sys
import shutil
import zipfile
import tempfile
import subprocess
import glob
import platform
from pathlib import Path

# Add 'src/' folder to path to import any module from 'src/'.
current_dir = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(current_dir, "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from GlobalVariables import GPTH_VERSION, EXIF_VERSION, INCLUDE_EXIF_TOOL, COPYRIGHT_TEXT, COMPILE_IN_ONE_FILE
from Utils import zip_folder, unzip_to_temp, unzip, unzip_flatten, clear_screen, print_arguments_pretty, get_os, get_arch

def include_extrafiles_and_zip(input_file, output_file):
    extra_files_to_subdir = [
        {
            'subdir': '', # Para indicar que estos ficheros van al directorio raiz del script
            'files': ["./README.md", "./Config.ini"]
        },
        {
            'subdir': 'assets/logos',# Estos ficheros van al subdirectorio 'assets'
            'files': ["./assets/logos/logo.jpg"]
        },
        {
            'subdir': 'docs',# Estos ficheros van al subdirectorio 'docs'
            'files': ["./docs/RELEASES-NOTES.md", "./docs/ROADMAP.md"]
        },
        {
            'subdir': 'help',  # Estos ficheros van al subdirectorio 'help'
            'files': ["./help/*.md"]
            # 'files': ["./help/1-command-line-interface.md", "./help/2-automatic-migration.md", "./help/3-google-takeout.md", "./help/4-synology-photos.md", "./help/5-immich-photos.md", "./help/6-other-features.md"]
        }
    ]
    if not input_file or not output_file:
        print("Uso: include_extrafiles_and_zip(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"ERROR   : The input file '{input_file}' does not exists.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    script_version_dir = os.path.join(temp_dir, SCRIPT_NAME_VERSION)
    print(script_version_dir)
    os.makedirs(script_version_dir, exist_ok=True)
    shutil.copy(input_file, script_version_dir)

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
    zip_folder(temp_dir, output_file)
    shutil.rmtree(temp_dir)

def get_script_version(file):
    if not Path(file).is_file():
        print(f"ERROR   : The file {file} does not exists.")
        return None
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("SCRIPT_VERSION"):
                return line.split('"')[1]
    print("ERROR   : Not found any value between colons after SCRIPT_VERSION.")
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
        print("'ROADMAP' block found")
        updated_readme = readme_lines[:start_index] + [roadmap_content] + readme_lines[end_index:]
    else:
        # Buscar la línea donde comienza "## 🎖️ Credits" para insertar el bloque ROADMAP antes
        credits_index = next((i for i, line in enumerate(readme_lines) if line.strip() == "## 🎖️ Credits:"), None)
        if credits_index is not None:
            print ("'CREDITS' block found but 'ROADMAP' block not found")
            updated_readme = readme_lines[:credits_index] + [roadmap_content] + readme_lines[credits_index:]
        else:
            # Si no se encuentra "## 🎖️ Credits", simplemente añadir al final del archivo
            print ("'CREDITS' block not found")
            updated_readme = readme_lines + [roadmap_content]
    # Escribir el contenido actualizado en el archivo README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.writelines(updated_readme)


def main(compiler='pyinstaller', compile_in_one_file=COMPILE_IN_ONE_FILE):
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global SCRIPT_NAME
    global SCRIPT_SOURCE_NAME
    global SCRIPT_VERSION
    global SCRIPT_VERSION_WITHOUT_V
    global SCRIPT_NAME_VERSION
    global root_dir

    # Detect the operating system and architecture
    # OPERATING_SYSTEM = platform.system().lower().replace('darwin', 'macos')
    # ARCHITECTURE = platform.machine().lower().replace('x86_64', 'amd64').replace('aarch64', 'arm64')
    # ARCHITECTURE = platform.machine().lower().replace('amd64', 'x64').replace('aarch64', 'arm64')
    OPERATING_SYSTEM = get_os(use_logger=False)
    ARCHITECTURE = get_arch(use_logger=False)
    SCRIPT_NAME = "PhotoMigrator"
    SCRIPT_SOURCE_NAME = f"{SCRIPT_NAME}.py"
    SCRIPT_VERSION = get_script_version('./src/GlobalVariables.py')
    SCRIPT_VERSION_WITHOUT_V = get_clean_version(SCRIPT_VERSION)
    SCRIPT_NAME_VERSION = f"{SCRIPT_NAME}_{SCRIPT_VERSION}"

    # Obtener el directorio raíz un nivel arriba del directorio de trabajo
    # root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    
    # Obtener el directorio de trabajo
    root_dir = os.getcwd()

    clear_screen()
    print("")
    print("=================================================================================================")
    print(f"INFO:    Running Main Module - main(compiler={compiler}, compile_in_one_file={compile_in_one_file})...")
    print("=================================================================================================")
    print("")

    # print("Adding neccesary packets to Python environment before to compile...")
    # subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    # subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', './requirements.txt'])
    # if OPERATING_SYSTEM == 'windows' and ARCHITECTURE == 'x64)':
    #     subprocess.run([sys.executable, '-m', 'pip', 'install', 'windows-curses'])
    # print("")

    if SCRIPT_VERSION:
        print(f"SCRIPT_VERSION found: {SCRIPT_VERSION_WITHOUT_V}")
    else:
        print("Caanot find SCRIPT_VERSION.")

    # Extraer el cuerpo de la CURRENT-RELEASE-NOTES y añadir ROADMAP al fichero README.md
    print("Extracting body of CURRENT-RELEASE-NOTES and adding ROADMAP to file README.md...")

    # Ruta de los archivos RELEASES-NOTES.md, CURRENT-RELEASE.md, README.md y ROADMAP.md
    download_filepath = os.path.join(root_dir, 'docs', 'DOWNLOAD.md')
    releases_filepath = os.path.join(root_dir, 'docs', 'RELEASES-NOTES.md')
    current_release_filepath = os.path.join(root_dir, 'CURRENT-RELEASE.md')
    roadmap_filepath = os.path.join(root_dir, 'docs', 'ROADMAP.md')
    readme_filepath = os.path.join(root_dir,'README.md')

    # Extraer el cuerpo de la Release actual de RELEASES-NOTES.md
    extract_release_body(download_filepath, releases_filepath, current_release_filepath)
    print(f"File '{current_release_filepath}' created successfully!.")

    # Añadimos el ROADMAP en el fichero README
    add_roadmap_to_readme(readme_filepath, roadmap_filepath)
    print(f"File 'README.md' updated successfully with ROADMAP.md")

    # Calcular el path relativo
    script_name_with_version_os_arch = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"./PhotoMigrator-builds/{SCRIPT_VERSION_WITHOUT_V}/{script_name_with_version_os_arch}.zip").resolve()
    archive_path_relative = os.path.relpath(script_zip_file, root_dir)

    # Guardar build_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'build_info.txt'), 'w') as file:
        file.write('OPERATING_SYSTEM=' + OPERATING_SYSTEM + '\n')
        file.write('ARCHITECTURE=' + ARCHITECTURE + '\n')
        file.write('SCRIPT_NAME=' + SCRIPT_NAME + '\n')
        file.write('SCRIPT_VERSION=' + SCRIPT_VERSION_WITHOUT_V + '\n')
        file.write('ROOT_PATH=' + root_dir + '\n')
        file.write('ARCHIVE_PATH=' + archive_path_relative + '\n')
        print('')
        print(f'OPERATING_SYSTEM: {OPERATING_SYSTEM}')
        print(f'ARCHITECTURE: {ARCHITECTURE}')
        print(f'SCRIPT_NAME: {SCRIPT_NAME}')
        print(f'SCRIPT_VERSION: {SCRIPT_VERSION_WITHOUT_V}')
        print(f'ROOT_PATH: {root_dir}')
        print(f'ARCHIVE_PATH: {archive_path_relative}')

    ok = True
    # Run Compile
    if compiler:
        ok = compile(compiler=compiler, compile_in_one_file=compile_in_one_file)
    return ok

def compile(compiler='pyinstaller', compile_in_one_file=COMPILE_IN_ONE_FILE):
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global SCRIPT_NAME
    global SCRIPT_SOURCE_NAME
    global SCRIPT_VERSION
    global SCRIPT_VERSION_WITHOUT_V
    global SCRIPT_NAME_VERSION
    global root_dir

    # Inicializamos variables
    SCRIPT_NAME_WITH_VERSION_OS_ARCH = f"{SCRIPT_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"PhotoMigrator-builts//{SCRIPT_VERSION_WITHOUT_V}/{SCRIPT_NAME_WITH_VERSION_OS_ARCH}.zip").resolve()
    splash_image = "assets/logos/logo.png" # Splash image for windows
    gpth_tool = f"gpth_tool/gpth-{GPTH_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext"
    exif_folder_tmp = "tmp/exif_tool"
    exif_folder_dest = "gpth_tool"
    # exif_tool = f"../exif_tool/exif-{EXIF_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext:exif_tool"
    if OPERATING_SYSTEM == 'windows':
        script_compiled = f'{SCRIPT_NAME}.exe'
        script_compiled_with_version_os_arch_extension = f"{SCRIPT_NAME_WITH_VERSION_OS_ARCH}.exe"
        gpth_tool = gpth_tool.replace(".ext", ".exe")
        exif_tool_zipped = "exif_tool/windows.zip"
    else:
        if compiler=='pyinstaller':
            script_compiled = f'{SCRIPT_NAME}'
        else:
            script_compiled = f'{SCRIPT_NAME}.bin'
        script_compiled_with_version_os_arch_extension = f"{SCRIPT_NAME_WITH_VERSION_OS_ARCH}.run"
        gpth_tool = gpth_tool.replace(".ext", ".bin")
        exif_tool_zipped = "exif_tool/others.zip"

    # Guardar build_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'build_info.txt'), 'a') as file:
        file.write('COMPILER=' + str(compiler) + '\n')
        file.write('SCRIPT_COMPILED=' + os.path.abspath(script_compiled_with_version_os_arch_extension) + '\n')
        file.write('GPTH_TOOL=' + gpth_tool + '\n')
        file.write('EXIF_TOOL=' + exif_tool_zipped + '\n')
        print('')
        print(f'COMPILER: {compiler}')
        print(f'COMPILE_IN_ONE_FILE: {compile_in_one_file}')
        print(f'SCRIPT_COMPILED: {script_compiled}')
        print(f'GPTH_TOOL: {gpth_tool}')
        print(f'EXIF_TOOL: {exif_tool_zipped}')

    print("")
    print("=================================================================================================")
    print(f"INFO:    Compiling with '{compiler}' for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}'...")
    print("=================================================================================================")
    print("")

    success = False
    # ===============================================================================================================================================
    # COMPILE WITH PYINSTALLER...
    # ===============================================================================================================================================
    if compiler=='pyinstaller':
        print("Compiling with Pyinstaller...")
        import PyInstaller.__main__

        # Build and Dist Folders for Pyinstaller
        build_path = "./pyinstaller_build"
        dist_path = "./pyinstaller_dist"

        # Add _pyinstaller suffix to exif_folder_tmp to avoid conflict if both commpiler are running in parallel
        exif_folder_tmp = exif_folder_tmp.replace('tmp', 'pyinstaller_tmp')

        # Borramos los ficheros y directorios temporales de compilaciones previas
        print("Removing temporary files from previous compilations...")
        Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare pyinstaller_command
        pyinstaller_command = ['./src/' + SCRIPT_SOURCE_NAME]
        if compile_in_one_file:
            pyinstaller_command.extend(["--onefile"])
        else:
            pyinstaller_command.extend(['--onedir'])
        if OPERATING_SYSTEM == 'windows':
            pyinstaller_command.extend(("--splash", splash_image))
        pyinstaller_command.extend(["--noconfirm"])
        pyinstaller_command.extend(("--distpath", dist_path))
        pyinstaller_command.extend(("--workpath", build_path))
        pyinstaller_command.extend(("--add-data", gpth_tool + ':gpth_tool'))
        if INCLUDE_EXIF_TOOL:
            # First delete exif_folder_tmp if exists
            shutil.rmtree(exif_folder_tmp, ignore_errors=True)
            # Unzip Exif_tool and include it to compiled binary with Pyinstaller
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            # unzip(exif_tool_zipped, exif_folder_tmp)
            exif_folder_tmp = unzip_to_temp(exif_tool_zipped)
            # Asegura permisos de ejecución para exiftool (y opcionalmente otros binarios)
            import stat
            exiftool_bin = Path(exif_folder_tmp) / "exiftool"
            if exiftool_bin.exists():
                exiftool_bin.chmod(exiftool_bin.stat().st_mode | stat.S_IEXEC)
            # Añadir los archivos directamente en la carpeta raíz
            pyinstaller_command.extend(("--add-data", f"{exif_folder_tmp}:{exif_folder_dest}"))
            # Recorrer todas las carpetas recursivamente
            for path in Path(exif_folder_tmp).rglob('*'):
                if path.is_dir():
                    # Verificar si contiene al menos un archivo
                    has_files = any(f.is_file() for f in path.iterdir())
                    if not has_files:
                        continue  # Saltar carpetas sin archivos
                    relative_path = path.relative_to(exif_folder_tmp).as_posix()
                    dest_path = f"{exif_folder_dest}/{relative_path}"
                    src_path = path.as_posix()
                    # Añadir todos los archivos directamente dentro de esa carpeta
                    pyinstaller_command.extend(("--add-data", f"{src_path}:{dest_path}"))
        if OPERATING_SYSTEM == 'linux':
            pyinstaller_command.extend(("--runtime-tmpdir", '/var/tmp'))

        # Now Run PyInstaller with previous settings
        print_arguments_pretty(pyinstaller_command, title="Pyinstaller Arguments", use_logger=False)

        try:
            PyInstaller.__main__.run(pyinstaller_command)
            print("[OK] PyInstaller finished successfully.")
            success = True
        except SystemExit as e:
            if e.code == 0:
                print("[OK] PyInstaller finished successfully.")
                success = True
            else:
                print(f"[ERROR] PyInstaller failed with error code: {e.code}")

    # ===============================================================================================================================================
    # COMPILE WITH NUITKA...
    # ===============================================================================================================================================
    elif compiler=='nuitka':
        print("Compiling with Nuitka...")
        # if ARCHITECTURE in ["amd64", "x86_64", "x64"]:
        #     os.environ['CC'] = 'gcc'
        # elif ARCHITECTURE in ["arm64", "aarch64"]:
        #     if sys.platform == "linux":
        #         os.environ['CC'] = 'aarch64-linux-gnu-gcc'
        #     elif sys.platform == "darwin":
        #         os.environ['CC'] = 'clang'  # explícito para macOS
        # else:
        #     print(f"Unknown architecture: {ARCHITECTURE}")
        #     return False
        # print("")

        # Build and Dist Folders for Nuitka
        dist_path = "./nuitka_dist"
        build_path = f"{dist_path}/{SCRIPT_NAME}.build"

        # Add _nuitka suffix to exif_folder_tmp to avoid conflict if both commpiler are running in parallel
        exif_folder_tmp = exif_folder_tmp.replace('tmp', 'nuitka_tmp')

        # Borramos los ficheros y directorios temporales de compilaciones previas
        print("Removing temporary files from previous compilations...")
        Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare nuitka_command
        nuitka_command = [
            sys.executable, '-m', 'nuitka',
            f"{'./src/' + SCRIPT_SOURCE_NAME}",
        ]
        if compile_in_one_file:
            nuitka_command.extend(['--onefile'])
            # nuitka_command.append('--onefile-no-compression)
            # if OPERATING_SYSTEM == 'windows':
            #     nuitka_command.extend([f'--onefile-windows-splash-screen-image={splash_image}'])
        else:
            nuitka_command.extend(['--standalone'])

        nuitka_command.extend([
            '--jobs=4',
            '--assume-yes-for-downloads',
            '--enable-plugin=tk-inter',
            '--disable-cache=ccache',
            '--lto=yes',
            # '--remove-output',
            f'--output-dir={dist_path}',
            f"--file-version={SCRIPT_VERSION_WITHOUT_V.split('-')[0]}",
            f'--copyright={COPYRIGHT_TEXT}',
            f'--include-data-file={gpth_tool}={gpth_tool}',
        ])
        if INCLUDE_EXIF_TOOL:
            # First delete exif_folder_tmp if exists
            shutil.rmtree(exif_folder_tmp, ignore_errors=True)
            # Unzip Exif_tool and include it to compiled binary with Nuitka
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            # unzip(exif_tool_zipped, exif_folder_tmp)
            exif_folder_tmp = unzip_to_temp(exif_tool_zipped)
            # Dar permiso de ejecución a exiftool
            import stat
            for path in Path(exif_folder_tmp).rglob('*'):
                if path.is_file() and path.name == "exiftool":
                    path.chmod(path.stat().st_mode | stat.S_IEXEC)
            nuitka_command.extend([f'--include-data-files={exif_folder_tmp}={exif_folder_dest}/=**/*.*'])
            nuitka_command.extend([f'--include-data-dir={exif_folder_tmp}={exif_folder_dest}'])
            # nuitka_command.extend(['--include-data-dir=../exif_tool=exif_tool'])
        if OPERATING_SYSTEM == 'linux':
            nuitka_command.extend([f'--onefile-tempdir-spec=/var/tmp/{SCRIPT_NAME_WITH_VERSION_OS_ARCH}'])
        # Now Run Nuitka with previous settings
        print_arguments_pretty(nuitka_command, title="Nuitka Arguments", use_logger=False)
        result = subprocess.run(nuitka_command)
        success = (result.returncode == 0)
        if not success:
            print(f"[ERROR] Nuitka failed with code: {result.returncode}")

    else:
        print(f"Compiler '{compiler}' not supported. Valid options are 'pyinstaller' or 'nuitka'. Compilation skipped.")
        return False

    # ===============================================================================================================================================
    # PACKAGING AND CLEANING ACTIONS...
    # ===============================================================================================================================================
    # Now checks if compilations finished successfully, if not, exit.
    if success:
        print("[OK] Compilation process finished successfully.")
    else:
        print("[ERROR] There was some error during compilation process.")
        sys.exit(-1)

    # Script Compiled Absolute Path
    script_compiled_abs_path = ''
    if compiler == 'pyinstaller':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{script_compiled}")
    elif compiler == 'nuitka':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{SCRIPT_NAME}.dist/{script_compiled}")

    # Move the compiled script to the parent folder
    if compile_in_one_file:
        print('')
        print(f"Moving compiled script '{script_compiled_with_version_os_arch_extension}'...")
        shutil.move(f'{dist_path}/{script_compiled}', f'./{script_compiled_with_version_os_arch_extension}')
        # Compress the folder with the compiled script and the files/directories to include
        include_extrafiles_and_zip(f'./{script_compiled_with_version_os_arch_extension}', script_zip_file)
        script_compiled_abs_path = os.path.abspath(script_compiled_with_version_os_arch_extension)

    # Delete temporary files and folders created during compilation
    print('')
    print("Deleting temporary compilation files...")
    shutil.rmtree(exif_folder_tmp, ignore_errors=True)
    shutil.rmtree("tmp_pyinstaller", ignore_errors=True)
    shutil.rmtree("tmp_nuitka", ignore_errors=True)
    Path(f"{SCRIPT_NAME}.spec").unlink(missing_ok=True)
    Path(f"nuitka-crash-report.xml").unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)
    if compile_in_one_file:
        shutil.rmtree(dist_path, ignore_errors=True)
    print("Temporary compilation files successfully deleted!")

    print('')
    print("=================================================================================================")
    print(f"Compilation for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}' completed successfully!!!")
    print('')
    print(f"SCRIPT_COMPILED: {script_compiled_abs_path}")
    print(f"SCRIPT_ZIPPED  : {script_zip_file}")
    print('')
    print("All compilations have finished successfully.")
    print("=================================================================================================")
    print('')
    return True


if __name__ == "__main__":
    # Obtener argumentos si existen
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None

    # Convertir a booleano
    if arg1 is not None:
        arg_lower = arg1.lower()
        if arg_lower in ['false', '-false', '--false', '0', 'no', 'n', 'none', '-none', '--none', 'no-compile', '-no-compile', '--no-compile', 'no-compiler', '-no-compiler', '--no-compiler']:
            compiler = None
        elif arg_lower in ['pyinstaller', '-pyinstaller', '--pyinstaller']:
            compiler = 'pyinstaller'
        elif arg_lower in ['nuitka', '-nuitka', '--nuitka']:
            compiler = 'nuitka'
        else:
            print (f"Unrecognized compiler: '{arg1}'. Using 'PyInstaller' by default...")
            compiler = 'pyinstaller'
    else:
        compiler = False  # valor por defecto

    # Convertir a booleano
    if arg2 is not None:
        arg_lower = arg2.lower()
        if arg_lower in ['false', '-false', '--false', '0', 'no', 'n', 'none', '-none', '--none', 'onedir', '-onedir', '--onedir', 'standalone', '-standalone', '--standalone', 'no-onefile', '-no-onefile', '--no-onefile']:
            onefile = False
        else:
            onefile = True
    else:
        onefile = True  # valor por defecto

    ok = main(compiler=compiler, compile_in_one_file=onefile)
    if ok:
        print('INFO    : COMPILATION FINISHED SUCCESSFULLY!')
        sys.exit(0)
    else:
        print('ERROR   : BUILD FINISHED WITH ERRORS!')
        sys.exit(-1)