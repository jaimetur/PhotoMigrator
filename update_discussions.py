import requests
import json
import subprocess

# Configura el user de GitHub y el repositorio
GITHUB_USER = "jaimetur"
GITHUB_REPO = "OrganizeTakeoutPhotos-dev"

# Configura las cadenas de reemplazo
ORIGINAL_STRING = "main_built_versions/"
REPLACEMENT_STRING = "main/_built_versions/"

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

    # Depuración: muestra el JSON enviado
    print("== JSON enviado a la API ==")
    print(json.dumps(payload, indent=4))

    response = requests.post(GITHUB_GRAPHQL_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[Error] La API devolvió un código {response.status_code}: {response.text}")
        return None
    return response.json()

# Consulta para obtener discusiones
GET_DISCUSSIONS_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    discussions(first: 100) {
      nodes {
        id
        title
        body
      }
    }
  }
}
"""

# Mutación para actualizar una discusión
UPDATE_DISCUSSION_MUTATION = """
mutation($id: ID!, $body: String!) {
  updateDiscussion(input: {discussionId: $id, body: $body}) {
    discussion {
      id
    }
  }
}
"""

# Función principal
def main():
    print(f"== Obteniendo discusiones de {GITHUB_USER}/{GITHUB_REPO} ==")

    # Obtener discusiones
    discussions_data = graphql_query(GET_DISCUSSIONS_QUERY, {"owner": GITHUB_USER, "repo": GITHUB_REPO})

    if not discussions_data or "data" not in discussions_data:
        print("[Error] No se pudieron obtener las discusiones.")
        return

    discussions = discussions_data["data"]["repository"]["discussions"]["nodes"]

    for discussion in discussions:
        discussion_id = discussion["id"]
        title = discussion["title"]
        body = discussion["body"]

        print(f"Procesando discusión: {title}")
        print(f"  Cuerpo actual de la discusión ({title}):")
        print(body)

        if ORIGINAL_STRING in body:
            print("  [INFO] La discusión contiene la cadena a reemplazar.")
            new_body = body.replace(ORIGINAL_STRING, REPLACEMENT_STRING)

            # Depuración: muestra el nuevo cuerpo
            print("  Nuevo cuerpo:")
            print(new_body)

            # Actualizar la discusión
            update_data = graphql_query(UPDATE_DISCUSSION_MUTATION, {"id": discussion_id, "body": new_body})
            if update_data and "errors" not in update_data:
                print(f"  [OK] Discusión actualizada: {title}")
            else:
                print(f"  [Error] No se pudo actualizar: {title}")
        else:
            print("  [INFO] Sin cambios en la discusión.")


# Punto de entrada del script
if __name__ == "__main__":
    main()
