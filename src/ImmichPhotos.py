#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ImmichPhotos.py
---------------
Ejemplo de módulo Python que encapsula funciones para interactuar con Immich:
  - Configuración (leer Immich.config)
  - Autenticación (login/logout)
  - Listado y gestión de álbumes
  - Listado, subida y descarga de assets
  - Eliminación de álbumes vacíos o duplicados
  - Extracción (descarga) de todas las fotos de uno o varios álbumes
  - Descarga con estructura específica (Albums + ALL_PHOTOS/yyyy/mm)

Requisitos:
  - requests
  - tqdm
"""

import os
import sys
import requests
import urllib3
from tqdm import tqdm
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------------------------------------------------------
#                          VARIABLES GLOBALES
# -----------------------------------------------------------------------------

CONFIG = None        # Diccionario con info de config
IMMICH_URL = None    # p.e. "http://192.168.1.100:2283"
USERNAME = None      # Usuario (email) de Immich
PASSWORD = None      # Contraseña de Immich
SESSION_TOKEN = None # Token JWT devuelto tras login
HEADERS = {}         # Cabeceras que usaremos en cada petición

# -----------------------------------------------------------------------------
#                          LECTURA DE CONFIGURACIÓN
# -----------------------------------------------------------------------------

def read_immich_config(config_file='Immich.config', show_info=True):
    """
    Lee la configuración (IMMICH_URL, USERNAME, PASSWORD) desde un fichero .config,
    por ejemplo:

        IMMICH_URL = http://192.168.1.100:2283
        USERNAME   = user@example.com
        PASSWORD   = 1234

    Si no se encuentra, se solicitará por pantalla.
    """
    global CONFIG, IMMICH_URL, USERNAME, PASSWORD

    if CONFIG:
        return CONFIG  # Ya se ha leído previamente

    CONFIG = {}
    print(f"[INFO] Buscando archivo de configuración '{config_file}'...")

    try:
        with open(config_file, 'r') as file:
            for line in file:
                # Eliminar comentarios ( # o // ) y espacios
                line = line.split('#')[0].split('//')[0].strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    if key not in CONFIG:
                        CONFIG[key] = value

    except FileNotFoundError:
        print(f"[WARNING] No se encontró el archivo {config_file}. Se pedirán datos por pantalla...")

    IMMICH_URL = CONFIG.get('IMMICH_URL', None)
    USERNAME   = CONFIG.get('USERNAME', None)
    PASSWORD   = CONFIG.get('PASSWORD', None)

    # Si falta algún dato, lo pedimos por pantalla
    if not IMMICH_URL:
        CONFIG['IMMICH_URL'] = input("[PROMPT] Introduce IMMICH_URL (p.e. http://192.168.1.100:2283): ")
        IMMICH_URL = CONFIG['IMMICH_URL']
    if not USERNAME:
        CONFIG['USERNAME'] = input("[PROMPT] Introduce USERNAME (email de Immich): ")
        USERNAME = CONFIG['USERNAME']
    if not PASSWORD:
        CONFIG['PASSWORD'] = input("[PROMPT] Introduce PASSWORD: ")
        PASSWORD = CONFIG['PASSWORD']

    if show_info:
        print("[INFO] Conexión a Immich:")
        print(f"       IMMICH_URL : {IMMICH_URL}")
        print(f"       USERNAME   : {USERNAME}")
        masked_password = '*' * len(PASSWORD)
        print(f"       PASSWORD   : {masked_password}")

    return CONFIG

# -----------------------------------------------------------------------------
#                          AUTENTICACIÓN / LOGOUT
# -----------------------------------------------------------------------------

def login_immich():
    """
    Inicia sesión en Immich y obtiene un token JWT que guardaremos en SESSION_TOKEN.
    Retorna True si la conexión fue exitosa, False en caso de error.
    """
    global SESSION_TOKEN, HEADERS

    # Si ya hay un token y cabeceras, asumimos que estamos logueados
    if SESSION_TOKEN and 'Authorization' in HEADERS:
        return True

    # Asegurarnos de que la config está leída
    read_immich_config()

    url = f"{IMMICH_URL}/api/auth/login"
    payload = {
        "email": USERNAME,
        "password": PASSWORD
    }

    try:
        response = requests.post(url, json=payload, verify=False)
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
    HEADERS = {
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json"
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
    url = f"{IMMICH_URL}/api/album"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        albums_data = response.json()
        # albums_data es una lista
        return albums_data
    except Exception as e:
        print(f"[ERROR] Error al listar álbumes: {e}")
        return []

def get_album_items_count(album_id):
    """
    Devuelve la cantidad de assets (fotos/videos) que hay en un álbum concreto.
    """
    if not login_immich():
        return 0
    url = f"{IMMICH_URL}/api/album/{album_id}/assets"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        data = response.json()  # lista de assets
        return len(data)
    except Exception as e:
        print(f"[WARNING] No se pudieron contar assets del álbum ID={album_id}: {e}")
        return 0

def create_album(album_name):
    """
    Crea un álbum en Immich con nombre 'album_name'.
    Devuelve el ID del álbum creado o None si falla.
    """
    if not login_immich():
        return None
    url = f"{IMMICH_URL}/api/album"
    payload = {"albumName": album_name}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        album_id = data.get("id")
        print(f"[INFO] Álbum '{album_name}' creado con ID={album_id}.")
        return album_id
    except Exception as e:
        print(f"[ERROR] No se pudo crear el álbum '{album_name}': {e}")
        return None

def delete_album(album_id):
    """
    Elimina un álbum de Immich por su ID. Devuelve True si se eliminó, False si no.
    """
    if not login_immich():
        return False
    url = f"{IMMICH_URL}/api/album/{album_id}"
    try:
        response = requests.delete(url, headers=HEADERS, verify=False)
        if response.status_code == 204:
            print(f"[INFO] Álbum ID={album_id} eliminado.")
            return True
        else:
            print(f"[WARNING] No se pudo eliminar el álbum {album_id}. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error al eliminar álbum {album_id}: {e}")
        return False

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

def add_assets_to_album(album_id, asset_ids):
    """
    Añade la lista de asset_ids (fotos/videos ya subidos) al álbum con album_id.
    Retorna cuántos assets se añadieron realmente.
    """
    if not login_immich():
        return 0
    if not asset_ids:
        return 0

    url = f"{IMMICH_URL}/api/album/{album_id}/assets"
    payload = {"assetIds": asset_ids}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        # data = { "successfullyAdded": int, "alreadyInAlbum": int }
        return data.get("successfullyAdded", 0)
    except Exception as e:
        print(f"[ERROR] No se pudo añadir assets al álbum {album_id}: {e}")
        return 0

def get_assets_from_album(album_id):
    """
    Retorna la lista de assets que pertenecen a un álbum concreto (ID).
    """
    if not login_immich():
        return []
    url = f"{IMMICH_URL}/api/album/{album_id}/assets"
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()
        assets = response.json()  # lista
        return assets
    except Exception as e:
        print(f"[ERROR] No se pudieron obtener assets del álbum ID={album_id}: {str(e)}")
        return []

# -----------------------------------------------------------------------------
#                          CÁLCULO DE TAMAÑO Y BORRADO MASIVO
# -----------------------------------------------------------------------------

def get_album_items_size(album_id):
    """
    Suma el tamaño de cada asset en un álbum, basándose en exifInfo.fileSizeInByte (si existe).
    """
    if not login_immich():
        return 0
    try:
        assets = get_assets_from_album(album_id)
        total_size = 0
        for a in assets:
            size_in_bytes = 0
            exif_info = a.get("exifInfo")
            if exif_info and exif_info.get("fileSizeInByte"):
                size_in_bytes = exif_info["fileSizeInByte"]
            total_size += size_in_bytes
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
        count = get_album_items_count(album_id)
        if count == 0:
            if delete_album(album_id):
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
        count = get_album_items_count(album_id)
        size = get_album_items_size(album_id)
        duplicates_map.setdefault((count, size), []).append((album_id, album_name))

    total_deleted = 0
    for (count, size), group in duplicates_map.items():
        if len(group) > 1:
            # Ordenar por ID (numérico) y quedarnos con el de ID menor
            group_sorted = sorted(group, key=lambda x: int(x[0]))
            # keep = group_sorted[0]
            to_delete = group_sorted[1:]  # Borramos a partir del segundo
            for alb_id, alb_name in to_delete:
                if delete_album(alb_id):
                    total_deleted += 1

    print(f"[INFO] Se eliminaron {total_deleted} álbumes duplicados.")
    return total_deleted

# -----------------------------------------------------------------------------
#                          SUBIR Y DESCARGAR FICHEROS
# -----------------------------------------------------------------------------

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

    url = f"{IMMICH_URL}/api/asset/upload-file"
    files = {
        "assetData": open(file_path, "rb")
    }
    data = {
        # Ejemplos de campos opcionales:
        # "deviceAssetId": os.path.basename(file_path),
        # "deviceId": "ScriptPy",
        # "fileCreatedAt": "2023-10-10T10:00:00.000Z",
        # "fileModifiedAt": "2023-10-10T10:00:00.000Z",
    }

    try:
        # En la subida, 'Content-Type' se genera automáticamente con multipart
        auth_headers = {"Authorization": HEADERS.get("Authorization", "")}
        response = requests.post(url, headers=auth_headers, files=files, data=data, verify=False)
        response.raise_for_status()
        new_asset = response.json()
        asset_id = new_asset.get("id")
        print(f"[INFO] Subido '{file_path}' a Immich con asset_id={asset_id}.")
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
                # Normalmente: attachment; filename="nombre.jpg"
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
#                         DESCARGAR ÁLBUMES ESPECÍFICOS
# -----------------------------------------------------------------------------

def extract_photos_from_album(album_name_or_id='ALL', output_folder="DownloadedAlbums"):
    """
    Descarga (extrae) todas las fotos/videos de uno o varios álbumes:

      - Si album_name_or_id == 'ALL', se descargan todos los álbumes.
      - Si coincide con un 'id' o con el 'albumName' de un álbum existente,
        se descargan únicamente sus assets.

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
    # Si se pide 'ALL', descargamos todos
    if isinstance(album_name_or_id, str) and album_name_or_id.strip().upper() == 'ALL':
        albums_to_download = all_albums
        print(f"[INFO] Se van a descargar TODOS los álbumes ({len(all_albums)})...")
    else:
        # Buscar por ID o por nombre
        found_album = None
        for alb in all_albums:
            # Coincidencia por ID
            if str(alb.get("id")) == str(album_name_or_id):
                found_album = alb
                break
            # Coincidencia por nombre (ignora mayúsculas)
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

    # Descargar assets de cada álbum
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
#                     DESCARGA GLOBAL: ÁLBUMES + FOTOS SIN ÁLBUM
# -----------------------------------------------------------------------------

