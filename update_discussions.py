import requests
import json
import subprocess

# Configura el user de GitHub y el repositorio
GITHUB_USER = "jaimetur"
GITHUB_REPO = "OrganizeTakeoutPhotos"

# Configura las cadenas de reemplazo
DISCUSSION_NAME_TO_PROCESS = "."  # Procesar solo discusiones que contengan esta cadena en el título
ORIGINAL_STRING = "## Release Notes: "
REPLACEMENT_STRING = "## Release Notes:"

# URL de la API GraphQL
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

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

# Función para realizar consultas GraphQL
def graphql_query(query, variables=None):
    headers = {
        "Authorization": f"bearer {get_github_token()}",
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

    # Filtrar discusiones que contengan la cadena en el título
    discussions = [d for d in discussions if DISCUSSION_NAME_TO_PROCESS in d["title"]]

    # Ordenar discusiones alfabéticamente por título
    discussions = sorted(discussions, key=lambda d: d["title"].lower())

    for discussion in discussions:
        discussion_id = discussion["id"]
        title = discussion["title"]
        body = discussion["body"]

        print(f"Procesando discusión: {title}")

        # Modificar el cuerpo, incluso si no contiene la cadena original
        if ORIGINAL_STRING in body:
            print("  [INFO] La discusión contiene la cadena a reemplazar.")
            new_body = body.replace(ORIGINAL_STRING, REPLACEMENT_STRING)
        else:
            print("  [INFO] La discusión no contiene la cadena, manteniendo el cuerpo original.")
            new_body = body

        # Actualizar la discusión
        update_data = graphql_query(UPDATE_DISCUSSION_MUTATION, {"id": discussion_id, "body": new_body})
        if update_data and "errors" not in update_data:
            print(f"  [OK] Discusión actualizada: {title}")
        else:
            print(f"  [Error] No se pudo actualizar: {title}")

# Punto de entrada del script
if __name__ == "__main__":
    main()
