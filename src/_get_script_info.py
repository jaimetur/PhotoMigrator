import os, sys
import shutil
import zipfile
import tempfile
import subprocess
import glob
import platform
from pathlib import Path

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

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
        if line.strip().startswith("## Download:"):
            download_section_index = i
            break
    # Validate that all required sections exist
    if release_notes_index is None or download_section_index is None:
        print("Required sections not found in the file.")
        return
    # Extract content from "## Release Notes:" to the second "**Release**"
    if second_release_index is not None:
        release_section = lines[release_notes_index:second_release_index]
    else:
        release_section = lines[release_notes_index:]
    # Extract content from "## Download:" to "## Release Notes:"
    download_section = lines[download_section_index:release_notes_index]
    # Rearrange sections: first the extracted release notes, then the modified download section
    new_content = download_section + ["\n"] + release_section
    # Write the modified content to the output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.writelines(new_content)

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
        if line.strip() == "# ROADMAP:":
            start_index = i
        if start_index is not None and line.strip() == "## Credits":
            end_index = i
            break

    if start_index is not None and end_index is not None:
        # Sustituir el bloque ROADMAP existente
        updated_readme = readme_lines[:start_index] + [roadmap_content] + readme_lines[end_index:]
    else:
        # Buscar la línea donde comienza "## Credits" para insertar el bloque ROADMAP antes
        credits_index = next((i for i, line in enumerate(readme_lines) if line.strip() == "## Credits"), None)

        if credits_index is not None:
            updated_readme = readme_lines[:credits_index] + [roadmap_content] + readme_lines[credits_index:]
        else:
            # Si no se encuentra "## Credits", simplemente añadir al final del archivo
            updated_readme = readme_lines + [roadmap_content]

    # Escribir el contenido actualizado en el archivo README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.writelines(updated_readme)


def get_script_info():
    global SCRIPT_NAME
    global SCRIPT_NAME_VERSION
    global ARCHITECTURE
    global SCRIPT_SOURCE_NAME

    clear_screen()

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

    # Extraer el cuerpo de la CURRENT-RELEASE-NOTES y añadir ROADMAP al fichero README.md
    print("Extrayendo el cuerpo de la CURRENT-RELEASE-NOTES y añadiendo ROADMAP al fichero README.md...")

    # Obtener el directorio raíz un nivel arriba del directorio de trabajo
    root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

    # Ruta de los archivos RELEASES-NOTES.md, CURRENT-RELEASE.md, README.md y ROADMAP.md
    releases_filepath = os.path.join(root_dir, 'docs', 'RELEASES-NOTES.md')
    current_release_filepath = os.path.join(root_dir, 'CURRENT-RELEASE.md')
    roadmap_filepath = os.path.join(root_dir, 'docs', 'ROADMAP.md')
    readme_filepath = os.path.join(root_dir,'README.md')

    # Extraer el cuerpo de la Release actual de RELEASES-NOTES.md
    extract_release_body(releases_filepath, current_release_filepath)
    print(f"Archivo {current_release_filepath} creado correctamente.")

    # Añadimos el ROADMAP en el fichero README
    add_roadmap_to_readme(readme_filepath, roadmap_filepath)
    print(f"Archivo README.md actualizado correctamente con el ROADMAP.md")

    # Calcular el path relativo
    relative_path = os.path.relpath(script_zip_file, root_dir)
    
    # Guardar script_info.txt en un fichero de texto
    with open(os.path.join(root_dir,'script_info.txt'), 'w') as file:
        file.write(SCRIPT_VERSION_INT + '\n')
        file.write(relative_path + '\n')
    print(f'El path relativo es: {relative_path}')
    return True

if __name__ == "__main__":
    ok = get_script_info()
    if ok:
        print(f'TASK FINISHED!')
    sys.exit(0)