def download_all_assets_with_structure(output_folder="ImmichDownload"):
    """
    Descarga TODAS las fotos y vídeos de Immich en una estructura:
    
        output_folder/
          ├─ Albums/
          │    ├─ albumName1/ (assets del álbum 1)
          │    ├─ albumName2/ (assets del álbum 2)
          │    ...
          └─ ALL_PHOTOS/
               └─ yyyy/
                   └─ mm/
                      (assets sin álbum en ese año/mes según fileCreatedAt)

    Devuelve la cantidad total de assets descargados.
    """
    if not login_immich():
        return 0

    # Asegurarnos de que existe la carpeta base
    os.makedirs(output_folder, exist_ok=True)

    total_downloaded = 0
    downloaded_assets_set = set()

    # 1) Descarga todos los álbumes en output_folder/Albums
    albums = list_albums()
    albums_path = os.path.join(output_folder, "Albums")
    os.makedirs(albums_path, exist_ok=True)

    for album in albums:
        album_id   = album.get("id")
        album_name = album.get("albumName", f"Album_{album_id}")

        # Crear carpeta del álbum
        album_folder = os.path.join(albums_path, album_name)
        os.makedirs(album_folder, exist_ok=True)

        # Obtener assets del álbum
        assets_in_album = get_assets_from_album(album_id)
        print(f"[INFO] Álbum '{album_name}' (ID={album_id}) tiene {len(assets_in_album)} asset(s).")

        # Descargar cada asset en la carpeta de este álbum
        for asset in tqdm(assets_in_album, desc=f"Álbum '{album_name}'", unit="fotos"):
            aid = asset.get("id")
            if not aid:
                continue

            ok = download_asset(aid, album_folder)
            if ok:
                total_downloaded += 1
                downloaded_assets_set.add(aid)

    # 2) Descarga todos los assets SIN ÁLBUM en output_folder/ALL_PHOTOS/yyyy/mm
    all_assets = list_all_assets()
    all_photos_path = os.path.join(output_folder, "ALL_PHOTOS")
    os.makedirs(all_photos_path, exist_ok=True)

    # Filtramos aquellos no descargados (o sea, no asociados a ningún álbum)
    leftover_assets = [a for a in all_assets if a.get("id") not in downloaded_assets_set]
    print(f"[INFO] Se encontraron {len(leftover_assets)} asset(s) que NO pertenecen a ningún álbum.")

    for asset in tqdm(leftover_assets, desc="Descargando SIN álbum", unit="fotos"):
        aid = asset.get("id")
        if not aid:
            continue

        # Determinar la fecha de creación para clasificar en yyyy/mm
        created_at_str = asset.get("fileCreatedAt", "")
        try:
            dt_created = datetime.fromisoformat(created_at_str.replace("Z",""))
        except:
            dt_created = datetime.now()

        year_str = dt_created.strftime("%Y")
        month_str = dt_created.strftime("%m")

        # output_folder/ALL_PHOTOS/yyyy/mm
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

    # 1) Leemos la config y hacemos login
    read_immich_config()
    login_immich()

    # 2) Ejemplo: Descargar TODAS las fotos de TODOS los álbumes (en "MisDescargasALL")
    print("\n=== EJEMPLO: Descargar todas las fotos de todos los álbumes ===")
    total = extract_photos_from_album('ALL', output_folder="MisDescargasALL")
    print(f"[RESULT] Se han descargado {total} assets en total.\n")

    # 3) Ejemplo: Crear un álbum y subir un par de fotos
    print("=== EJEMPLO: Crear un álbum y subir 2 fotos ===")
    new_album_id = create_album("AlbumDePrueba")
    if new_album_id:
        asset_ids = []
        for f in ["foto1.jpg", "foto2.png"]:
            if os.path.isfile(f):
                aid = upload_file_to_immich(f)
                if aid:
                    asset_ids.append(aid)
            else:
                print(f"[WARNING] No se encuentra '{f}' en el disco local.")

        # Añadimos assets al álbum
        added = add_assets_to_album(new_album_id, asset_ids)
        print(f"[INFO] Se añadieron {added} assets a 'AlbumDePrueba'.\n")

    # 4) Ejemplo: Borrar álbumes vacíos
    print("=== EJEMPLO: Borrar álbumes vacíos ===")
    deleted = immich_delete_empty_albums()
    print(f"[RESULT] Álbumes vacíos borrados: {deleted}\n")

    # 5) Ejemplo: Borrar álbumes duplicados
    print("=== EJEMPLO: Borrar álbumes duplicados ===")
    duplicates = immich_delete_duplicates_albums()
    print(f"[RESULT] Álbumes duplicados borrados: {duplicates}\n")

    # 6) Ejemplo: Descargar TODAS las fotos/vídeos con la estructura Albums/ + ALL_PHOTOS/
    print("=== EJEMPLO: Descargar TODAS las fotos/vídeos en estructura Albums y ALL_PHOTOS ===")
    total_struct = download_all_assets_with_structure(output_folder="FullImmichDownload")
    print(f"[RESULT] Descarga masiva completada. Total assets: {total_struct}\n")

    # 7) Logout local
    logout_immich()