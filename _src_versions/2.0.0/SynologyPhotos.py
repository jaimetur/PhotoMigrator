import os,sys
import requests
import urllib3
import Utils
from tqdm import tqdm

# Definimos variables globales del NAS:
global CONFIG
global NAS_IP
global USERNAME
global PASSWORD
global ROOT_PHOTOS_PATH
global SYNOLOGY_URL
global SESSION
global SID

# Initialize global variables
SESSION = None
SID = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def read_synology_config(config_file='nas.config'):
    global CONFIG
    global NAS_IP
    global USERNAME
    global PASSWORD
    global ROOT_PHOTOS_PATH
    global SYNOLOGY_URL
    from LoggerConfig import logger  # Importar logger dentro de la función

    CONFIG = {}
    logger.info(f"INFO: Looking for NAS config file: '{config_file}'")
    try:
        # Intentar abrir el archivo
        with open(config_file, 'r') as file:
            for line in file:
                line = line.split('#')[0].split('//')[0].strip()  # Eliminar comentarios y espacios
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    # Solo agregar si la clave no existe aún
                    if key not in CONFIG:
                        CONFIG[key] = value
    except FileNotFoundError:
        logger.warning(f"WARNING: The file {config_file} was not found. You must introduce required data manually...")

    # Extraer valores específicos
    NAS_IP = CONFIG.get('NAS_IP')
    USERNAME = CONFIG.get('USERNAME')
    PASSWORD = CONFIG.get('PASSWORD')
    ROOT_PHOTOS_PATH = CONFIG.get('ROOT_PHOTOS_PATH')

    # Verificación de parámetros obligatorios y solicitud por pantalla si faltan
    if not NAS_IP:
        logger.warning(f"WARNING: NAS_IP not found. It will be requested on screen.")
        CONFIG['NAS_IP'] = input("\nEnter NAS_IP: ")
    if not USERNAME:
        logger.warning(f"WARNING: USERNAME not found. It will be requested on screen.")
        CONFIG['USERNAME'] = input("\nEnter USERNAME: ")
    if not PASSWORD:
        logger.warning(f"WARNING: PASSWORD not found. It will be requested on screen.")
        CONFIG['PASSWORD'] = input("\nEnter PASSWORD: ")
    if not ROOT_PHOTOS_PATH:
        logger.warning(f"WARNING: ROOT_PHOTOS_PATH not found. It will be requested on screen.")
        CONFIG['ROOT_PHOTOS_PATH'] = input("\nEnter ROOT_PHOTOS_PATH: ")

    # Actualiza las variables globales de la conexión
    NAS_IP = CONFIG['NAS_IP']
    USERNAME = CONFIG['USERNAME']
    PASSWORD = CONFIG['PASSWORD']
    ROOT_PHOTOS_PATH = CONFIG['ROOT_PHOTOS_PATH']
    SYNOLOGY_URL = f"http://{NAS_IP}:5000"

    # Muestra por pantalla las variables globales de la conexión
    masked_password = '*' * len(PASSWORD)
    logger.info(f"INFO: NAS_IP           : {NAS_IP}")
    logger.info(f"INFO: USERNAME         : {USERNAME}")
    logger.info(f"INFO: PASSWORD         : {masked_password}")
    logger.info(f"INFO: ROOT_PHOTOS_PATH : {ROOT_PHOTOS_PATH}")

    return CONFIG



def login_synology():
    """Inicia sesión en el NAS y devuelve la sesión activa con el SID y la URL de Synology DSM."""
    global SESSION
    global SID
    from LoggerConfig import logger

    # Si ya tenemos una sesión iniciada, devolvemos esa sesión en lugar de crear otra nueva
    if SESSION and SID:
        return SESSION, SID

    # Read Server Config
    read_synology_config()

    SESSION = requests.Session()
    url = f"{SYNOLOGY_URL}/webapi/auth.cgi"
    params = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": USERNAME,
        "passwd": PASSWORD,
        "format": "sid",
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if data.get("success"):
        SESSION.cookies.set("id", data["data"]["sid"])  # Asigna el SID como cookie
        logger.info(f"INFO: Authentication correct: Session iniciated sucssesfully")
        SID = data["data"]["sid"]
        return SESSION, SID
    else:
        logger.error(f"ERROR: Unable to Authenticate in NAS with the providen data: {data}")


