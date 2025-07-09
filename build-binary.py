import os
import sys

# ------------------------------------------------------------
# Add 'src/' folder to path to import any module from 'src/'.
current_dir = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(current_dir, "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# ------------------------------------------------------------

import shutil
import tempfile
import subprocess
import glob
from pathlib import Path

from Core.GlobalVariables import TOOL_NAME, TOOL_VERSION, GPTH_VERSION, INCLUDE_EXIF_TOOL, COPYRIGHT_TEXT, COMPILE_IN_ONE_FILE, FOLDERNAME_GPTH, FOLDERNAME_EXIFTOOL
from Utils.GeneralUtils import clear_screen, print_arguments_pretty, get_os, get_arch, ensure_executable
from Utils.FileUtils import unzip_to_temp, zip_folder
from Utils.StandaloneUtils import resolve_external_path

global OPERATING_SYSTEM
global ARCHITECTURE
global TOOL_SOURCE_NAME
global TOOL_VERSION_WITHOUT_V
global TOOL_NAME_VERSION
global root_dir
global tool_name_with_version_os_arch
global script_zip_file
global archive_path_relative

def include_extrafiles_and_zip(input_file, output_file):
    extra_files_to_subdir = [
        {
            'subdir': '', # Para indicar que estos ficheros van al directorio raiz del script
            'files': ["./Config.ini"]
        },
        {
            'subdir': 'assets/logos',# Estos ficheros van al subdirectorio 'assets'
            # 'files': ["./assets/logos/logo.png"]
            'files': ["./assets/logos/logo_17*.png"]
        },
        {
            'subdir': 'docs',# Estos ficheros van al subdirectorio 'docs'
            'files': ["./README.md", "./CHANGELOG.md", "./ROADMAP.md", "./DOWNLOAD.md", "./CONTRIBUTING.md", "./CODE_OF_CONDUCT.md", "./LICENSE"]
        },
        {
            'subdir': 'help',  # Estos ficheros van al subdirectorio 'help'
            'files': ["./help/*.md"]
        }
    ]
    if not input_file or not output_file:
        print("Uso: include_extrafiles_and_zip(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"ERROR   : The input file '{input_file}' does not exists.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    tool_version_dir = os.path.join(temp_dir, TOOL_NAME_VERSION)
    print(tool_version_dir)
    os.makedirs(tool_version_dir, exist_ok=True)
    shutil.copy(input_file, tool_version_dir)

    # Ahora copiamos los extra files
    for subdirs_dic in extra_files_to_subdir:
        subdir = subdirs_dic.get('subdir', '')  # Si 'subdir' está vacío, copiará en el directorio raíz
        files = subdirs_dic.get('files', [])  # Garantiza que siempre haya una lista de archivos
        subdir_path = os.path.join(tool_version_dir, subdir) if subdir else tool_version_dir
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

def get_tool_version(file):
    if not Path(file).is_file():
        print(f"ERROR   : The file {file} does not exists.")
        return None
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("TOOL_VERSION"):
                return line.split('"')[1]
    print("ERROR   : Not found any value between colons after TOOL_VERSION.")
    return None

def get_clean_version(version: str):
    # Elimina la 'v' si existe al principio
    clean_version = version.lstrip('v')
    return clean_version

def extract_release_body(input_file, output_file, download_file):
    """Extracts two specific sections from the changelog file, modifies a header, and appends them along with additional content from another file."""
    # Open the file and read its content into a list
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    # Initialize key indices and counter
    changelog_index = None
    second_release_index = None
    release_count = 0
    # Loop through lines to find the start of the "Changelog" section and locate the second occurrence of "## Release"
    for i, line in enumerate(lines):
        if line.strip() == "# 🗓️ CHANGELOG":
            changelog_index = i
            # lines[i] = lines[i].replace("# 🗓️ CHANGELOG", "# 🗓️ Changelog")
        if "## Release:" in line:
            release_count += 1
            if release_count == 2:
                second_release_index = i
                break
    # Validate that all release notes section exists
    if changelog_index is None:
        print("Required sections not found in the file.")
        return
    # Extract content from "## Changelog:" to the second "## Release"
    if second_release_index is not None:
        release_section = lines[changelog_index:second_release_index]
    else:
        release_section = lines[changelog_index:]
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
        if line.strip() == "## 📅 ROADMAP":
            start_index = i
        if start_index is not None and line.strip() == "## 🎖️ Credits":
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
    # =======================
    # Create global variables
    # =======================
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global TOOL_SOURCE_NAME
    global TOOL_VERSION_WITHOUT_V
    global TOOL_NAME_VERSION
    global root_dir
    global tool_name_with_version_os_arch
    global script_zip_file
    global archive_path_relative

    # Detect the operating system and architecture
    OPERATING_SYSTEM = get_os(use_logger=False)
    ARCHITECTURE = get_arch(use_logger=False)

    # Script Names
    TOOL_SOURCE_NAME = f"{TOOL_NAME}.py"
    TOOL_VERSION_WITHOUT_V = get_clean_version(TOOL_VERSION)
    TOOL_NAME_VERSION = f"{TOOL_NAME}_{TOOL_VERSION}"

    # Obtener el directorio de trabajo
    root_dir = os.getcwd()
    # Obtener el directorio raíz un nivel arriba del directorio de trabajo
    # root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

    # Calcular el path relativo
    tool_name_with_version_os_arch = f"{TOOL_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"./PhotoMigrator-builds/{TOOL_VERSION_WITHOUT_V}/{tool_name_with_version_os_arch}.zip").resolve()
    archive_path_relative = os.path.relpath(script_zip_file, root_dir)
    # ========================
    # End of global variables
    # ========================


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

    if TOOL_VERSION:
        print(f"TOOL_VERSION found: {TOOL_VERSION_WITHOUT_V}")
    else:
        print("Caanot find TOOL_VERSION.")

    # Extraer el cuerpo de la RELEASE-NOTES y añadir ROADMAP al fichero README.md
    # print("Extracting body of RELEASE-NOTES and adding ROADMAP to file README.md...")
    print("Extracting body of RELEASE-NOTES...")

    # Ruta de los archivos CHANGELOG.md, RELEASE-NOTES.md, README.md y ROADMAP.md
    download_filepath = os.path.join(root_dir, 'DOWNLOAD.md')
    changelog_filepath = os.path.join(root_dir, 'CHANGELOG.md')
    current_release_filepath = os.path.join(root_dir, 'RELEASE-NOTES.md')
    roadmap_filepath = os.path.join(root_dir, 'ROADMAP.md')
    readme_filepath = os.path.join(root_dir, 'README.md')

    # Extraer el cuerpo de la Release actual de CHANGELOG.md
    extract_release_body(input_file=changelog_filepath, output_file=current_release_filepath, download_file=download_filepath)
    print(f"File '{current_release_filepath}' created successfully!.")

    # Añadimos el ROADMAP en el fichero README
    # add_roadmap_to_readme(readme_filepath, roadmap_filepath)
    # print(f"File 'README.md' updated successfully with ROADMAP.md")

    # Guardar build_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'build_info.txt'), 'w') as file:
        file.write('OPERATING_SYSTEM=' + OPERATING_SYSTEM + '\n')
        file.write('ARCHITECTURE=' + ARCHITECTURE + '\n')
        file.write('TOOL_NAME=' + TOOL_NAME + '\n')
        file.write('TOOL_VERSION=' + TOOL_VERSION_WITHOUT_V + '\n')
        file.write('ROOT_PATH=' + root_dir + '\n')
        file.write('ARCHIVE_PATH=' + archive_path_relative + '\n')
        print('')
        print(f'OPERATING_SYSTEM: {OPERATING_SYSTEM}')
        print(f'ARCHITECTURE: {ARCHITECTURE}')
        print(f'TOOL_NAME: {TOOL_NAME}')
        print(f'TOOL_VERSION: {TOOL_VERSION_WITHOUT_V}')
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
    global TOOL_SOURCE_NAME
    global TOOL_VERSION_WITHOUT_V
    global TOOL_NAME_VERSION
    global root_dir
    global tool_name_with_version_os_arch
    global script_zip_file
    global archive_path_relative

    # Inicializamos variables
    TOOL_NAME_WITH_VERSION_OS_ARCH    = f"{TOOL_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    splash_image                        = "assets/logos/logo_17_1024x1024.png" # Splash image for windows
    gpth_folder                         = FOLDERNAME_GPTH
    exif_folder                         = FOLDERNAME_EXIFTOOL
    gpth_tool                           = os.path.join(gpth_folder, f"gpth-{GPTH_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext")
    exif_tool                           = os.path.join(exif_folder, "<ZIP_NAME>.zip")
    exif_folder_dest                    = exif_folder
    if OPERATING_SYSTEM == 'windows':
        script_compiled = f'{TOOL_NAME}.exe'
        script_compiled_with_version_os_arch_extension = f"{TOOL_NAME_WITH_VERSION_OS_ARCH}.exe"
        gpth_tool = gpth_tool.replace(".ext", ".exe")
        exif_tool = exif_tool.replace('<ZIP_NAME>', 'windows')
    else:
        if compiler=='pyinstaller':
            script_compiled = f'{TOOL_NAME}'
        else:
            script_compiled = f'{TOOL_NAME}.bin'
        script_compiled_with_version_os_arch_extension = f"{TOOL_NAME_WITH_VERSION_OS_ARCH}.run"
        gpth_tool = gpth_tool.replace(".ext", ".bin")
        exif_tool = exif_tool.replace('<ZIP_NAME>', 'others')

    # Usar resolve_external_path para acceder a archivos o directorios que se empaquetarán en el modo de ejecutable binario:
    gpth_tool_path = resolve_external_path(gpth_tool)

    # Ensure exec permissions for gpth binary file
    ensure_executable(gpth_tool_path)

    # Guardar build_info.txt en un fichero de texto
    with open(os.path.join(root_dir, 'build_info.txt'), 'a') as file:
        file.write('COMPILER=' + str(compiler) + '\n')
        file.write('SCRIPT_COMPILED=' + os.path.abspath(script_compiled_with_version_os_arch_extension) + '\n')
        file.write('GPTH_TOOL=' + gpth_tool + '\n')
        file.write('EXIF_TOOL=' + exif_tool + '\n')
        print('')
        print(f'COMPILER: {compiler}')
        print(f'COMPILE_IN_ONE_FILE: {compile_in_one_file}')
        print(f'SCRIPT_COMPILED: {script_compiled}')
        print(f'GPTH_TOOL: {gpth_tool}')
        print(f'EXIF_TOOL: {exif_tool}')

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

        # Borramos los ficheros y directorios temporales de compilaciones previas
        print("Removing temporary files from previous compilations...")
        Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare Pyinstaller command
        pyinstaller_command = ['./src/' + TOOL_SOURCE_NAME]

        # Mode onefile or standalone
        if compile_in_one_file:
            pyinstaller_command.extend(["--onefile"])
        else:
            pyinstaller_command.extend(['--onedir'])

        # Add splash image to .exe file (only supported in windows)
        if OPERATING_SYSTEM == 'windows':
            pyinstaller_command.extend(("--splash", splash_image))

        # Add following generic arguments to Pyinstaller:
        pyinstaller_command.extend(["--noconfirm"])
        pyinstaller_command.extend(("--distpath", dist_path))
        pyinstaller_command.extend(("--workpath", build_path))
        pyinstaller_command.extend(("--add-data", gpth_tool + ':gpth_tool'))

        # If INCLUDE_EXIF_TOOL flag is True, then Unzip, Change Permissions and Add Exif Tool files to the binary file
        if INCLUDE_EXIF_TOOL:
            # Unzip Exif_tool and include it to compiled binary with Pyinstaller
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            exif_folder_tmp = unzip_to_temp(exif_tool)

            # Dar permiso de ejecución a exiftool
            exiftool_bin = Path(exif_folder_tmp) / "exiftool"
            if exiftool_bin.exists():
                ensure_executable(exiftool_bin)

            # Add Exif Tool files to the binary
            pyinstaller_command.extend(("--add-data", f"{exif_folder_tmp}:{exif_folder_dest}"))

            # walk exif_folder_tmp to add all the files and subfolder to the binary file (I didn't find other way to do this with Pyinstaller)
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

        # In linux set runtime tmp dir to /var/tmp for Synology compatibility (/tmp does not have access rights in Synology NAS)
        if OPERATING_SYSTEM == 'linux':
            pyinstaller_command.extend(("--runtime-tmpdir", '/var/tmp'))

        # Now Run PyInstaller with previous settings
        print_arguments_pretty(pyinstaller_command, title="Pyinstaller Arguments", use_logger=False, use_custom_print=False)

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
        # # Force C Compiler based on the Platform used (is better left Nuita find the best C Compilar installed on the system)
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
        build_path = f"{dist_path}/{TOOL_NAME}.build"

        # Borramos los ficheros y directorios temporales de compilaciones previas
        print("Removing temporary files from previous compilations...")
        Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare Nuitka command
        nuitka_command = [sys.executable, '-m', 'nuitka', './src/' + TOOL_SOURCE_NAME]

        # Mode onefile or standalone
        if compile_in_one_file:
            nuitka_command.extend(['--onefile'])
            # nuitka_command.append('--onefile-no-compression)
            # if OPERATING_SYSTEM == 'windows':
            #     nuitka_command.extend([f'--onefile-windows-splash-screen-image={splash_image}'])
        else:
            nuitka_command.extend(['--standalone'])

        # Add following generic arguments to Nuitka
        nuitka_command.extend([
            '--jobs=4',
            '--assume-yes-for-downloads',
            '--enable-plugin=tk-inter',
            '--disable-cache=ccache',
            '--lto=yes',
            # '--remove-output',
            f'--output-dir={dist_path}',
            f"--file-version={TOOL_VERSION_WITHOUT_V.split('-')[0]}",
            f'--copyright={COPYRIGHT_TEXT}',
            f'--include-data-file={gpth_tool}={gpth_tool}',
        ])

        # If INCLUDE_EXIF_TOOL flag is True, then Unzip, Change Permissions and Add Exif Tool files to the binary file
        if INCLUDE_EXIF_TOOL:
            # Unzip Exif_tool and include it to compiled binary with Nuitka
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            exif_folder_tmp = unzip_to_temp(exif_tool)

            # Dar permiso de ejecución a exiftool
            exiftool_bin = Path(exif_folder_tmp) / "exiftool"
            if exiftool_bin.exists():
                ensure_executable(exiftool_bin)

            # Add Exif Tool files to the binary
            nuitka_command.extend([f'--include-data-files={exif_folder_tmp}={exif_folder_dest}/=**/*.*'])
            nuitka_command.extend([f'--include-data-dir={exif_folder_tmp}={exif_folder_dest}'])
            # nuitka_command.extend(['--include-data-dir=../exif_tool=exif_tool'])

        # In linux set runtime tmp dir to /var/tmp for Synology compatibility (/tmp does not have access rights in Synology NAS)
        if OPERATING_SYSTEM == 'linux':
            nuitka_command.extend([f'--onefile-tempdir-spec=/var/tmp/{TOOL_NAME_WITH_VERSION_OS_ARCH}'])

        # Now Run Nuitka with previous settings
        print_arguments_pretty(nuitka_command, title="Nuitka Arguments", use_logger=False, use_custom_print=False)
        result = subprocess.run(nuitka_command)
        success = (result.returncode == 0)
        if not success:
            print(f"[ERROR] Nuitka failed with code: {result.returncode}")

    else:
        print(f"Compiler '{compiler}' not supported. Valid options are 'pyinstaller' or 'nuitka'. Compilation skipped.")
        return success

    # ===============================================================================================================================================
    # PACKAGING AND CLEANING ACTIONS...
    # ===============================================================================================================================================
    # Now checks if compilations finished successfully, if not, exit.
    if success:
        print("[OK] Compilation process finished successfully.")
    else:
        print("[ERROR] There was some error during compilation process.")
        return success

    # Script Compiled Absolute Path
    script_compiled_abs_path = ''
    if compiler == 'pyinstaller':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{script_compiled}")
    elif compiler == 'nuitka':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{TOOL_NAME}.dist/{script_compiled}")

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
    Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
    Path(f"nuitka-crash-report.xml").unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)
    try:
        shutil.rmtree(exif_folder_tmp, ignore_errors=True)
    except NameError:
        pass
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
    return success


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