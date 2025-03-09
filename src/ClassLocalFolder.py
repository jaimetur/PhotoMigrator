import os
import shutil
from pathlib import Path
from collections import defaultdict

class ClassLocalFolder:
    def __init__(self, base_folder):
        """Inicializa la clase con la carpeta base donde se gestionarán los álbumes y archivos."""
        self.base_folder = Path(base_folder)
        self.albums_folder = self.base_folder / "Albums"
        self.shared_albums_folder = self.base_folder / "Albums-shared"
        self.no_albums_folder = self.base_folder / "No-Albums"
        
        # Crear las carpetas base si no existen
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.albums_folder.mkdir(parents=True, exist_ok=True)
        self.shared_albums_folder.mkdir(parents=True, exist_ok=True)
        self.no_albums_folder.mkdir(parents=True, exist_ok=True)

    def get_client_name(self):
        return "Local Folder"

    def read_config_file(self):
        return {}

    def login(self):
        return True

    def logout(self):
        return True

    def get_supported_media_types(self):
        return [".jpg", ".jpeg", ".png", ".mp4", ".mov"]

    def get_user_id(self):
        return self.base_folder

    def create_album(self, album_id):
        album_path = Path(album_id)
        album_path.mkdir(parents=True, exist_ok=True)
        return album_path.exists()

    def remove_album(self, album_id):
        album_path = Path(album_id)
        if album_path.exists() and album_path.is_dir():
            shutil.rmtree(album_path)
            return True
        return False

    def get_albums_owned_by_user(self):
        return [str(p) for p in self.albums_folder.iterdir() if p.is_dir()]

    def get_albums_including_shared_with_user(self):
        albums = [str(p) for p in self.albums_folder.iterdir() if p.is_dir()]
        shared_albums = [str(p) for p in self.shared_albums_folder.iterdir() if p.is_dir()]
        return albums + shared_albums

    def get_album_assets(self, album_id):
        album_path = Path(album_id)
        return [str(f) for f in album_path.iterdir() if f.is_file() or f.is_symlink()]

    def get_no_albums_assets(self):
        return [str(f) for f in self.no_albums_folder.rglob("*") if f.is_file()]

    def get_album_assets_size(self, album_id):
        return sum(Path(f).stat().st_size for f in self.get_album_assets(album_id))

    def get_album_assets_count(self, album_id):
        return len(self.get_album_assets(album_id))

    def album_exists(self, album_id):
        return Path(album_id).exists()

    def upload_asset(self, asset_id):
        asset_path = Path(asset_id)
        if not asset_path.exists() or not asset_path.is_file():
            return False

        # Obtener fecha de creación del archivo
        creation_time = asset_path.stat().st_ctime
        year = str(Path(asset_path).stat().st_mtime).split("-")[0]
        month = str(Path(asset_path).stat().st_mtime).split("-")[1]

        target_folder = self.no_albums_folder / year / month
        target_folder.mkdir(parents=True, exist_ok=True)

        target_path = target_folder / asset_path.name
        shutil.copy(asset_path, target_path)

        return str(target_path)

    def download_asset(self, asset_id, download_folder):
        asset_path = Path(asset_id)
        download_path = Path(download_folder) / asset_path.name
        shutil.copy(asset_path, download_path)
        return str(download_path)

    def add_assets_to_album(self, album_id, asset_ids):
        album_path = Path(album_id)
        album_path.mkdir(parents=True, exist_ok=True)

        for asset in asset_ids:
            asset_path = Path(asset)
            if asset_path.exists() and asset_path.is_file():
                symlink_path = album_path / asset_path.name
                if not symlink_path.exists():
                    symlink_path.symlink_to(asset_path)
        return True

    def remove_assets(self, asset_ids):
        for asset in asset_ids:
            asset_path = Path(asset)
            if asset_path.exists():
                asset_path.unlink()
        return True

    def remove_empty_folders(self):
        for folder in self.base_folder.rglob("*"):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
        return True

    def remove_empty_albums(self):
        for album in self.get_albums_including_shared_with_user():
            if self.get_album_assets_count(album) == 0:
                shutil.rmtree(album)
        return True

    def remove_duplicates_albums(self):
        album_files_map = defaultdict(list)

        for album in self.get_albums_owned_by_user():
            files = tuple(sorted([(f, Path(f).stat().st_size) for f in self.get_album_assets(album)]))
            if files:
                album_files_map[files].append(album)

        for albums in album_files_map.values():
            if len(albums) > 1:
                for duplicate_album in albums[1:]:
                    shutil.rmtree(duplicate_album)

        return True

    def remove_orphan_assets(self):
        return True

    def remove_all_assets(self):
        for album in self.get_albums_including_shared_with_user():
            for asset in self.get_album_assets(album):
                asset_path = Path(asset)
                if asset_path.is_symlink():
                    asset_path.unlink()
                elif asset_path.exists():
                    asset_path.unlink()

        for asset in self.get_no_albums_assets():
            asset_path = Path(asset)
            if asset_path.exists():
                asset_path.unlink()

        return True

    def remove_all_albums(self):
        for album in self.get_albums_including_shared_with_user():
            shutil.rmtree(album)
        return True