def create_synology_albums(albums_folder):
    """
    Crea álbumes en Synology Photos basados en las carpetas en el NAS.

    Args:
        albums_folder (str): Ruta base en el NAS donde están las carpetas de los álbumes.

    Returns:
        None
    """
    # Importar logger e iniciar sesión en el NAS:
    from LoggerConfig import logger
    login_synology()

    #######################
    # AUXILIARY FUNNCTIONS:
    #######################
    def get_photos_root_folder_id():
        """
        Obtiene el folder_id de una carpeta en Synology Photos dado su ruta.

        Args:
            folder_path (str): Ruta de la carpeta en el NAS.

        Returns:
            int: El ID de la carpeta (folder_id).
        """
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        params = {
            "api": "SYNO.Foto.Browse.Folder",
            "method": "get",
            "version": "2",
        }
        # Realizar la solicitud
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            logger.error(f"ERROR: Cannot obtain Photos Root Folder ID due to error in API call.")
            sys.exit(-1)
        # Extraer el folder_id
        folder_name = data["data"]["folder"]["name"]
        folder_id = str(data["data"]["folder"]["id"])
        if not folder_id or folder_name!="/":
            logger.error(f"ERROR: Cannot obtain Photos Root Folder ID.")
            sys.exit(-1)
        return folder_id


    def get_folder_id(search_in_folder_id, folder_name):
        """
        Obtiene el folder_id de una carpeta en Synology Photos dado el id de la carpeta en la que queremos buscar y el nombre de la carpeta a buscar.

        Args:
            search_in_folder_id (str): id de Synology Photos con la carpeta en la que vamos a buscar la subcarpeta folder_name
            folder_name (str): Nombre de la carpeta que queremos buscar en la estructura de carpetas de Synology Photos.

        Returns:
            int: El ID de la carpeta (folder_id).
        """
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

        offset = 0
        limit = 5000
        subfolders_dict = []
        folder_id = None
        while True:
            params = {
                "api": "SYNO.Foto.Browse.Folder",
                "method": "list",
                "version": "2",
                "id": search_in_folder_id,
                "offset": offset,
                "limit": limit
            }
            # Realizar la solicitud
            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                logger.error(f"ERROR: Cannot obtain ID for folder '{folder_name}' due to error in API call.")
                sys.exit(-1)
            # Construimos un diccionario con todos los IDs de todas las subcarpetas encontradas en albums_folder_id
            subfolders_dict = {item["name"].split("/")[-1]: str(item["id"]) for item in data["data"]["list"] if "id" in item}

            # Verificar si se han devuelto menos elementos que el límite o si la carpeta del album a crear ya se ha encontrado
            if len(data["data"]["list"]) < limit or folder_name in subfolders_dict.keys():
                break
            # Incrementar el offset para la siguiente página
            offset += limit

        # Comprobamos si se ha encontrado el id para la carpeta que estamos buscando y si se ha encontrado lo devolvemos
        folder_id = subfolders_dict.get(folder_name)
        if folder_id:
            return folder_id
        # Si no se ha encontrado, iteramos recursivamente por todas las subcarpetas y si se encuentra en alguna lo devolvemos
        else:
            for subfolder_id in subfolders_dict.values():
                folder_id = get_folder_id(search_in_folder_id=subfolder_id, folder_name=folder_name)
                if folder_id:
                    return folder_id
            # Si después de iterar por todas las subcarpetas recursivamente, seguimos sin encontrarlo, entonces devolvemos None
            return folder_id


    def add_photos_to_album(folder_id, album_name):
        """Añade fotos de una carpeta a un álbum."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

        # Primero nos aseguramos de que la carpeta folder_id tenga al menos 1 fichero soportado indexado
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "count",
            "version": "4",
            "folder_id": folder_id,
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.warning(f"WARNING: Connot count files in folder: '{album_name}' due to API call error. Skipped! ")
            return -1

        # Comprobar si hay fotos para añadir
        num_files = data["data"]["count"]
        if not num_files > 0:
            logger.warning(f"WARNING: Connot find supported files in folder: '{album_name}'. Skipped! ")
            return -1

        # Obtenemos los ids de todos los ficheros de medios encontrados en folder_id
        file_ids = []
        offset = 0
        limit = 5000
        while True:
            params = {
                "api": "SYNO.Foto.Browse.Item",
                "method": "list",
                "version": "4",
                "folder_id": folder_id,
                "offset": offset,
                "limit": limit
            }
            # Realizar la solicitud
            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                logger.warning(f"WARNING: Cannot list files in folder: '{album_name}' due to API call error. Skipped! ")
                return -1
            file_ids.extend([str(item["id"]) for item in data["data"]["list"] if "id" in item])
            # Verificar si se han devuelto menos elementos que el límite
            if len(data["data"]["list"]) < limit:
                break
            # Incrementar el offset para la siguiente página
            offset += limit

        # Ahora creamos el álbum con el mismo nombre que tiene su carpeta siempre y cuando la carpeta contenga ficheros soportados
        if not len(file_ids) > 0:
            logger.warning(f"WARNING: Cannot find supported files in folder: '{album_name}'. Skipped! ")
            return -1
        params = {
            "api": "SYNO.Foto.Browse.NormalAlbum",
            "method": "create",
            "version": "3",
            "name": f'"{album_name}"',
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.error(f"ERROR: Unable to create album '{album_name}': {data}")
            return -1
        album_id = data["data"]["album"]["id"]
        logger.info(f"INFO: Álbum '{album_name}' created with ID: {album_id}.")

        # Finalmente, añadimos los ficheros al álbum en bloques de 100
        batch_size = 100
        total_added = 0

        for i in range(0, len(file_ids), batch_size):
            batch = file_ids[i:i + batch_size]  # Dividir en bloques de 100
            items = ",".join(batch)  # Envía las fotos como una lista separada por comas
            params = {
                "api": "SYNO.Foto.Browse.NormalAlbum",
                "method": "add_item",
                "version": "1",
                "id": album_id,
                "item": f"[{items}]",
            }

            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()

            if not data["success"]:
                logger.warning(f"WARNING: Unable to add photos to album '{album_name}' (Batch {i // batch_size + 1}). Skipped!")
                continue

            total_added += len(batch)

        return total_added

    #######################
    # END OF AUX FUNNCTIONS
    #######################

    # Check if albums_folder is inside ROOT_PHOTOS_PATH (This is necessary to process files within Albums with the indexed IDs.
    albums_folder = Utils.remove_quotes(albums_folder)
    if albums_folder.endswith(os.path.sep):
        albums_folder=albums_folder[:-1]
    if not os.path.isdir(albums_folder):
        logger.error(f"ERROR: Cannot find Album folder '{albums_folder}'. Exiting...")
        sys.exit(-1)
    logger.info(f"INFO: Albums Folder Path: '{albums_folder}")
    albums_folder_full_path = os.path.realpath(albums_folder)
    ROOT_PHOTOS_PATH_full_path = os.path.realpath(ROOT_PHOTOS_PATH)
    if ROOT_PHOTOS_PATH_full_path not in albums_folder_full_path:
        logger.error(f"ERROR: Albums folder: '{albums_folder_full_path}' should be inside ROOT_PHOTOS_PATH: '{ROOT_PHOTOS_PATH_full_path}'")
        sys.exit(-1)

    # El proceso consta de 4 pasos:
    # 1. Primero obtenemos el id de la carpeta raiz de Synology Photos para el usuario autenticado
    photos_root_folder_id = get_photos_root_folder_id ()
    logger.info(f"INFO: Synology Photos root folder ID: {photos_root_folder_id}")

    # 2. Luego buscamos el id de la carpeta que contiene los albumes que queremos añadir
    albums_folder_id = get_folder_id (search_in_folder_id=photos_root_folder_id, folder_name=os.path.basename(albums_folder))
    logger.info(f"INFO: Albums folder ID: {albums_folder_id}")
    if not albums_folder_id:
        logger.error(f"ERROR: Cannot obtain ID for folder '{albums_folder}'. Probably the folder has not been indexed yet. Try to force Indexing and try again.")
        sys.exit(-1)

    # Recorrer carpetas y crear álbumes
    albums_crated = 0
    albums_skipped = 0
    photos_added = 0
    logger.info(f"INFO: Processing all Albums in folder '{albums_folder}' and Creating a new Album in Synology Photos with the same Folder Name...")
    for album_folder in os.listdir(albums_folder):
        logger.info(f"INFO: Processing Album: '{album_folder}'")

        # 3. A continuación, por cada carpeta album_folder, buscamos el individual_folder_id dentro de la carpeta donde están los albumes que queremos crear
        individual_album_folder_id = get_folder_id (search_in_folder_id=albums_folder_id, folder_name=album_folder)
        if not individual_album_folder_id:
            logger.error(f"ERROR: Cannot obtain ID for folder '{album_folder}'. Probably the folder has not been indexed yet. Skipped this Album creation.")
            albums_skipped += 1
            continue

        # 4. Por último añadimos todos los ficheros de fotos o videos encontrados en la carpeta del álbum, al álbum recién creado
        res = add_photos_to_album(folder_id=individual_album_folder_id, album_name=album_folder)
        if res==-1:
            albums_skipped += 1
        else:
            albums_crated += 1
            photos_added += res

    logger.info(f"INFO: Create Albums on Synology Photos Finished!.")
    return albums_crated, albums_skipped, photos_added


def delete_empty_albums():
    """
    Elimina todos los álbumes vacíos en Synology Photos.

    Args:
        synology_url (str): Dirección IP o URL del NAS (ej: https://192.168.1.100:5001).
        user (str): Nombre de usuario para autenticar con Synology.
        password (str): Contraseña del usuario.
    """
    # Importar logger e iniciar sesión en el NAS:
    from LoggerConfig import logger
    login_synology()

    #######################
    # AUXILIARY FUNNCTIONS:
    #######################
    def list_albums():
        """Lists all albums in Synology Photos."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        offset = 0
        limit = 5000
        albums_dict = []
        while True:
            params = {
                "api": "SYNO.Foto.Browse.NormalAlbum",
                "method": "list",
                "version": "3",
                "offset": offset,
                "limit": limit
            }
            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            if data["success"]:
                # Add IDs filtered by supported extensions
                albums_dict = {str(item["id"]): item["name"] for item in data["data"]["list"] if "id" in item}
            else:
                logger.error(f"ERROR: Failed to list albums: ", data)
                return -1
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        return albums_dict

    def get_album_items_count(album_id, album_name):
        """Gets the number of items in an album."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "count",
            "version": "4",
            "album_id": album_id,
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.warning(f"WARNING: Cannot count files for album: '{album_name}' due to API call error. Skipped! ")
            return -1
        num_files = data["data"]["count"]
        return num_files

    def delete_album(album_id, album_name):
        """Deletes an album in Synology Photos."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        params = {
            "api": "SYNO.Foto.Browse.Album",
            "method": "delete",
            "version": "3",
            "id": f"[{album_id}]",
            "name": album_name,
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.warning(f"WARNING: Could not delete album {album_id}: ", data)

    #######################
    # END OF AUX FUNCTIONS
    #######################

    # List albums and check which ones are empty
    albums_dict = list_albums()
    albums_deleted = 0
    if not albums_dict == -1:
        logger.info(f"INFO: Looking for Empty Albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc=f"INFO: Processing Albums", unit=" albums" ):
            item_count = get_album_items_count(album_id=album_id, album_name=album_name)
            if item_count == 0:
                logger.info(f"INFO: Deleting empty album: '{album_name}' (ID: {album_id})")
                delete_album(album_id=album_id, album_name=album_name)
                albums_deleted += 1
    logger.info(f"INFO: Deleting empty albums process finished!")
    return albums_deleted

def delete_duplicates_albums():
    """
    Elimina todos los álbumes duplicados en Synology Photos.

    Args:
        synology_url (str): Dirección IP o URL del NAS (ej: https://192.168.1.100:5001).
        user (str): Nombre de usuario para autenticar con Synology.
        password (str): Contraseña del usuario.
    """
    # Importar logger e iniciar sesión en el NAS:
    from LoggerConfig import logger
    login_synology()

    #######################
    # AUXILIARY FUNNCTIONS:
    #######################
    def list_albums():
        """Lists all albums in Synology Photos."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        offset = 0
        limit = 5000
        albums_dict = []
        while True:
            params = {
                "api": "SYNO.Foto.Browse.NormalAlbum",
                "method": "list",
                "version": "3",
                "offset": offset,
                "limit": limit
            }
            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            if data["success"]:
                # Add IDs filtered by supported extensions
                albums_dict = {str(item["id"]): item["name"] for item in data["data"]["list"] if "id" in item}
            else:
                logger.error(f"ERROR: Failed to list albums: ", data)
                return -1
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        return albums_dict

    def get_album_items_count(album_id, album_name):
        """Gets the number of items in an album."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "count",
            "version": "4",
            "album_id": album_id,
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.warning(f"WARNING: Cannot count files for album: '{album_name}' due to API call error. Skipped! ")
            return -1
        num_files = data["data"]["count"]
        return num_files

    def get_album_items_size(album_id, album_name):
        """Gets the number of items in an album."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        offset = 0
        limit = 5000
        album_size = 0
        album_items = []
        while True:
            params = {
                "api": "SYNO.Foto.Browse.Item",
                "method": "list",
                "version": "4",
                "album_id": album_id,
                "offset": offset,
                "limit": limit
            }
            response = SESSION.get(url, params=params, verify=False)
            response.raise_for_status()
            data = response.json()
            if not data["success"]:
                logger.warning(f"WARNING: Cannot list files for album: '{album_name}' due to API call error. Skipped! ")
                return -1
            album_items.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        for set in album_items:
            for item in set:
                album_size += item.get("filesize")

        return album_size

    def delete_album(album_id, album_name):
        """Deletes an album in Synology Photos."""
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        params = {
            "api": "SYNO.Foto.Browse.Album",
            "method": "delete",
            "version": "3",
            "id": f"[{album_id}]",
            "name": album_name,
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            logger.warning(f"WARNING: Could not delete album {album_id}: ", data)

    #######################
    # END OF AUX FUNCTIONS
    #######################

    # List albums and check which ones are empty
    albums_dict = list_albums()
    albums_deleted = 0
    albums_data = {}
    if not albums_dict == -1:
        logger.info(f"INFO: Looking for Duplicates Albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc=f"INFO: Processing Albums", unit=" albums" ):
            item_count = get_album_items_count(album_id=album_id, album_name=album_name)
            item_size = get_album_items_size(album_id=album_id, album_name=album_name)
            # albums_data[(item_count, item_size)].append((album_id, album_name))
            albums_data.setdefault((item_count, item_size), []).append((album_id, album_name))

        ids_to_delete = {}
        for (item_count, item_size) in albums_data.keys():
            if len(albums_data[(item_count, item_size)]) > 1:
                duplicates_set = albums_data[(item_count, item_size)]
                min_id = 0
                min_name = ""
                for album_id, album_name in duplicates_set:
                    if min_id==0:
                        min_id = album_id
                        min_name = album_name
                    elif int(album_id) < int(min_id):
                        ids_to_delete.setdefault(min_id, []).append(min_name)
                        min_id = album_id
                        min_name = album_name
                    else:
                        ids_to_delete.setdefault(album_id, []).append(album_name)

        for album_id, album_name in ids_to_delete.items():
            logger.info(f"INFO: Deleting duplicated album: '{album_name}' (ID: {album_id})")
            delete_album(album_id=album_id, album_name=album_name)
            albums_deleted += 1
    logger.info(f"INFO: Deleting duplicates albums process finished!")
    return albums_deleted

if __name__ == "__main__":
    # Create timestamp, and initialize logger.
    from datetime import datetime
    from LoggerConfig import log_setup
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename=f"execution_log_{TIMESTAMP}"
    log_folder="Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)

    # Define albums_folder_path
    albums_folder_path = "/volume1/homes/jaimetur/Photos/Albums"     # For Linux (NAS)
    albums_folder_path = r"r:\jaimetur\Photos\Albums"                 # For Windows
    delete_duplicates_albums()
    delete_empty_albums()
    # create_synology_albums(albums_folder_path)