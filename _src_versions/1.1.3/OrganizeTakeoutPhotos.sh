#!/bin/bash

# Script version & date
SCRIPT_NAME="OrganizeTakeoutPhotos"
SCRIPT_VERSION="v1.1.3"
SCRIPT_NAME_VERSION="${SCRIPT_NAME}_${SCRIPT_VERSION}"
SCRIPT_DATE="2024-11-22"

######################
# FUNCIONES AUXILIARES
######################

# Función para contar archivos en una carpeta
function count_files_in_folder() {
    local folder="$1"
    find "$folder" -type f | wc -l
}

# Función para descomprimir ficheros zip
function unpack_zips() {
	usage() {	
	    echo "INFO: Usage: unpack_zips -i|--input-folder <input-folder> [-o|--output-folder <output-folder>]"
	}	
    # Procesar parámetros de entrada
    local input_folder=""
    local output_folder=""

    while [[ "$#" -gt 0 ]]; do
        case "$1" in
	        -i|--input-folder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --input-folder."
					usage
					return 1
		    	fi  
	            input_folder="$(realpath "$2")"  # Usa realpath para obtener la ruta absoluta
	            shift 2
	            ;;
	        -o|--output_folder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --output_folder."
					usage
					return 1
		    	fi  
	            output_folder="$(realpath "$2")"  # Usa realpath para obtener la ruta absoluta
	            shift 2
	            ;;
	        *)
	            echo "ERROR: Unknown option: $1"
	            usage
	            return 1
	            ;;
        esac
    done

    # Validar carpeta de entrada obligatoria
    if [ -z "$input_folder" ]; then
        echo "ERROR: The parameter -i|--input_folder is required."
        return 1
    fi

    # Si no se especifica la carpeta de salida, usar el directorio actual
    if [ -z "$output_folder" ]; then
        output_folder=$(pwd)
    fi

    # Carpeta donde se moverán los ZIP extraídos correctamente
    local output_zip_folder="$input_folder""_extracted"

    echo ""
    echo "INFO: Unpacking all Zip files in folder: '"$input_folder"'"
    echo "INFO: The extracted Zip files will be moved (if extraction is successful) to the folder: '"$output_zip_folder"'"
    echo "INFO: The files will be extracted into the folder: '"$output_folder"'"
    echo ""

    # Comprobar si hay archivos ZIP en la carpeta de entrada
    if ls "$input_folder"/*.zip 1> /dev/null 2>&1; then
	    # Crear la carpeta de ZIP procesados si no existe
	    mkdir -p "$output_zip_folder"
        # Iterar sobre los archivos ZIP encontrados
        for file in "$input_folder"/*.zip; do
            echo ""
            echo "INFO: Processing file: '"$file"'..."
            # Extraer el contenido del archivo ZIP al directorio actual
            if 7z x "$file" -y -o"$output_folder" -scsUTF-8; then
                echo ""
                echo "INFO: Successfully extracted '"$file"' to '"$output_folder"'."
                # Mover el archivo ZIP procesado a la carpeta de salida
                mv "$file" "$output_zip_folder/"
                echo "INFO: The archive '"$file"' has been extracted and moved to folder: '"$output_zip_folder"' successfully."
            else
                echo ""
                echo "ERROR: Failed to extract '"$file"'. Skipping."
            fi
        done
        echo ""
        echo "INFO: All extracted ZIP files have been processed and moved to folder: '"$output_zip_folder"'."
    else
        echo ""
        echo "WARNING: No ZIP files found in folder: '"$input_folder"'."
    fi
}


# Función paar mover todos los albumes a una carpeta específica para albumes
function move_albums() {
	usage() {
    	echo "INFO: Usage: move_albums -i|--input-folder <input-folder> [-a|--albums-subfolder <albums-subfolder>]"
	}
    # Variables inicializadas
    local input_folder=""
    local albums_subfolder=""

    # Procesar argumentos
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            -i|--input-folder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --input-folder."
					usage
					return 1
		    	fi  
                input_folder="$(realpath "$2")"  # Usa realpath para obtener la ruta absoluta
                shift 2
                ;;
            -a|--albums-subfolder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --albums-subfolder."
					usage
					return 1
		    	fi  
                albums_subfolder="$input_folder/"$(basename "$2")
                shift 2
                ;;
            *)
	            echo "ERROR: Unknown option: $1"
                usage
                return 1
                ;;
        esac
    done

    # Verificar que se haya proporcionado el parámetro obligatorio
    if [[ -z "$input_folder" ]]; then
        echo "ERROR: The parameter -i|--input-folder is required."
        usage
        return 1
    fi

    # Asignar un valor predeterminado a albums_subfolder si no se proporcionó
    if [[ -z "$albums_subfolder" ]]; then
        albums_subfolder="$input_folder/Albums"
    fi
    
	# Crea la subcarpeta Albums si no existe
	mkdir -p "$albums_subfolder"
	
	# Mueve todas las carpetas excepto ALL_PHOTOS y evita conflictos
	for folder in "$input_folder"/*; do
	    # Asegúrate de que sea un directorio y no sea la carpeta ALL_PHOTOS o Albums
	    if [ -d "$folder" ] && [ "$(basename "$folder")" != "ALL_PHOTOS" ] && [ "$(basename "$folder")" != "Albums" ]; then
	        mv "$folder" "$albums_subfolder/" > /dev/null 2>&1
	        echo "INFO: Moving to '$(basename "$albums_subfolder")' the album folder called: '$(basename "$folder")' "
	    fi
	done
	echo ""
	echo "INFO: Process completed. All Album's folders have been moved to '$(basename "$albums_subfolder")'."
}


# Función para aplanar todas las subcarpetas dentro de una carpeta dada
function flatten_subfolders() {
	usage() {	
	    echo "INFO: Usage: flatten_subfolders -i|--input-folder <folder> [-e|--exclude-folder <subfolder>]"
	}
    local input_folder=""
    local exclude_subfolder=""

    # Parsear argumentos
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            -i|--input-folder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --input-folder."
					usage
					return 1
		    	fi              
                input_folder="$2"
                shift 2
                ;;
            -e|--exclude-subfolder)
            	if [ -z "$2" ]; then
			        echo "ERROR: No folder specified for --exclude-subfolder."
					usage
					return 1
		    	fi                  
                exclude_subfolder="$2"
                shift 2
                ;;
            *)
	            echo "ERROR: Unknown option: $1"
                usage
                return 1
                ;;
        esac
    done

    # Convertir a rutas absolutas
    input_folder=$(realpath "$input_folder")
    if [[ -n "$exclude_subfolder" ]]; then
        exclude_subfolder=$(realpath "$input_folder/$exclude_subfolder")
    fi

    # Caso especial: si la carpeta base es ALL_PHOTOS
    if [[ "$(basename "$input_folder")" == "ALL_PHOTOS" ]]; then
        find "$input_folder" -mindepth 2 -type f 2>/dev/null | while read -r file; do
            mv "$file" "$input_folder/"
        done
        # Eliminar todas las subcarpetas vacías (incluso las que contienen archivos ocultos)
        find "$input_folder" -mindepth 1 -type d | while read -r dir; do
            rm -rf "$dir"
        done

    # Procesar carpetas normales
    else
	    find "$input_folder" -mindepth 1 -type d 2>/dev/null | while read -r subdir; do
	        # Verificar si es la carpeta excluida o está dentro de ella
	        if [[ -n "$exclude_subfolder" && "$subdir" == "$exclude_subfolder"* ]]; then
	            continue
	        fi
	        # Mover archivos al nivel raíz de su subcarpeta actual
	        find "$subdir" -mindepth 1 -type f 2>/dev/null | while read -r file; do
	            mv "$file" "$subdir/"
	        done
	        # Eliminar todas las sub-subcarpetas vacías dentro del directorio procesado
	        find "$subdir" -depth -type d -empty -exec rmdir {} \; 2>/dev/null
	    done
	fi
	
    # Mensaje de confirmación
    if [[ -n "$exclude_subfolder" ]]; then    
        echo "INFO: The content of all albums inside: '$(basename "$input_folder")' has been flattened within their own folder, excluding subfolder: '$(basename "$exclude_subfolder")'."
    else
        echo "INFO: The content of all subfolders inside: '$(basename "$input_folder")' has been flattened within their own flder."
    fi
}

##########################
# Fin fUNCIONES AUXILIARES
##########################

# Limpiamos la pantalla
clear

# Valores por defecto
zip_folder="Zip_files"
takeout_folder="Takeout"
suffix="fixed"

# Flags por defecto
skip_log=false
skip_unzip=false
skip_gpth_tool=false
skip_exif_tool=false
skip_move_albums=false
flatten_albums=false
flatten_no_albums=false

# Función para mostrar ayuda
usage() {
	echo ""
	echo "---------------------------------------------------------------------------------------------------------------------------------------------------------------"
	echo "$SCRIPT_NAME_VERSION - $SCRIPT_DATE"
	echo "Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, fix metadata, organize per year/month folder, and separate Albums)"
	echo "(c) by Jaime Tur (@jaimetur)"
	echo ""
    echo "Usage: $(basename "$0") [Options]"
    echo "Options:"
    echo "  -z,  --zip-folder          Specify the Zip folder where the Zip files downloaded with Google Takeout are placed (default: Zip_files)"
    echo "  -t,  --takeout-folder      Specify the Takeout folder where all the Zip files downloaded with Google Takeout will be unpacked (default: Takeout)"
    echo "  -s,  --suffix              Specify the suffix for the output folder. Output folder will be Takeout folder followed by _{suffix}_{timestamp} (default: fixed)"
    echo ""
    echo "  -sl, --skip-log            Flag to skip saving output messages into log file"
    echo "  -su, --skip-unzip          Flag to skip unzip files (useful if you have already unzipped all the Takeout Zip files manually)"
    echo "  -sg, --skip-gpth-tool      Flag to skip process files with GPTH Tool (not recommended since this tool do the main job)"
    echo "  -se, --skip-exif-tool      Flag to skip process files with EXIF Tool"
    echo "  -sm, --skip-move-albums    Flag to skip move all albums into Albums folder (not recommended)"
    echo "  -fa, --flatten-albums      Flag to skip create year/month folder structuture on each album folder individually (recommended)"
    echo "  -fn, --flatten-no-albums   Flag to skip create year/month folder structuture on ALL_PHOTOS folder (Photos without albums) (not recommended)"
    echo ""
    echo "  -h , --help                Show this help message and exit"
	echo "---------------------------------------------------------------------------------------------------------------------------------------------------------------"
}

# Parseo de argumentos
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -z|--zip-folder)
		    if [ -z "$2" ]; then
		        echo "ERROR: No folder specified for --zip-folder."
		        usage
		        exit 1
		    fi        
            zip_folder="${2%/}" # Quitamos barra (/) final si existe
            shift 2
            ;;
        -t|--takeout-folder)
		    if [ -z "$2" ]; then
		        echo "ERROR: No folder specified for --takeout-folder."
		        usage
		        exit 1
		    fi             
            takeout_folder="${2%/}" # Quitamos barra (/) final si existe
            shift 2
            ;;
        -s|--suffix)
            suffix="${2#_}" # Quitamos guión bajo (_) inicial si existe
            if [[ -z "$suffix" ]]; then
                echo "ERROR: Suffix cannot be empty."
                usage
                exit 1
            fi            
            shift 2
            ;;
        -sl|--skip-log)
            skip_log=true
            shift 1
            ;;	            
        -su|--skip-unzip)
            skip_unzip=true
        	shift 1
            ;; 
        -sg|--skip-gpth-tool)
            skip_gpth_tool=true
            shift 1
            ;;     
        -se|--skip-exif-tool)
		    skip_exif_tool=true
            shift 1
            ;;
        -sm|--skip-move-albums)
            skip_move_albums=true
            shift 1
            ;;		    
        -fa|--flatten-albums)
            flatten_albums=true
            shift 1
            ;;
        -fn|--flatten-no-albums)
            flatten_no_albums=true
            shift 1
            ;;  
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

if ! "$skip_log"; then
	# Crear un archivo de log único con timestamp
	mkdir -p Logs
	timestamp=$(date +"%Y%m%d-%H%M%S")
	log_file="Logs/execution_log_"$timestamp".log"
	exec > >(tee -a "$log_file") 2>&1
fi
echo ""
echo "Running Script: ${SCRIPT_NAME_VERSION} - ${SCRIPT_DATE}"
if [ -n "$BASH_VERSION" ]; then
    echo "Script running on bash: $BASH_VERSION"
else
    echo "ERROR: This script requires Bash. Please run with Bash."
    exit 1
fi

echo ""
echo "====================="
echo " STARTING PROCESS...."
echo "====================="
echo ""
# Añadimos el timestamp al sufijo para identificar bien de qué ejecución es la carpeta de salida
suffix2="${suffix}"_"${timestamp}"

# Inicia el temporizador
start_time=$(date +%s)

# Comprobar si las herramientas existen
if ! command -v ./gpth_tool/gpth &> /dev/null && ! skip_gpth_tool; then
    echo "WARNING: 'GPTH' tool not found. Setting 'skip_gpth_tool' flag to true."
    skip_gpth_tool=true
fi
if ! command -v ./exif_tool/exiftool &> /dev/null && ! skip_exif_tool; then
    echo "WARNING: 'EXIF' tool not found. Setting 'skip_exif_tool' flag to true."
    skip_exif_tool=true
fi

# Creamos las variables de las carpetas de salida
output_folder="$takeout_folder"_"${suffix2}"
output_folder_no_albums="$output_folder-no-albums"

# Mensajes informativos
echo "INFO: Log file with all messages during the execution of this script is being saved into file: "${log_file}""
echo ""
echo "INFO: Using Zip folder    : '"$zip_folder"'"
echo "INFO: Using Takeout folder: '"$takeout_folder"'"
echo "INFO: Using Suffix        : '"${suffix}"'"
echo "INFO: Using Output folder : '"$output_folder"'"
echo ""
if "$skip_log"; then 
	echo "INFO: Flag detected '--skip-log'. Skipping saving output into log file..." 
fi
if "$skip_unzip"; then 
	echo "INFO: Flag detected '--skip-unzip'. Skipping Unzipping files..." 
fi
if "$skip_gpth_tool"; then 
	echo "INFO: Flag detected '--skip-gpth-toot'. Skipping Processing photos with GPTH Tool..." 
	echo "                                        Skipping Moving Albums to Albums folder..."
fi
if "$skip_exif_tool";	then 
	echo "INFO: Flag detected '--skip-exif-tool'. Skipping Processing photos with EXIF Tool..." 
fi
if "$skip_move_albums"; then 
	echo "INFO: Flag detected '--skip-move-albums'. Skipping Moving Albums to Albums folder..." 
fi
if "$flatten_albums"; then 
	echo "INFO: Flag detected '--flatten-albums'. All photos/videos within each album folder will be flattened (without year/month folder structure)..."
fi
if "$flatten_no_albums"; then
	echo "INFO: Flag detected '--flatten-no-albums'. All photos/videos within ALL_PHOTOS folder will be flattened on ALL_PHOTOS folder (without year/month folder structure)..." 
fi
echo ""

# Comienza la llamada a los diferentes scripts

if ! "$skip_unzip"; then
	echo ""
	echo "==============================="
	echo "1. UNPACKING TAKEOUT FOLDER..."
	echo "==============================="
	echo ""
    # Inicia el temporizador parcial
    partial_start_time=$(date +%s)
    
    # Unpack the ZIPs
	unpack_zips -i "$zip_folder" -o "$takeout_folder"
    
    # Finaliza el temporizador parcial y muestra el tiempo por pantalla
    current_time=$(date +%s)
    step_time=$((current_time - partial_start_time))
    elapsed_time=$((current_time - start_time))
    echo "INFO: Step time   : $((step_time / 60)) minutes and $((step_time % 60)) seconds."
    echo "INFO: Elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."
    echo ""
else
	echo ""
	echo "==============================="
	echo "1. UNPACKING TAKEOUT FOLDER..."
	echo "==============================="
	echo ""
	echo "INFO: Step skipped due to Flag detection: '--skip-unzip'"
	echo ""
fi

if ! "$skip_gpth_tool"; then
	echo ""
	echo "============================================================================"
	echo "2. FIXING PHOTOS METADATA WITH GPTH TOOL AND COPYING IT TO OUTPUT FOLDER..."
	echo "============================================================================"
	echo ""
    # Inicia el temporizador parcial
    partial_start_time=$(date +%s)
  
	if [ "$flatten_albums" = true ] && [ "$flatten_no_albums" = true ]; then
		./gpth_tool/gpth --input "$takeout_folder" --output "$output_folder" --skip-extras --copy --albums "duplicate-copy" --no-divide-to-dates
	else
		./gpth_tool/gpth --input "$takeout_folder" --output "$output_folder" --skip-extras --copy --albums "duplicate-copy" --divide-to-dates 
		if "$flatten_albums"; then
			echo ""
			echo "INFO: Since Flag '--flatten-albums' have been detected, we are now flattening out individually all albums folder to remove year/month structure..."
			echo ""
			# Función para aplanar todos los albumes (excluyendo la carpeta ALL_PHOTOS)
			flatten_subfolders -i "$output_folder" -e ALL_PHOTOS	
		fi
		if "$flatten_no_albums"; then
			echo ""
			echo "INFO: Since Flag '--flatten-no-albums' have been detected, we are now flattening out ALL_PHOTOS folder to remove year/month structure..."
			echo ""	
			# cFunción para aplanar r la carpeta ALL_PHOTOS que está dentro de la carpeta de salida
			flatten_subfolders -i "$output_folder/ALL_PHOTOS"
		fi
	    echo ""
	fi
    
    # Finaliza el temporizador parcial y muestra el tiempo por pantalla
    current_time=$(date +%s)
    step_time=$((current_time - partial_start_time))
    elapsed_time=$((current_time - start_time))
    echo "INFO: Step time   : $((step_time / 60)) minutes and $((step_time % 60)) seconds."
    echo "INFO: Elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."
    echo ""  
else
	echo ""
	echo "======================================"
	echo "2. COPYING PHOTOS TO OUTPUT FOLDER..."
	echo "======================================"
	echo ""
    # Inicia el temporizador parcial
    partial_start_time=$(date +%s)
    
	echo "INFO: Since Flag '--skip-gpth-toot' have been detected, we are skipping GPTH Tool processing and we are now manually copying files to output folder: '"$output_folder"'..."
	echo ""
	# Detecta el directorio principal de la carpeta de entrada (aquel del que cuelgan todas las subcarpetas), y copia todas las subcarpetas a la carpeta destino en un mismo nivel excepto las carpetas que comiencen por 'Photos from dddd' y ALL_PHOTOS que se copiaran en una subcarpeta llamada ALL_PHOTOS en la carpeta de destino.
	DIRECTORIO_ORIGEN="$takeout_folder"; 
	DIRECTORIO_DESTINO="$output_folder"; 
	DIRECTORIO_ACTUAL="$DIRECTORIO_ORIGEN";
	while true; do NUM_DIRS=$(find "$DIRECTORIO_ACTUAL" -mindepth 1 -maxdepth 1 -type d | wc -l); NUM_FILES=$(find "$DIRECTORIO_ACTUAL" -mindepth 1 -maxdepth 1 -type f | wc -l); if [ "$NUM_DIRS" -eq 1 ] && [ "$NUM_FILES" -eq 0 ]; then DIRECTORIO_ACTUAL=$(find "$DIRECTORIO_ACTUAL" -mindepth 1 -maxdepth 1 -type d); else break; fi; done; mkdir -p "$DIRECTORIO_DESTINO/ALL_PHOTOS"; for dir in "$DIRECTORIO_ACTUAL"/Photos\ from\ [1-2][0-9][0-9][0-9]; do if [ -d "$dir" ]; then cp -r "$dir" "$DIRECTORIO_DESTINO/ALL_PHOTOS/"; fi; done; if [ -d "$DIRECTORIO_ACTUAL/ALL_PHOTOS" ]; then cp -r "$DIRECTORIO_ACTUAL/ALL_PHOTOS/"* "$DIRECTORIO_DESTINO/ALL_PHOTOS/"; fi; for dir in "$DIRECTORIO_ACTUAL"/*; do if [ -d "$dir" ] && [[ ! "$dir" =~ Photos\ from\ [1-2][0-9][0-9][0-9] ]] && [ "$(basename "$dir")" != "ALL_PHOTOS" ]; then cp -r "$dir" "$DIRECTORIO_DESTINO/"; fi; done
    
    # Finaliza el temporizador parcial y muestra el tiempo por pantalla
    current_time=$(date +%s)
    step_time=$((current_time - partial_start_time))
    elapsed_time=$((current_time - start_time))
    echo "INFO: Step time   : $((step_time / 60)) minutes and $((step_time % 60)) seconds."
    echo "INFO: Elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."
    echo ""  
fi


if ! "$skip_move_albums"; then
	echo ""
	echo "=========================="
	echo "3. MOVING ALBUMS FOLDER..."
	echo "=========================="
	echo ""	
    # Inicia el temporizador parcial
    partial_start_time=$(date +%s)
    
    # Move All albums to Album folder
	move_albums -i "$output_folder" -a "Albums"
    
    # Finaliza el temporizador parcial y muestra el tiempo por pantalla
    current_time=$(date +%s)
    step_time=$((current_time - partial_start_time))
    elapsed_time=$((current_time - start_time))
    echo "INFO: Step time   : $((step_time / 60)) minutes and $((step_time % 60)) seconds."
    echo "INFO: Elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."
    echo ""      
else
	echo ""
	echo "=========================="
	echo "3. MOVING ALBUMS FOLDER..."
	echo "=========================="
	echo ""	
	echo "INFO: Step skipped due to Flag detection: '--skip_move_albums'"
	echo ""	
fi

if ! "$skip_exif_tool"; then
	echo ""
	echo "==========================================="
	echo "4. FIXING PHOTOS METADATA WITH EXIF TOOL..."
	echo "==========================================="
	echo ""	
    # Inicia el temporizador parcial
    partial_start_time=$(date +%s)
    
	echo "INFO: Scanning output folder: '"$output_folder"' to fix EXIF data..."
	#./exif_tool/exiftool "$output_folder" -overwrite_original -r -if 'not defined DateTimeOriginal' -P "-AllDates<FileModifyDate"
	./exif_tool/exiftool "$output_folder" -overwrite_original -ExtractEmbedded -r '-datetimeoriginal<filemodifydate' -if '(not $datetimeoriginal or ($datetimeoriginal eq "0000:00:00 00:00:00"))'
    
    # Finaliza el temporizador parcial y muestra el tiempo por pantalla
    current_time=$(date +%s)
    step_time=$((current_time - partial_start_time))
    elapsed_time=$((current_time - start_time))
    echo "INFO: Step time   : $((step_time / 60)) minutes and $((step_time % 60)) seconds."
    echo "INFO: Elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."
    echo ""      
else
	echo ""
	echo "==========================================="
	echo "4. FIXING PHOTOS METADATA WITH EXIF TOOL..."
	echo "==========================================="
	echo ""
	echo "INFO: Step skipped due to Flag detection: '--skip_exif_tool'"
	echo ""
fi


# Variables para el Resumen final
files_unzipped=0
photos_videos_without_duplicates=0
photos_videos_without_album=0
photos_videos_within_album=0
total_albums=0

# Conteo para el Resumen final
if [ -d "$takeout_folder" ]; then
	files_unzipped=$(count_files_in_folder "$takeout_folder")
fi
if [ -d "$output_folder" ]; then
	photos_videos_without_duplicates=$(count_files_in_folder "$output_folder")
	photos_videos_without_album=$(count_files_in_folder "$output_folder/ALL_PHOTOS")
	photos_videos_within_album=$(count_files_in_folder "$output_folder/Albums")
	total_albums=$(find "$output_folder/Albums" -mindepth 1 -type d | wc -l)	
fi

echo ""
echo "=================================================="
echo "PROCESS COMPLETED SUMMARY:"
echo "=================================================="
echo ""
echo "INFO: Total files unpacked (including duplicates and metadata): $files_unzipped"
echo "INFO: Total photos/videos (without duplicates if GPTH tool was executed): $photos_videos_without_duplicates"
echo "INFO: Total photos/videos without albums: $photos_videos_without_album"
echo "INFO: Total photos/videos within any album: $photos_videos_within_album"
echo "INFO: Total albums folders found: $total_albums"

# Finaliza el temporizador
end_time=$(date +%s)
# Calcula el tiempo total transcurrido
elapsed_time=$((end_time - start_time))

echo ""
echo "INFO: Process Completed with success!. All your photos should be fixed and organized now in the folder: '"$output_folder"'"
echo ""
echo "INFO: Log file with all messages during the execution of this script has been saved saved into file: '"$log_file"'"
echo ""
echo "INFO: Total elapsed time: $((elapsed_time / 60)) minutes and $((elapsed_time % 60)) seconds."

echo ""
echo "================================="
echo "PROCESS COMPLETED WITH SUCCESS!!!"
echo "================================="
echo ""
