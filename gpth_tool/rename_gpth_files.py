import os
import re
import zipfile


# Cambia esto a False para renombrar realmente
SIMULATE = False

# Expresión regular para capturar la estructura del nombre
#pattern = re.compile(r"^gpth-v(?P<version>[\d\.]+)-nightly-(?P<os>\w+)-(?P<arch>[\w_]+)(?P<ext>\.\w
pattern = re.compile(r"^gpth-v(?P<version>[\d\.]+)-(?P<tag>\w+)-(?P<os>\w+)-(?P<arch>[\w_]+)(?P<ext>\.\w+)?$")


# Normalización de arquitectura
ARCH_MAP = {
#    "x86_64": "amd64"
    "x86_64": "x86_64"
}

# Extensión por sistema operativo
EXT_MAP = {
    "windows": ".exe"
}

def extract_zip_files_to_current_directory():
    execution_dir = os.getcwd()

    for filename in os.listdir(execution_dir):
        if filename.lower().endswith(".zip"):
            zip_path = os.path.join(execution_dir, filename)
            print(f"Extracting: {zip_path}")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    # Solo extrae archivos (ignora carpetas dentro del zip)
                    if not member.is_dir():
                        # Extrae el nombre del archivo sin la ruta
                        target_filename = os.path.basename(member.filename)
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

    print("✅ Extracción completada.")

def main():
    print(f"\n==== INICIO (SIMULATE={'yes' if SIMULATE else 'no'}) ====\n")
    
    # Extract all zips in working dir
    extract_zip_files_to_current_directory()

    for filename in os.listdir():
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

        print(f"{filename} > {new_name}")

        if not SIMULATE:
            os.rename(filename, new_name)

    print(f"\n==== FINALIZADO (SIMULATE={'yes' if SIMULATE else 'no'}) ====")


if __name__ == "__main__":
    main()
