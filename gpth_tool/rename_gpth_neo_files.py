import os
import re
import zipfile


# Cambia esto a False para renombrar realmente
SIMULATE = False

# Borra los zips originales tras extraerlos solo si está a True
DELETE_SOURCE_ZIPS = True

# Expresión regular para capturar la estructura del nombre real
# Ejemplos válidos:
# gpth_neo-v6.1.1-release-linux-arm64.bin
# gpth_neo-6.1.1-release-linux-arm64.bin
pattern = re.compile(
    r"^gpth_neo-v?(?P<version>[\d\.]+)-(?P<tag>\w+)-(?P<os>\w+)-(?P<arch>[\w_]+)(?P<ext>\.\w+)?$"
)

# Normalización de arquitectura
ARCH_MAP = {
    "x86_64": "x64",
    "x64": "x64",
    "arm64": "arm64"
}

# Extensión por sistema operativo
EXT_MAP = {
    "windows": ".exe",
    "linux": ".bin",
    "macos": ".bin"
}


def extract_zip_files_to_current_directory():
    execution_dir = os.path.dirname(os.path.abspath(__file__))
    found_zip = False

    for filename in os.listdir(execution_dir):
        if filename.startswith("._") or filename == ".DS_Store":
            continue

        if not filename.lower().endswith(".zip"):
            continue

        found_zip = True
        zip_path = os.path.join(execution_dir, filename)
        print(f"Extracting: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for member in zip_ref.infolist():
                    # Solo extrae archivos (ignora carpetas dentro del zip)
                    if member.is_dir():
                        continue

                    # Extrae solo el nombre del archivo sin rutas internas
                    target_filename = os.path.basename(member.filename)

                    # Ignora archivos vacíos o metadata de macOS
                    if not target_filename or target_filename.startswith("._") or target_filename == ".DS_Store":
                        continue

                    target_path = os.path.join(execution_dir, target_filename)

                    # Si ya existe, añade sufijo
                    base, ext = os.path.splitext(target_filename)
                    counter = 1
                    while os.path.exists(target_path):
                        target_filename = f"{base}_{counter}{ext}"
                        target_path = os.path.join(execution_dir, target_filename)
                        counter += 1

                    if SIMULATE:
                        print(f"[SIMULATE] Extract: {member.filename} -> {target_filename}")
                    else:
                        with zip_ref.open(member) as source, open(target_path, "wb") as target:
                            target.write(source.read())

        except zipfile.BadZipFile:
            print(f"❌ Invalid zip skipped: {zip_path}")
            continue

        if DELETE_SOURCE_ZIPS:
            print(f"Deleting source zip: {zip_path}")
            if not SIMULATE:
                os.remove(zip_path)

    if found_zip:
        print("✅ Extracción completada.")
    else:
        print("ℹ️ No se encontraron archivos zip. Se continúa con el renombrado.")

    return found_zip


def get_unique_target_path(directory, filename):
    target_path = os.path.join(directory, filename)

    if not os.path.exists(target_path):
        return target_path

    base, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_filename = f"{base}_{counter}{ext}"
        target_path = os.path.join(directory, new_filename)
        if not os.path.exists(target_path):
            return target_path
        counter += 1


def main():
    execution_dir = os.path.dirname(os.path.abspath(__file__))

    print(
        f"\n==== INICIO (SIMULATE={'yes' if SIMULATE else 'no'}, "
        f"DELETE_SOURCE_ZIPS={'yes' if DELETE_SOURCE_ZIPS else 'no'}) ====\n"
    )

    # Extrae todos los zips del directorio, si existen
    extract_zip_files_to_current_directory()

    renamed_any = False

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
        os_name = match.group("os").lower()
        arch = match.group("arch").lower()
        original_ext = match.group("ext") or ""

        # Normalizar arquitectura
        arch = ARCH_MAP.get(arch, arch)

        # Determinar extensión final
        new_ext = EXT_MAP.get(os_name, original_ext if original_ext else ".bin")

        new_name = f"gpth-{version}-{os_name}-{arch}{new_ext}"
        new_path = get_unique_target_path(execution_dir, new_name)

        print(f"{filename} > {os.path.basename(new_path)}")
        renamed_any = True

        if not SIMULATE:
            os.rename(full_path, new_path)

    if not renamed_any:
        print("ℹ️ No se encontró ningún archivo que coincida con el patrón de renombrado.")

    print(
        f"\n==== FINALIZADO (SIMULATE={'yes' if SIMULATE else 'no'}, "
        f"DELETE_SOURCE_ZIPS={'yes' if DELETE_SOURCE_ZIPS else 'no'}) ===="
    )


if __name__ == "__main__":
    main()