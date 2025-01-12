import requests
import json
import subprocess

# Configura el user de GitHub y el repositorio
GITHUB_USER = "jaimetur"
GITHUB_REPO = "OrganizeTakeoutPhotos-dev"

# Configura las cadenas de reemplazo
ORIGINAL_STRING_IN_BODY = "### Release Notes:"
REPLACEMENT_STRING_IN_BODY = "## Release Notes:"
ORIGINAL_STRING_IN_NAME_AND_TAG = "Release-"
REPLACEMENT_STRING_IN_NAME_AND_TAG = ""

# URLs base
GITHUB_API_URL = "https://api.github.com"

# Función para obtener el token desde la CLI de GitHub
def get_github_token():
    try:
        result = subprocess.run(['gh', 'auth', 'token'], check=True, stdout=subprocess.PIPE, text=True)
        token = result.stdout.strip()
        if not token:
            raise ValueError("No se encontró un token en la salida de GitHub CLI.")
        return token
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error al ejecutar el comando 'gh auth token': {e}")

# Función para obtener la lista de releases
def get_releases():
    url = f"{GITHUB_API_URL}/repos/{GITHUB_USER}/{GITHUB_REPO}/releases"
    headers = {
        "Authorization": f"token {get_github_token()}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"[Error] No se pudieron obtener las releases. HTTP {response.status_code}: {response.text}")
        return None

    return response.json()

# Función para obtener detalles de una release específica
def get_release_details(tag_name):
    url = f"{GITHUB_API_URL}/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/tags/{tag_name}"
    headers = {
        "Authorization": f"token {get_github_token()}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"[Error] No se pudieron obtener los detalles de la release {tag_name}. HTTP {response.status_code}: {response.text}")
        return None

    return response.json()

# Función para actualizar una release
def update_release(release_id, tag_name, name, body):
    url = f"{GITHUB_API_URL}/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/{release_id}"
    headers = {
        "Authorization": f"token {get_github_token()}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "tag_name": tag_name,
        "name": name,
        "body": body
    }
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"[Error] No se pudo actualizar la release {tag_name}. HTTP {response.status_code}: {response.text}")
        return None

    return response.json()

# Procesar releases
def process_releases():
    print(f"== Listando releases del repositorio {GITHUB_USER}/{GITHUB_REPO} ==")
    releases = get_releases()

    if not releases:
        print("[Error] No se encontraron releases para procesar.")
        return

    for release in releases:
        tag_name = release.get("tag_name")
        name = release.get("name")
        body = release.get("body", "")

        print(f"Procesando release: {tag_name} ({name})")

        # Verificar si el body existe
        if not body:
            print(f"  [Advertencia] La release {tag_name} no tiene un body definido.")
            continue

        # Reemplazar cadenas
        new_tag_name = tag_name.replace(ORIGINAL_STRING_IN_NAME_AND_TAG, REPLACEMENT_STRING_IN_NAME_AND_TAG)
        new_name = name.replace(ORIGINAL_STRING_IN_NAME_AND_TAG, REPLACEMENT_STRING_IN_NAME_AND_TAG)
        new_body = body.replace(ORIGINAL_STRING_IN_BODY, REPLACEMENT_STRING_IN_BODY)

        # Actualizar la release
        updated_release = update_release(release["id"], new_tag_name, new_name, new_body)
        if updated_release:
            print(f"  [OK] Release actualizada: {new_tag_name} ({new_name})")
        else:
            print(f"  [Error] No se pudo actualizar la release: {tag_name}")

# Punto de entrada
def main():
    process_releases()

if __name__ == "__main__":
    main()
