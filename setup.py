import os, re
from setuptools import setup, find_packages

# 1) Leer versión de GlobalVariables.py
here = os.path.dirname(__file__)
gv = os.path.join(here, "src", "photomigrator", "Core", "GlobalVariables.py")
with open(gv, encoding="utf-8") as f:
    txt = f.read()
m = re.search(r"^SCRIPT_VERSION_WITHOUT_V\s*=\s*['\"]([^'\"]+)['\"]", txt, re.MULTILINE)
if not m:
    raise RuntimeError("Not found SCRIPT_VERSION_WITHOUT_V in GlobalVariables.py")
version = m.group(1)

# 2) Leer deps de requirements.txt (si existe)
reqs = []
reqs_file = os.path.join(here, "requirements.txt")
if os.path.isfile(reqs_file):
    with open(reqs_file, encoding="utf-8") as f:
        reqs = [l.strip() for l in f if l.strip() and not l.startswith("#")]

setup(
    name="photomigrator",               # distribución y paquete iguales
    version=version,                    # viene de GlobalVariables.SCRIPT_VERSION
    description="Herramienta de migración de fotos",
    package_dir={"": "src"},            # todos los paquetes cuelgan de src/
    packages=find_packages(where="src"),# detecta photomigrator y subpaquetes
    install_requires=reqs,              # deps leídas de requirements.txt
    entry_points={
        "console_scripts": [
            "photomigrator = photomigrator.PhotoMigrator:main",
        ],
    },
    python_requires=">=3.7",
)
