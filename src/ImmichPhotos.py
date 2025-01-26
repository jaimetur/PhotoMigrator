#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ImmichPhotos.py
---------------
Módulo Python con ejemplos de funciones para interactuar con Immich:
  - Configuración (leer Immich.config)
  - Autenticación (login/logout)
  - Listado y gestión de álbumes
  - Listado, subida y descarga de assets
  - Eliminación de álbumes vacíos o duplicados
  - NUEVOS NOMBRES:
     - immich_extract_albums()    (antes extract_photos_from_album)
     - immich_create_albums()     (antes create_albums_from_folder)
     - immich_download_all_with_structure() (antes download_all_assets_with_structure)

Requisitos:
  - requests
  - tqdm
"""

import os
import sys
import requests
import json
import urllib3
from requests_toolbelt.multipart.encoder import total_len
from tqdm import tqdm
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------------------------------------------------------
#                          VARIABLES GLOBALES
# -----------------------------------------------------------------------------

CONFIG          = None  # Diccionario con info de config
IMMICH_URL      = None  # p.e. "http://192.168.1.100:2283"
API_KEY         = None  # API_KEY de Immich
USERNAME        = None  # Usuario (email) de Immich
PASSWORD        = None  # Contraseña de Immich
SESSION_TOKEN   = None  # Token JWT devuelto tras login
API_KEY_LOGIN   = False # Variable to define if we use API_KEY for login or not
HEADERS         = {}    # Cabeceras que usaremos en cada petición

# Lista de extensiones “compatibles” (ajústalo a tus necesidades)
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.heic', '.heif', '.bmp',
    '.mp4', '.mov', '.avi', '.mkv', '.mts', '.m2ts', '.wmv'
}

# -----------------------------------------------------------------------------
#                          LECTURA DE CONFIGURACIÓN
# -----------------------------------------------------------------------------

def read_immich_config(config_file='Immich.config', show_info=True):
    """
    Lee la configuración (IMMICH_URL, USERNAME, PASSWORD) desde un fichero .config,
    por ejemplo:

        IMMICH_URL = http://192.168.1.100:2283
        API_KEY    ='
        USERNAME   = user@example.com
        PASSWORD   = 1234

    Si no se encuentra, se solicitará por pantalla.
    """
    global CONFIG, IMMICH_URL, API_KEY, USERNAME, PASSWORD, API_KEY_LOGIN

    if CONFIG:
        return CONFIG  # Ya se ha leído previamente

    CONFIG = {}
    print(f"[INFO] Buscando archivo de configuración '{config_file}'...")

    try:
        with open(config_file, 'r') as file:
            for line in file:
                # Eliminar comentarios y espacios extra
                line = line.split('#')[0].strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    if key not in CONFIG:
                        CONFIG[key] = value

    except FileNotFoundError:
        print(f"[WARNING] No se encontró el archivo {config_file}. Se pedirán datos por pantalla...")

    IMMICH_URL = CONFIG.get('IMMICH_URL', None)
    API_KEY    = CONFIG.get('API_KEY', None)
    USERNAME   = CONFIG.get('USERNAME', None)
    PASSWORD   = CONFIG.get('PASSWORD', None)

    # Si falta algún dato, lo pedimos por pantalla
    if not IMMICH_URL:
        CONFIG['IMMICH_URL'] = input("[PROMPT] Introduce IMMICH_URL (p.e. http://192.168.1.100:2283): ")
        IMMICH_URL = CONFIG['IMMICH_URL']
    if not API_KEY:
        if not USERNAME:
            CONFIG['USERNAME'] = input("[PROMPT] Introduce USERNAME (email de Immich): ")
            USERNAME = CONFIG['USERNAME']
        if not PASSWORD:
            CONFIG['PASSWORD'] = input("[PROMPT] Introduce PASSWORD: ")
            PASSWORD = CONFIG['PASSWORD']
    else:
        API_KEY_LOGIN = True

    if show_info:
        print( "[INFO] Conexión a Immich:")
        print(f"       IMMICH_URL : {IMMICH_URL}")
        if API_KEY_LOGIN:
            masked_password = '*' * len(API_KEY)
            print(f"       API_KEY : {masked_password}")
        else:
            print(f"       USERNAME   : {USERNAME}")
            masked_password = '*' * len(PASSWORD)
            print(f"       PASSWORD   : {masked_password}")

    return CONFIG

# -----------------------------------------------------------------------------
#                          AUTENTICACIÓN / LOGOUT
# -----------------------------------------------------------------------------

def login_immich():
    """
    Inicia sesión en Immich y obtiene un token JWT (SESSION_TOKEN).
    Retorna True si la conexión fue exitosa, False en caso de error.
    """
    global SESSION_TOKEN, HEADERS

    # Si ya hay un token y cabeceras, asumimos que estamos logueados
    if (SESSION_TOKEN and 'Authorization') or API_KEY in HEADERS:
        return True

    # Asegurarnos de que la config está leída
    read_immich_config()

    url = f"{IMMICH_URL}/api/auth/login"
    payload = json.dumps({
      "email": USERNAME,
      "password": PASSWORD
    })
    HEADERS = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }

    try:
        response = requests.post(url, headers=HEADERS, data=payload)
        response.raise_for_status()  # lanza excepción si 4xx o 5xx
    except Exception as e:
        print(f"[ERROR] Excepción al hacer login en Immich: {str(e)}")
        return False

    data = response.json()
    SESSION_TOKEN = data.get("accessToken", None)
    if not SESSION_TOKEN:
        print(f"[ERROR] No se obtuvo 'accessToken' en la respuesta: {data}")
        return False

    # Cabeceras base para nuestras peticiones
    if API_KEY_LOGIN:
        HEADERS = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': API_KEY
        }
    else:
        HEADERS = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {SESSION_TOKEN}'
        }

    print("[INFO] Autenticación correcta. Token obtenido.")
    return True

def logout_immich():
    """
    "Cierra" la sesión local, descartando el token.
    (Actualmente Immich no provee un endpoint /logout oficial).
    """
    global SESSION_TOKEN, HEADERS
    SESSION_TOKEN = None
    HEADERS = {}
    print("[INFO] Sesión cerrada localmente (JWT descartado).")

# -----------------------------------------------------------------------------
#                          ÁLBUMES
# -----------------------------------------------------------------------------
def get_user_id():
    url = f"{IMMICH_URL}/api/users/me"
    payload = {}
    try:
        response = requests.request("GET", url, headers=HEADERS, data=payload)
        data = response.json()
        user_id = data.get("id")
        user_mail = data.get("email")
        print(f"[INFO] User ID: '{user_id}' found for user '{user_mail}'.")
        return user_id
    except Exception as e:
        print(f"[ERROR] Cannot find User ID for user '{user_mail}': {e}")
        return None

def create_album(album_name):
    """
    Crea un álbum en Immich con nombre 'album_name'.
    Devuelve el ID del álbum creado o None si falla.
    """
    from LoggerConfig import LOGGER
    if not login_immich():
        return None
    user_id = get_user_id()

    url = f"{IMMICH_URL}/api/albums"
    payload = json.dumps({
        "albumName": album_name,
        # "albumUsers": [
        #   {
        #     "role": "editor",
        #     "userId": user_id
        #   }
        # ],
    })

    try:
        response = requests.post(url, headers=HEADERS, data=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        album_id = data.get("id")
        print(f"[INFO] Álbum '{album_name}' creado con ID={album_id}.")
        return album_id
    except Exception as e:
        LOGGER.warning(f"WARNING: Cannot create album: '{album_name}' due to API call error. Skipped! ")
        return None

def delete_album(album_id, album_name):
    """
    Elimina un álbum de Immich por su ID. Devuelve True si se eliminó, False si no.
    """
    if not login_immich():
        return False
    url = f"{IMMICH_URL}/api/albums/{album_id}"
    try:
        response = requests.delete(url, headers=HEADERS, verify=False)
        if response.status_code == 200 :
            print(f"[INFO] Álbum '{album_name} con ID={album_id} eliminado.")
            return True
        else:
            print(f"[WARNING] No se pudo eliminar el álbum {album_id}. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error al eliminar álbum {album_id}: {e}")
        return False

def list_albums():
    """
    Devuelve la lista de álbumes del usuario actual en Immich.
    Cada elemento es un dict con al menos:
        {
          "id": <str>,
          "albumName": <str>,
          "ownerId": <str>,
          "assets": [ ... ],
          ...
        }
    """
    if not login_immich():
        return []
    url = f"{IMMICH_URL}/api/albums"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        albums_data = response.json()  # una lista
        return albums_data
    except Exception as e:
        print(f"[ERROR] Error al listar álbumes: {e}")
        return []

def add_assets_to_album(album_id, asset_ids):
    """
    Añade la lista de asset_ids (fotos/videos ya subidos) al álbum con album_id.
    Retorna cuántos assets se añadieron realmente.
    """
    if not login_immich():
        return 0
    if not asset_ids:
        return 0

    url = f"{IMMICH_URL}/api/albums/{album_id}/assets"
    payload = json.dumps({
              "ids": asset_ids
            })
    try:
        response = requests.put(url, headers=HEADERS, data=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        total_files = len(data)
        total_added = 0
        for item in data:
            if item.get("success"):
                total_added += 1
        return total_added
    except Exception as e:
        print(f"[ERROR] No se pudo añadir assets al álbum {album_id}: {e}")
        return 0

# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS)
# -----------------------------------------------------------------------------

def list_all_assets():
    """
    Devuelve una lista de TODOS los assets (fotos, vídeos) del usuario en Immich.
    Cada ítem incluye metadata como { id, deviceAssetId, fileCreatedAt, exifInfo, etc. }
    """
    if not login_immich():
        return []
    url = f"{IMMICH_URL}/api/asset"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        data = response.json()  # lista de assets
        return data
    except Exception as e:
        print(f"[ERROR] Error al obtener lista de assets: {e}")
        return []

def upload_file_to_immich(file_path):
    """
    Sube un fichero local (foto o vídeo) a Immich mediante /api/asset/upload-file.
    Retorna el 'id' del asset creado, o None si falla.
    """
    if not login_immich():
        return None

    if not os.path.isfile(file_path):
        print(f"[ERROR] Fichero no encontrado: {file_path}")
        return None

    # Comprobamos si la extensión es compatible
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        print(f"[WARNING] Fichero '{file_path}' no es de una extensión compatible. Omitido.")
        return None

    url = f"{IMMICH_URL}/api/assets"

    if API_KEY_LOGIN:
        HEADERS = {
            'Accept': 'application/json',
            'x-api-key': API_KEY
        }
    else:
        HEADERS = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {SESSION_TOKEN}'
        }

    stats = os.stat(file_path)
    date_time_for_filename = datetime.fromtimestamp(stats.st_mtime).strftime("%Y%m%d_%H%M%S")
    date_time_for_attributes = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    data = {
        'deviceAssetId': f'IMG_{date_time_for_filename}_{os.path.basename(file_path)}',
        'deviceId': 'OrganizeTakeoutPhotos',
        'fileCreatedAt': date_time_for_attributes,
        'fileModifiedAt': date_time_for_attributes,
        'fileSize': str(stats.st_size),
        'isFavorite': 'false',
        # 'assetData': ('filename',open(file_path,'rb'),'application/octet-stream')
        # Puedes añadir otros campos opcionales, si lo deseas como
        # "deviceAssetId": os.path.basename(file_path),
        # "deviceId": "ScriptPy",
        # "fileCreatedAt": "2023-10-10T10:00:00.000Z",
        # "isArchived": "false"
        # "isFavorite": "true"
        # "isVisible": "true"
        # ...
    }

    files = {
        'assetData': open(file_path, 'rb')
    }

    # files=[
    #   ('assetData',('file',open(file_path,'rb'),'application/octet-stream'))
    # ]

    try:
        # En la subida, 'Content-Type' se genera automáticamente con multipart
        response = requests.post(url, headers=HEADERS, data=data, files=files)
        response.raise_for_status()
        new_asset = response.json()
        asset_id = new_asset.get("id")
        if asset_id:
            print(f"[INFO] Subido '{os.path.basename(file_path)}' con asset_id={asset_id}")
        return asset_id
    except Exception as e:
        print(f"[ERROR] No se pudo subir '{file_path}': {e}")
        return None

def download_asset(asset_id, download_folder="Downloaded_Immich"):
    """
    Descarga un asset (foto/video) de Immich y lo guarda en disco local.
    Usa GET /api/asset/:assetId/serve
    Retorna True si se descargó con éxito, False en caso de error.
    """
    if not login_immich():
        return False

    os.makedirs(download_folder, exist_ok=True)
    url = f"{IMMICH_URL}/api/asset/{asset_id}/serve"

    try:
        with requests.get(url, headers=HEADERS, verify=False, stream=True) as r:
            r.raise_for_status()
            # Intentar deducir filename de la cabecera
            content_disp = r.headers.get('Content-Disposition', '')
            filename = f"{asset_id}"
            if 'filename=' in content_disp:
                # attachment; filename="nombre.jpg"
                filename = content_disp.split("filename=")[-1].strip('"; ')

            out_path = os.path.join(download_folder, filename)

            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return True

    except Exception as e:
        print(f"[ERROR] No se pudo descargar asset {asset_id}: {e}")
        return False

# -----------------------------------------------------------------------------
#           FUNCIONES PARA SUBIR FICHEROS DESDE DIRECTORIOS (NUEVAS)
# -----------------------------------------------------------------------------

def immich_create_albums(input_folder):
    """
    Recorre las *subcarpetas* de 'input_folder', creando un álbum por cada subcarpeta
    (nombre = nombre de la subcarpeta).
    Dentro de cada subcarpeta, sube todos los ficheros 'compatibles' (según ALLOWED_EXTENSIONS)
    y los asocia al álbum recién creado.

    Ejemplo de estructura:
        input_folder/
          ├─ Album1/   (ficheros compatibles para el álbum "Album1")
          └─ Album2/   (ficheros compatibles para el álbum "Album2")

    Retorna la cantidad de álbumes creados.
    """
    if not login_immich():
        return 0

    if not os.path.isdir(input_folder):
        print(f"[ERROR] La carpeta '{input_folder}' no existe.")
        return 0

    albums_created = 0

    # Listar subcarpetas directas
    for item in os.listdir(input_folder):
        subpath = os.path.join(input_folder, item)
        if os.path.isdir(subpath):
            # 'item' será el nombre del nuevo álbum
            album_name = item
            album_id = create_album(album_name)
            if not album_id:
                print(f"[WARNING] No se pudo crear el álbum para la subcarpeta '{item}'.")
                continue

            albums_created += 1

            # Recorrer ficheros en esta subcarpeta
            assets_ids = []
            for file_in_sub in os.listdir(subpath):
                file_path = os.path.join(subpath, file_in_sub)
                if os.path.isfile(file_path):
                    # Subir si es compatible
                    asset_id = upload_file_to_immich(file_path)
                    if asset_id:
                        assets_ids.append(asset_id)

            # Asociar ficheros al álbum
            if assets_ids:
                added_count = add_assets_to_album(album_id, assets_ids)
                print(f"[INFO] Añadidos {added_count}/{len(assets_ids)} ficheros al álbum '{album_name}'.")

    print(f"[INFO] Se crearon {albums_created} álbum(es) a partir de '{input_folder}'.")
    return albums_created

def upload_files_without_album(input_folder):
    """
    Recorre recursivamente 'input_folder' y sus subcarpetas para subir todos los ficheros
    'compatibles' (fotos/vídeos) a Immich, **sin** asociarlos a ningún álbum.

    Retorna la cantidad de ficheros subidos.
    """
    if not login_immich():
        return 0

    if not os.path.isdir(input_folder):
        print(f"[ERROR] La carpeta '{input_folder}' no existe.")
        return 0

    total_uploaded = 0

    # Recorrer recursivamente
    for root, dirs, files in os.walk(input_folder):
        for fname in files:
            file_path = os.path.join(root, fname)
            # Subir si es compatible
            asset_id = upload_file_to_immich(file_path)
            if asset_id:
                total_uploaded += 1

    print(f"[INFO] Se subieron {total_uploaded} ficheros (sin álbum) desde '{input_folder}'.")
    return total_uploaded

# -----------------------------------------------------------------------------
#                          CÁLCULO DE TAMAÑO Y BORRADO MASIVO
# -----------------------------------------------------------------------------

def get_album_items_size(album_id):
    """
    Suma el tamaño de cada asset en un álbum, usando exifInfo.fileSizeInByte (si existe).
    """
    if not login_immich():
        return 0
    try:
        assets = get_assets_from_album(album_id)
        total_size = 0
        for asset in assets:
            exif_info = asset.get("exifInfo", {})
            if "fileSizeInByte" in exif_info:
                total_size += exif_info["fileSizeInByte"]
        return total_size
    except:
        return 0

def immich_delete_empty_albums():
    """
    Elimina todos los álbumes que no tengan ningún asset (estén vacíos).
    Retorna la cantidad de álbumes eliminados.
    """
    if not login_immich():
        return 0

    albums = list_albums()
    if not albums:
        print("[INFO] No se encontraron álbumes.")
        return 0

    empty_count = 0
    for album in tqdm(albums, desc="Buscando álbumes vacíos", unit="álbum"):
        album_id = album.get("id")
        album_name = album.get("albumName")
        assets_count = album.get("assetCount")
        if assets_count == 0:
            if delete_album(album_id, album_name):
                print(f"[INFO] Álbum vacío '{album_name}' (ID={album_id}) eliminado.")
                empty_count += 1

    print(f"[INFO] Se eliminaron {empty_count} álbumes vacíos.")
    return empty_count

def immich_delete_duplicates_albums():
    """
    Elimina álbumes que tengan la misma cantidad de assets y el mismo tamaño total.
    De cada grupo duplicado, conserva el primero (ID menor) y borra los demás.
    """
    if not login_immich():
        return 0

    albums = list_albums()
    if not albums:
        return 0

    duplicates_map = {}
    for album in tqdm(albums, desc="Buscando álbumes duplicados", unit="álbum"):
        album_id = album.get("id")
        album_name = album.get("albumName")
        assets_count = album.get("assetCount")
        size = get_album_items_size(album_id)
        duplicates_map.setdefault((assets_count, size), []).append((album_id, album_name))

    total_deleted = 0
    for (assets_count, size), group in duplicates_map.items():
        if len(group) > 1:
            group_sorted = sorted(group, key=lambda x: x[1])
            # keep = group_sorted[0]
            to_delete = group_sorted[1:]
            for album_id, album_name in to_delete:
                if delete_album(album_id, album_name):
                    total_deleted += 1

    print(f"[INFO] Se eliminaron {total_deleted} álbumes duplicados.")
    return total_deleted

# -----------------------------------------------------------------------------
#             EXTRAER (DESCARGAR) FOTOS DE UN ÁLBUM (O DE TODOS)
# -----------------------------------------------------------------------------

def get_assets_from_album(album_id):
    """
    Retorna la lista de assets que pertenecen a un álbum concreto (ID).
    """
    if not login_immich():
        return []
    url = f"{IMMICH_URL}/api/albums/{album_id}"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        data = response.json()  # lista
        assets = data.get("assets")
        return assets
    except Exception as e:
        print(f"[ERROR] No se pudieron obtener assets del álbum ID={album_id}: {str(e)}")
        return []

def immich_extract_albums(album_name_or_id='ALL', output_folder="DownloadedAlbums"):
    """
    (Antes extract_photos_from_album)
    Descarga (extrae) todas las fotos/videos de uno o varios álbumes:

      - Si album_name_or_id == 'ALL', se descargan todos los álbumes.
      - Si coincide con un 'id' o con el 'albumName', se descarga sólo ése.

    Retorna la cantidad total de assets descargados.
    """
    if not login_immich():
        return 0

    os.makedirs(output_folder, exist_ok=True)
    all_albums = list_albums()
    if not all_albums:
        print("[INFO] No hay álbumes disponibles o no se pudieron listar.")
        return 0

    # Determinar qué álbum(es) descargar
    albums_to_download = []
    if isinstance(album_name_or_id, str) and album_name_or_id.strip().upper() == 'ALL':
        albums_to_download = all_albums
        print(f"[INFO] Se van a descargar TODOS los álbumes ({len(all_albums)})...")
    else:
        found_album = None
        for alb in all_albums:
            if str(alb.get("id")) == str(album_name_or_id):
                found_album = alb
                break
            if alb.get("albumName", "").strip().lower() == album_name_or_id.strip().lower():
                found_album = alb
                break

        if found_album:
            albums_to_download = [found_album]
            print(f"[INFO] Se descargará el álbum: '{found_album.get('albumName')}' (ID={found_album.get('id')}).")
        else:
            print(f"[WARNING] No se encontró el álbum '{album_name_or_id}'.")
            return 0

    total_downloaded = 0
    for album in albums_to_download:
        album_id = album.get("id")
        album_name = album.get("albumName", f"album_{album_id}")
        album_folder = os.path.join(output_folder, f"{album_name}_{album_id}")
        os.makedirs(album_folder, exist_ok=True)

        assets = get_assets_from_album(album_id)
        print(f"[INFO] Álbum '{album_name}' (ID={album_id}) tiene {len(assets)} asset(s).")

        for asset in tqdm(assets, desc=f"Descargando '{album_name}'", unit="fotos"):
            aid = asset.get("id")
            if aid:
                ok = download_asset(aid, album_folder)
                if ok:
                    total_downloaded += 1

    return total_downloaded

# -----------------------------------------------------------------------------
#          DESCARGA COMPLETA DE TODOS LOS ASSETS (Albums + ALL_PHOTOS)
# -----------------------------------------------------------------------------

def immich_download_all_with_structure(output_folder="ImmichDownload"):
    """
    (Antes download_all_assets_with_structure)
    Descarga TODAS las fotos y vídeos de Immich en:
        output_folder/
          ├─ Albums/
          │    ├─ albumName1/ (assets del álbum)
          │    ├─ albumName2/ (assets del álbum)
          │    ...
          └─ ALL_PHOTOS/
               └─ yyyy/
                   └─ mm/ (assets sin álbum en ese año/mes)

    Devuelve la cantidad total de assets descargados.
    """
    if not login_immich():
        return 0

    os.makedirs(output_folder, exist_ok=True)
    total_downloaded = 0
    downloaded_assets_set = set()

    # 1) Álbumes en output_folder/Albums
    albums = list_albums()
    albums_path = os.path.join(output_folder, "Albums")
    os.makedirs(albums_path, exist_ok=True)

    for album in albums:
        album_id   = album.get("id")
        album_name = album.get("albumName", f"Album_{album_id}")

        album_folder = os.path.join(albums_path, album_name)
        os.makedirs(album_folder, exist_ok=True)

        assets_in_album = get_assets_from_album(album_id)
        print(f"[INFO] Álbum '{album_name}' (ID={album_id}) tiene {len(assets_in_album)} asset(s).")

        for asset in tqdm(assets_in_album, desc=f"Álbum '{album_name}'", unit="fotos"):
            aid = asset.get("id")
            if not aid:
                continue

            ok = download_asset(aid, album_folder)
            if ok:
                total_downloaded += 1
                downloaded_assets_set.add(aid)

    # 2) Assets sin álbum -> output_folder/ALL_PHOTOS/yyyy/mm
    all_assets = list_all_assets()
    all_photos_path = os.path.join(output_folder, "ALL_PHOTOS")
    os.makedirs(all_photos_path, exist_ok=True)

    leftover_assets = [a for a in all_assets if a.get("id") not in downloaded_assets_set]
    print(f"[INFO] Se encontraron {len(leftover_assets)} asset(s) que no están en ningún álbum.")

    for asset in tqdm(leftover_assets, desc="Descargando SIN álbum", unit="fotos"):
        aid = asset.get("id")
        if not aid:
            continue

        created_at_str = asset.get("fileCreatedAt", "")
        try:
            dt_created = datetime.fromisoformat(created_at_str.replace("Z", ""))
        except:
            dt_created = datetime.now()

        year_str = dt_created.strftime("%Y")
        month_str = dt_created.strftime("%m")

        target_folder = os.path.join(all_photos_path, year_str, month_str)
        os.makedirs(target_folder, exist_ok=True)

        ok = download_asset(aid, target_folder)
        if ok:
            total_downloaded += 1

    print(f"[INFO] Descarga completada. Total de assets descargados: {total_downloaded}")
    return total_downloaded

# -----------------------------------------------------------------------------
#                          MAIN DE EJEMPLO
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    # # 1) Leemos la config y hacemos login
    # read_immich_config()
    # login_immich()

    # # 2) Ejemplo: Subir ficheros SIN asignarlos a álbum, desde 'r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Others'
    # print("\n=== EJEMPLO: upload_files_without_album ===")
    # big_folder = r"r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Others"
    # upload_files_without_album(big_folder)

    # 3) Ejemplo: Crear álbumes a partir de subcarpetas en 'r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Albums'
    print("\n=== EJEMPLO: immich_create_albums ===")
    input_albums_folder = r"r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Albums"
    immich_create_albums(input_albums_folder)

    # # 4) Ejemplo: Borrar álbumes vacíos
    # print("=== EJEMPLO: Borrar álbumes vacíos ===")
    # deleted = immich_delete_empty_albums()
    # print(f"[RESULT] Álbumes vacíos borrados: {deleted}\n")

    # 5) Ejemplo: Borrar álbumes duplicados
    print("=== EJEMPLO: Borrar álbumes duplicados ===")
    duplicates = immich_delete_duplicates_albums()
    print(f"[RESULT] Álbumes duplicados borrados: {duplicates}\n")

    # # 6) Ejemplo: Descargar todas las fotos de TODOS los álbumes
    # print("\n=== EJEMPLO: immich_extract_albums ===")
    # total = immich_extract_albums('ALL', output_folder="MisDescargasALL")
    # print(f"[RESULT] Se han descargado {total} assets en total.\n")

    # # 7) Ejemplo: Descargar todos en estructura /Albums/<albumName>/ + /ALL_PHOTOS/yyyy/mm
    # print("=== EJEMPLO: immich_download_all_with_structure ===")
    # total_struct = immich_download_all_with_structure(output_folder="FullImmichDownload")
    # print(f"[RESULT] Descarga masiva completada. Total assets: {total_struct}\n")

    # 9) Logout local
    logout_immich()