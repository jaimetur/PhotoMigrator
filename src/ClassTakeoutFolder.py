# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-

"""
Single-class version of ServiceGooglePhotos.py:
 - Preserves original log messages without altering their text.
 - Replaces the global LOGGER usage with LOGGER from GlobalVariables.
 - Docstrings / comments are now in English.
"""

import os
import sys
from datetime import datetime, timedelta
import logging
import inspect
import shutil
from pathlib import Path

# Keep your existing imports for external modules:
import Utils
import ExifFixers
from Duplicates import find_duplicates
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassGoogleTakeout(ClassLocalFolder):
    def __init__(self, base_folder, input_folder):
        """
        Inicializa la clase con la carpeta base (donde se guardan los archivos ya procesados)
        y la carpeta de entrada (donde se encuentran los archivos sin procesar).
        """
        super().__init__(base_folder)  # Inicializa la estructura de base_folder
        self.input_folder = Path(input_folder)
        self.input_folder.mkdir(parents=True, exist_ok=True)  # Asegurar que input_folder existe

    def google_takeout_processor(self):
        """
        Procesa los archivos en input_folder y los mueve a la base_folder con la estructura de ClassLocalFolder.
        """
        for file in self.input_folder.iterdir():
            if file.is_file():
                # Aquí iría la lógica específica de procesamiento del archivo
                processed_file = self._preprocess_file(file)

                # Determinar la ubicación final (siguiendo la estructura de ClassLocalFolder)
                year = str(processed_file.stat().st_mtime).split("-")[0]
                month = str(processed_file.stat().st_mtime).split("-")[1]
                target_folder = self.no_albums_folder / year / month
                target_folder.mkdir(parents=True, exist_ok=True)

                # Mover el archivo procesado a la carpeta final
                shutil.move(str(processed_file), str(target_folder / processed_file.name))

    def _preprocess_file(self, file_path):
        """
        Método interno que representa el preprocesamiento del archivo.
        Aquí podrías agregar cualquier lógica de transformación de datos.
        """
        # En este ejemplo, simplemente devolvemos el mismo archivo como "procesado"
        return file_path

##############################################################################
#                                END OF CLASS                                #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
# Example main usage
if __name__ == "__main__":
    import sys
    from Utils import change_workingdir
    change_workingdir()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    input_folder = Path("r:\jaimetur\CloudPhotoMigrator\Takeout")
    base_folder = input_folder.parent / f"Takeout_processed_{timestamp}"

    takeout = ClassTakeoutFolder(base_folder, input_folder)
    result = takeout.google_takeout_processor("Output_Takeout_Folder", log_level=logging.DEBUG)
    print(result)
