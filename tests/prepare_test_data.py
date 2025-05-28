
import os
import zipfile
from PIL import Image
import json
import shutil

base_dir = "test_data"
album_dir = os.path.join(base_dir, "album1")
photo_path = os.path.join(base_dir, "photo.jpg")
json_path = os.path.join(base_dir, "photo.json")
config_path = os.path.join(base_dir, "config_test.ini")
takeout_zip_path = os.path.join(base_dir, "takeout.zip")
fake_album_dir = os.path.join(base_dir, "fake_album")
fake_album_photo = os.path.join(fake_album_dir, "photo.jpg")

os.makedirs(album_dir, exist_ok=True)
os.makedirs(fake_album_dir, exist_ok=True)

# Crear una imagen falsa
img = Image.new("RGB", (100, 100), color="blue")
img.save(photo_path)
img.save(fake_album_photo)
img.save(os.path.join(album_dir, "image1.jpg"))

# Crear archivo JSON simulado
with open(json_path, "w") as f:
    json.dump({
        "photoTakenTime": {"timestamp": "1609502400"},
        "geoData": {"latitude": 37.7749, "longitude": -122.4194}
    }, f, indent=4)

# Crear archivo INI simulado
with open(config_path, "w") as f:
    f.write("""# Config.ini File
    
# Configuration for Google Takeout
[Google Takeout]
# No configuration needed for this module for the time being.

# Configuration for Synology Photos
[Synology]
SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
SYNOLOGY_USERNAME_3         = username_3                                    # Account 3: Your username for Synology Photos
SYNOLOGY_PASSWORD_3         = password_3                                    # Account 3: Your password for Synology Photos

# Configuration for Immich Photos
[Immich Photos]
IMMICH_URL                  = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
IMMICH_API_KEY_ADMIN        = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
IMMICH_API_KEY_USER_1       = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
IMMICH_USERNAME_1           = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
IMMICH_PASSWORD_1           = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
IMMICH_API_KEY_USER_2       = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
IMMICH_USERNAME_2           = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
IMMICH_PASSWORD_2           = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
IMMICH_API_KEY_USER_3       = API_KEY_USER_3                                # Account 3: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
IMMICH_USERNAME_3           = username_3                                    # Account 3: Your username for Immich Photos (mandatory if not API_KEY is providen)
IMMICH_PASSWORD_3           = password_3                                    # Account 3: Your password for Immich Photos (mandatory if not API_KEY is providen)
""")

# Crear ZIP simulado
with zipfile.ZipFile(takeout_zip_path, 'w') as zipf:
    for root, _, files in os.walk(fake_album_dir):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, base_dir)
            zipf.write(abs_path, rel_path)

# Eliminar carpeta temporal
shutil.rmtree(fake_album_dir)

print("✅ Test data preparado en tests/test_data/")
