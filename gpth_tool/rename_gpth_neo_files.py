import os
import re
import zipfile


# Cambia esto a False para renombrar realmente
SIMULATE = False

# Borra los zips originales tras extraerlos solo si está a True
DELETE_SOURCE_ZIPS = True

# Expresión regular para capturar la estructura del nombre
pattern = re.compile(r"^gpth_neo-v(?P<version>[\d\.]+)-(?P<tag>\w+)-(?P<os>\w+)-(?P<arch>[\w_]+)(?P<ext>\.\w+)?$")


# Normalización de arquitectura
ARCH_MAP = {
    "x86_64": "x86_64"
}

# Extensión por sistema operativo
EXT_MAP = {
    "windows": ".exe"
}


def extract_zip_files_to_current_directory():
    execution_dir = os.path.dirname(os.path.abspath(__file__))

    for filename in os.listdir(execution_dir):
        if filename.startswith("._") or filename == ".DS_Store":
            continue

        if filename.lower().endswith(".zip"):
            zip_path = os.path.join(execution_dir, filename)
            print(f"Extracting: {zip_path}")

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for member in zip_ref.infolist():
                        # Solo extrae archivos (ignora carpetas dentro del zip)
                        if not member.is_dir():
                            # Extrae el nombre del archivo sin la ruta
                            target_filename = os.path.basename(member.filename)

                            # Ignora archivos vacíos, metadata de macOS y similares
                            if not target_filename or target_filename.startswith("._") or target_filename == ".DS_Store":
                                continue

                            target_path = os.path.join(execution_dir, target_filename)

                            # Si ya existe un archivo con ese nombre, añade un sufijo
                            base, ext = os.path.splitext(target_filename)
                            counter = 1
                            while os.path.exists(target_path):
                                target_filename = f"{base}_{counter}{ext}"
                                target_path = os.path.join(execution_dir, target_filename)
                                counter += 1

                            with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                                target.write(source.read())
            except zipfile.BadZipFile:
                print(f"❌ Invalid zip skipped: {zip_path}")
                continue

            # Solo borrar el zip si está activado explícitamente
            if DELETE_SOURCE_ZIPS:
                print(f"Deleting source zip: {zip_path}")
                if not SIMULATE:
                    os.remove(zip_path)

    print("✅ Extracción completada.")


def main():
    execution_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"\n==== INICIO (SIMULATE={'yes' if SIMULATE else 'no'}, DELETE_SOURCE_ZIPS={'yes' if DELETE_SOURCE_ZIPS else 'no'}) ====\n")

    # Extract all zips in working dir
    extract_zip_files_to_current_directory()

    for filename in os.listdir(execution_dir):
        full_path = os.path.join(execution_dir, filename)

        if not os.path.isfile(full_path):
            continue

        if filename.startswith("._") or filename == ".DS_Store":
            continue

        # No renombrar nunca los zips originales
        if filename.lower().endswith(".zip"):
            continue

        match = pattern.match(filename)
        if not match:
            continue

        version = match.group("version")
        os_name = match.group("os")
        arch = match.group("arch")
        arch = arch.replace('x86_64', 'x64')
        ext = match.group("ext") or ""

        # Normalizar arquitectura
        arch = ARCH_MAP.get(arch, arch)

        # Determinar extensión
        new_ext = EXT_MAP.get(os_name.lower(), ".bin")

        new_name = f"gpth-{version}-{os_name}-{arch}{new_ext}"
        new_path = os.path.join(execution_dir, new_name)

        print(f"{filename} > {new_name}")

        if not SIMULATE:
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(full_path, new_path)

    print(f"\n==== FINALIZADO (SIMULATE={'yes' if SIMULATE else 'no'}, DELETE_SOURCE_ZIPS={'yes' if DELETE_SOURCE_ZIPS else 'no'}) ====")


if __name__ == "__main__":
    main()