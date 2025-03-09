import os
import shutil
from pathlib import Path

class ClassLocalFolder:
    def __init__(self, base_folder):
        """Inicializa la clase con la carpeta base donde se gestionarán los álbumes y archivos."""
        self.base_folder = Path(base_folder)
        self.albums_folder = self.base_folder / "Albums"
        self.shared_albums_folder = self.base_folder / "Albums-shared"
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.albums_folder.mkdir(parents=True, exist_ok=True)
        self.shared_albums_folder.mkdir(parents=True, exist_ok=True)

    def get_client_name(self):
        """Devuelve el nombre del cliente, en este caso, 'Local Folder'."""
        return "Local Folder"

    def read_config_file(self):
        """En este contexto local, no se utiliza un archivo de configuración."""
        return {}

    def login(self):
        """No requiere autenticación en el sistema de archivos local."""
        return True

    def logout(self):
        """No requiere cierre de sesión en el sistema de archivos local."""
        return True

    def get_supported_media_types(self):
        """Devuelve los tipos de archivos multimedia comúnmente utilizados."""
        return [".jpg", ".jpeg", ".png", ".mp4", ".mov"]

    def get_user_id(self):
        """En este contexto local, no hay usuarios identificados."""
        return "local_user"

    def create_album(self, album_id):
        """Crea una carpeta para el álbum especificado."""
        album_path = Path(album_id)
        album_path.mkdir(parents=True, exist_ok=True)
        return album_path.exists()

    def remove_album(self, album_id):
        """Elimina una carpeta de álbum si existe."""
        album_path = Path(album_id)
        if album_path.exists() and album_path.is_dir():
            shutil.rmtree(album_path)
            return True
        return False

    def get_albums_owned_by_user(self):
        """Lista las carpetas de álbumes creadas por el usuario."""
        return [str(p) for p in self.albums_folder.iterdir() if p.is_dir()]

    def get_albums_including_shared_with_user(self):
        """Lista todas las carpetas en 'Albums' y 'Albums-shared'."""
        albums = [str(p) for p in self.albums_folder.iterdir() if p.is_dir()]
        shared_albums = [str(p) for p in self.shared_albums_folder.iterdir() if p.is_dir()]
        return albums + shared_albums

    def get_album_assets_size(self, album_id):
        """Devuelve el tamaño total de los archivos dentro de un álbum."""
        album_path = Path(album_id)
        if not album_path.exists():
            return 0
        return sum(f.stat().st_size for f in album_path.glob("**/*") if f.is_file())

    def get_album_assets_count(self, album_id):
        """Devuelve el número de archivos dentro de un álbum."""
        album_path = Path(album_id)
        if not album_path.exists():
            return 0
        return len([f for f in album_path.glob("**/*") if f.is_file()])

    def album_exists(self, album_id):
        """Verifica si existe la carpeta del álbum."""
        return Path(album_id).exists()

    def get_no_albums_assets(self):
        """Lista los archivos que no pertenecen a ningún álbum."""
        return [str(f) for f in self.base_folder.iterdir() if f.is_file()]

    def get_album_assets(self, album_id):
        """Lista los archivos dentro de un álbum."""
        album_path = Path(album_id)
        return [str(f) for f in album_path.glob("*") if f.is_file()]

    def get_all_albums_assets(self):
        """Lista todos los archivos en todos los álbumes."""
        all_files = []
        for album in self.get_albums_including_shared_with_user():
            all_files.extend(self.get_album_assets(album))
        return all_files

    def add_assets_to_album(self, album_id, asset_ids):
        """Mueve archivos especificados a un álbum."""
        album_path = Path(album_id)
        album_path.mkdir(parents=True, exist_ok=True)
        for asset in asset_ids:
            asset_path = Path(asset)
            if asset_path.exists() and asset_path.is_file():
                shutil.move(str(asset_path), str(album_path / asset_path.name))
        return True

    def upload_asset(self, asset_id):
        """No aplica en almacenamiento local, ya que no hay una subida remota."""
        return True

    def download_asset(self, asset_id, download_folder):
        """Copia un archivo a la carpeta de descarga especificada."""
        asset_path = Path(asset_id)
        download_path = Path(download_folder) / asset_path.name
        shutil.copy(asset_path, download_path)
        return str(download_path)

    def remove_assets(self, asset_ids):
        """Elimina los archivos especificados."""
        for asset in asset_ids:
            asset_path = Path(asset)
            if asset_path.exists() and asset_path.is_file():
                asset_path.unlink()
        return True

    def remove_empty_folders(self):
        """Elimina todas las carpetas vacías en la estructura."""
        for folder in self.base_folder.rglob("*"):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
        return True

    def remove_empty_albums(self):
        """Elimina álbumes que no contienen archivos."""
        for album in self.get_albums_including_shared_with_user():
            if self.get_album_assets_count(album) == 0:
                shutil.rmtree(album)
        return True

    def remove_duplicates_albums(self):
        """No aplica en almacenamiento local."""
        return True

    def remove_orphan_assets(self):
        """No aplica en almacenamiento local."""
        return True

    def remove_all_assets(self):
        """Elimina todos los archivos en todos los álbumes."""
        for album in self.get_albums_including_shared_with_user():
            for asset in self.get_album_assets(album):
                Path(asset).unlink()
        return True

    def remove_all_albums(self):
        """Elimina todas las carpetas de álbumes."""
        for album in self.get_albums_including_shared_with_user():
            shutil.rmtree(album)
        return True
