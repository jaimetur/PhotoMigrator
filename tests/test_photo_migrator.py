import unittest
import subprocess
import shutil
import os
from tests.utils import get_test_file

class TestPhotoMigratorCLI(unittest.TestCase):
    def setUp(self):
        # Copia temporal del Config.ini desde test_data a la raíz, donde el script lo busca por defecto
        self.temp_config_path = "Config.ini"
        test_config = get_test_file("config_test.ini")
        shutil.copyfile(test_config, self.temp_config_path)
        
    def tearDown(self):
        # Limpieza: elimina el archivo de configuración temporal tras cada test
        if os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)
        
    def test_run_photo_migrator_google_to_immich(self):
        result = subprocess.run(
            [
                "python3", 
                "src/PhotoMigrator.py", 
                "--source=synology", 
                "--target=immich"
            ],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)
        self.assertEqual(result.returncode, 0)
