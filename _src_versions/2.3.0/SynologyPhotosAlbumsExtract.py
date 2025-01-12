import requests
import json
import sys

# Configuración de conexión
SYNOLOGY_URL = "https://tu-synology-servidor:5001/webapi/"  # Reemplaza con la URL de tu servidor Synology
USERNAME = "tu_usuario"  # Reemplaza con tu usuario
PASSWORD = "tu_contraseña"  # Reemplaza con tu contraseña
API_VERSION = "2"  # Versión de la API, verifica en tu documentación

# Función para iniciar sesión y obtener el SID
def login():
    login_params = {
        'api': 'SYNO.API.Auth',
        'version': '6',
        'method': 'login',
        'account': USERNAME,
        'passwd': PASSWORD,
        'session': 'PhotoStation',
        'format': 'sid'
    }
    try:
        response = requests.get(SYNOLOGY_URL, params=login_params, verify=False)
        data = response.json()
        if data['success']:
            return data['data']['sid']
        else:
            print("Error al iniciar sesión:", data)
            sys.exit(1)
    except Exception as e:
        print("Excepción durante el inicio de sesión:", e)
        sys.exit(1)

# Función para listar álbumes propios
def listar_albumes_propios(sid):
    params = {
        'api': 'SYNO.Foto.Browse.Album',
        'version': '1',
        'method': 'list',
        '_sid': sid,
        'album_type': 'owned'
    }
    try:
        response = requests.get(SYNOLOGY_URL, params=params, verify=False)
        data = response.json()
        if data['success']:
            return data['data']['albums']
        else:
            print("Error al listar álbumes propios:", data)
            return []
    except Exception as e:
        print("Excepción al listar álbumes propios:", e)
        return []

# Función para listar álbumes compartidos
def listar_albumes_compartidos(sid):
    params = {
        'api': 'SYNO.Foto.Sharing.Misc',
        'version': '1',
        'method': 'list',
        '_sid': sid
    }
    try:
        response = requests.get(SYNOLOGY_URL, params=params, verify=False)
        data = response.json()
        if data['success']:
            return data['data']['albums']
        else:
            print("Error al listar álbumes compartidos:", data)
            return []
    except Exception as e:
        print("Excepción al listar álbumes compartidos:", e)
        return []

# Función para listar fotos en un álbum
def listar_fotos_album(sid, album_id):
    params = {
        'api': 'SYNO.Foto.Browse.Item',
        'version': '1',
        'method': 'list',
        '_sid': sid,
        'album_id': album_id
    }
    try:
        response = requests.get(SYNOLOGY_URL, params=params, verify=False)
        data = response.json()
        if data['success']:
            return data['data']['items']
        else:
            print(f"Error al listar fotos del álbum {album_id}:", data)
            return []
    except Exception as e:
        print(f"Excepción al listar fotos del álbum {album_id}:", e)
        return []

# Función para obtener o crear una carpeta
def obtener_o_crear_carpeta(sid, nombre_carpeta, parent_folder_id=None):
    # Primero, intenta obtener la carpeta
    params_get = {
        'api': 'SYNO.Foto.Browse.Folder',
        'version': '1',
        'method': 'get',
        '_sid': sid,
        'folder_name': nombre_carpeta
    }
    
    if parent_folder_id:
        params_get['parent_folder_id'] = parent_folder_id

    try:
        response = requests.get(SYNOLOGY_URL, params=params_get, verify=False)
        data = response.json()
        if data['success']:
            if data['data']['exists']:
                print(f"La carpeta '{nombre_carpeta}' ya existe.")
                return data['data']['folder_id']
            else:
                # Crear la carpeta
                params_create = {
                    'api': 'SYNO.Foto.Browse.Folder',
                    'version': '1',
                    'method': 'create',
                    '_sid': sid,
                    'folder_name': nombre_carpeta
                }
                
                if parent_folder_id:
                    params_create['parent_folder_id'] = parent_folder_id

                response_create = requests.get(SYNOLOGY_URL, params=params_create, verify=False)
                data_create = response_create.json()
                if data_create['success']:
                    print(f"Carpeta '{nombre_carpeta}' creada exitosamente.")
                    return data_create['data']['folder_id']
                else:
                    print("Error al crear la carpeta:", data_create)
                    return None
        else:
            print("Error al obtener la carpeta:", data)
            return None
    except Exception as e:
        print("Excepción al obtener o crear la carpeta:", e)
        return None

