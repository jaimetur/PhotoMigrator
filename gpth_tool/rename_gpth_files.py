import os
import re

# Cambia esto a False para renombrar realmente
SIMULATE = False

# Expresión regular para capturar la estructura del nombre
pattern = re.compile(r"^gpth-v(?P<version>[\d\.]+)-nightly-(?P<os>\w+)-(?P<arch>[\w_]+)(?P<ext>\.\w+)?$")

# Normalización de arquitectura
ARCH_MAP = {
    "x86_64": "amd64"
}

# Extensión por sistema operativo
EXT_MAP = {
    "windows": ".exe"
}


def main():
    print(f"\n==== INICIO (SIMULATE={'yes' if SIMULATE else 'no'}) ====\n")

    for filename in os.listdir():
        match = pattern.match(filename)
        if not match:
            continue

        version = match.group("version")
        os_name = match.group("os")
        arch = match.group("arch")
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
