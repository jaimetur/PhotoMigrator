import requests
import json
import subprocess

# Configura el user de GitHub y el repositorio
GITHUB_USER = "jaimetur"
GITHUB_REPO = "OrganizeTakeoutPhotos"

# Configura las cadenas de reemplazo
ORIGINAL_STRING_IN_BODY = "_built_versions/OrganizeTakeoutPhotos_v"
REPLACEMENT_STRING_IN_BODY = "_built_versions/"
ORIGINAL_STRING_IN_NAME_AND_TAG = "Release-"
REPLACEMENT_STRING_IN_NAME_AND_TAG = ""

# URL de la API GraphQL
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Obtener el token de GitHub desde GitHub CLI
def get_gh_token():
    result = subprocess.run(['gh', 'auth', 'status', '--show-token'], capture_output=True, text=True)
    if result.returncode != 0:
        print("[Error] No se pudo obtener el token de GitHub CLI. Asegúrate de estar autenticado.")
        exit(1)
    for line in result.stdout.splitlines():
        if line.startswith("Token:"):
            return line.split("Token:")[1].strip()
    print("[Error] No se encontró un token en la salida de GitHub CLI.")
    exit(1)

# Función para realizar consultas GraphQL
def graphql_query(query, variables=None):
    headers = {
        "Authorization": f"bearer {get_gh_token()}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "variables": variables or {}
    }
    response = requests.post(GITHUB_GRAPHQL_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[Error] La API devolvió un código {response.status_code}: {response.text}")
        return None
    return response.json()

# Obtener lista de releases
def get_releases():
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        releases(first: 100) {
          nodes {
            tagName
            name
          }
        }
      }
    }
    """
    variables = {"owner": GITHUB_USER, "repo": GITHUB_REPO}
    return graphql_query(query, variables)

# Obtener detalles de una release específica
def get_release_details(tag_name):
    query = """
    query($owner: String!, $repo: String!, $tagName: String!) {
      repository(owner: $owner, name: $repo) {
        release(tagName: $tagName) {
          body
        }
      }
    }
    """
    variables = {"owner": GITHUB_USER, "repo": GITHUB_REPO, "tagName": tag_name}
    return graphql_query(query, variables)

# Actualizar una release
def update_release(tag_name, new_tag_name, new_title, new_body):
    mutation = """
    mutation($repoId: ID!, $tagName: String!, $title: String!, $body: String!) {
      updateRelease(input: {
        releaseId: $repoId,
        tagName: $tagName,
        name: $title,
        description: $body
      }) {
        release {
          id
        }
      }
    }
    """
    variables = {
        "repoId": tag_name,
        "tagName": new_tag_name,
        "title": new_title,
        "body": new_body
    }
    return graphql_query(mutation, variables)

# Procesar releases
def process_releases():
    print(f"== Listando releases del repositorio {GITHUB_USER}/{GITHUB_REPO} ==")
    releases_data = get_releases()

    if not releases_data or "data" not in releases_data:
        print("[Error] No se pudieron obtener las releases.")
        return

    releases = releases_data["data"]["repository"]["releases"]["nodes"]

    for release in releases:
        tag_name = release["tagName"]
        name = release["name"]

        print(f"Procesando release: {tag_name} ({name})")

        # Obtener detalles del body de la release
        details_data = get_release_details(tag_name)
        if not details_data or "data" not in details_data:
            print(f"  [Advertencia] No se pudieron obtener los detalles de la release: {tag_name}")
            continue

        body = details_data["data"]["repository"]["release"]["body"]
        if not body:
            print(f"  [Advertencia] La release {tag_name} no tiene un body definido.")
            continue

        # Reemplazar cadenas
        new_tag_name = tag_name.replace(ORIGINAL_STRING_IN_NAME_AND_TAG, REPLACEMENT_STRING_IN_NAME_AND_TAG)
        new_name = name.replace(ORIGINAL_STRING_IN_NAME_AND_TAG, REPLACEMENT_STRING_IN_NAME_AND_TAG)
        new_body = body.replace(ORIGINAL_STRING_IN_BODY, REPLACEMENT_STRING_IN_BODY)

        # Actualizar la release
        response = update_release(tag_name, new_tag_name, new_name, new_body)
        if response and "errors" not in response:
            print(f"  [OK] Release actualizada: {new_tag_name} ({new_name})")
        else:
            print(f"  [Error] No se pudo actualizar la release: {tag_name}")

# Punto de entrada
def main():
    process_releases()

if __name__ == "__main__":
    main()