# Función para copiar fotos a una carpeta
def copiar_fotos_a_carpeta(sid, folder_id, lista_fotos):
    # Supongamos que hay un método 'copy' en la API para copiar fotos a una carpeta
    # Este es un ejemplo hipotético, ajusta según la documentación real
    params_copy = {
        'api': 'SYNO.Foto.BackgroundTask.File',
        'version': '1',
        'method': 'copy',
        '_sid': sid,
        'destination_folder_id': folder_id,
        'photo_ids': ','.join([str(foto['id']) for foto in lista_fotos])
    }
    try:
        response = requests.get(SYNOLOGY_URL, params=params_copy, verify=False)
        data = response.json()
        if data['success']:
            print(f"Fotos copiadas exitosamente a la carpeta ID {folder_id}.")
        else:
            print("Error al copiar las fotos:", data)
    except Exception as e:
        print("Excepción al copiar las fotos:", e)

# Función para extraer y copiar álbumes
def ExtractSynologyPhotosAlbums(album_name='ALL'):
    # Iniciar sesión
    sid = login()
    print("Inicio de sesión exitoso. SID:", sid)

    # Crear o obtener la carpeta principal 'Albums_Synology_Photos'
    carpeta_principal = "Albums_Synology_Photos"
    carpeta_principal_id = obtener_o_crear_carpeta(sid, carpeta_principal)

    if not carpeta_principal_id:
        print("No se pudo obtener o crear la carpeta principal 'Albums_Synology_Photos'.")
        sys.exit(1)

    # Listar álbumes propios y compartidos
    albumes_propios = listar_albumes_propios(sid)
    albumes_compartidos = listar_albumes_compartidos(sid)
    todos_albumes = albumes_propios + albumes_compartidos

    # Determinar los álbumes a copiar
    if album_name.strip().upper() == 'ALL':
        albumes_a_copiar = todos_albumes
        print(f"Se copiarán todos los álbumes ({len(albumes_a_copiar)}).")
    else:
        # Buscar el álbum por nombre (case-insensitive)
        album_objetivo = None
        for album in todos_albumes:
            if album['title'].strip().lower() == album_name.strip().lower():
                album_objetivo = album
                break
        if not album_objetivo:
            print(f"No se encontró un álbum con el nombre '{album_name}'.")
            sys.exit(1)
        albumes_a_copiar = [album_objetivo]
        print(f"Se copiará el álbum: ID {album_objetivo['id']}, Nombre: {album_objetivo['title']}")

    # Iterar sobre cada álbum a copiar
    for album in albumes_a_copiar:
        nombre_album = album['title']
        album_id = album['id']
        print(f"\nProcesando álbum: {nombre_album} (ID: {album_id})")

        # Listar fotos en el álbum
        fotos = listar_fotos_album(sid, album_id)
        print(f"Cantidad de fotos en el álbum '{nombre_album}': {len(fotos)}")

        if not fotos:
            print(f"No hay fotos para copiar en el álbum '{nombre_album}'.")
            continue

        # Crear o obtener la carpeta de destino para el álbum dentro de 'Albums_Synology_Photos'
        carpeta_destino_nombre = nombre_album
        carpeta_destino_id = obtener_o_crear_carpeta(sid, carpeta_destino_nombre, parent_folder_id=carpeta_principal_id)

        if not carpeta_destino_id:
            print(f"No se pudo obtener o crear la carpeta de destino para el álbum '{nombre_album}'.")
            continue

        # Copiar las fotos a la carpeta de destino
        copiar_fotos_a_carpeta(sid, carpeta_destino_id, fotos)

    print("\nProceso completado.")

# Función principal
def main():
    # Desactivar advertencias de SSL si usas certificados autofirmados
    requests.packages.urllib3.disable_warnings()

    # Verificar si se pasó un argumento para el nombre del álbum
    if len(sys.argv) > 1:
        nombre_album = sys.argv[1]
    else:
        # Si no se pasa argumento, usar 'ALL' por defecto
        nombre_album = 'ALL'

    # Llamar a la función para extraer y copiar los álbumes
    ExtractSynologyPhotosAlbums(album_name=nombre_album)

if __name__ == "__main__":
    main()