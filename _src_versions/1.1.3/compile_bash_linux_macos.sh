#!/bin/bash

# Funci�n para extraer el valor entre comillas despu�s de SCRIPT_VERSION
get_script_version() {
    local file="$1" # Nombre del archivo pasado como argumento

    # Comprobar si el archivo existe
    if [[ ! -f "$file" ]]; then
        echo "Error: El archivo $file no existe." >&2
        return 1
    fi

    # Buscar la l�nea que comienza con SCRIPT_VERSION y extraer el contenido entre comillas
    local script_version
    script_version=$(grep -E '^SCRIPT_VERSION' "$file" | sed -E 's/^SCRIPT_VERSION.*"([^"]*)".*/\1/')

    # Verificar si se encontr� un valor v�lido
    if [[ -z "$script_version" ]]; then
        echo "Error: No se encontr� un valor entre comillas despu�s de SCRIPT_VERSION en el archivo." >&2
        return 1
    fi

    # Devolver el valor encontrado
    echo "$script_version"
    return 0
}

SCRIPT_NAME="OrganizeTakeoutPhotos"
SCRIPT_ORIGINAL="$SCRIPT_NAME.sh"
SCRIPT_COMPILED="${SCRIPT_NAME}_bash.run"
SCRIPT_VERSION=$(get_script_version $SCRIPT_ORIGINAL)

if [[ $? -eq 0 ]]; then
    echo "SCRIPT_VERSION encontrado: $SCRIPT_VERSION"
else
    echo "No se pudo obtener SCRIPT_VERSION."
fi

SCRIPT_NAME_VERSION="$SCRIPT_NAME"_"$SCRIPT_VERSION"
SCRIPT_ZIP_FILE="./built_versions/${SCRIPT_NAME_VERSION}_bash_linux_mac.zip"
SCRIPT_ZIP_FILE=$(realpath "$SCRIPT_ZIP_FILE")


# Funci�n para comprimir un fichero y carpetas
compress_file_and_folders() {
    local input_file=""
    local output_file=""
    local extra_folders=()
    local temp_dir=""

    # Parsear los argumentos
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -i|--input-file) input_file="$2"; shift ;;
            -o|--output-file) output_file="$2"; shift ;;
            *) echo "Opci�n desconocida: $1" >&2; exit 1 ;;
        esac
        shift
    done

    # Definir carpetas adicionales a incluir
    extra_folders=("./exif_tool" "./gpth_tool")

    # Comprobar si los par�metros son v�lidos
    if [[ -z "$input_file" || -z "$output_file" ]]; then
        echo "Uso: compress_file_and_folders -i <input_file> -o <output_file>"
        exit 1
    fi

    # Verificar que el archivo de entrada existe
    if [[ ! -f "$input_file" ]]; then
        echo "Error: El archivo de entrada '$input_file' no existe." >&2
        exit 1
    fi

    # Crear un directorio temporal
    temp_dir=$(mktemp -d)
    mkdir -p "$temp_dir/$SCRIPT_NAME_VERSION/"
    
    # Creamos dentro del directorio temporal la carpeta "../Zip_files"
    mkdir -p "$temp_dir/$SCRIPT_NAME_VERSION/Zip_files/"

    # Comprobar si la carpeta se cre� correctamente
    if [[ ! -d "$temp_dir/$SCRIPT_NAME_VERSION" ]]; then
        echo "Error: No se pudo crear la carpeta temporal '$temp_dir/$SCRIPT_NAME'."
        exit 1
    fi

    # Copiar el archivo al directorio temporal
    cp "$input_file" "$temp_dir/$SCRIPT_NAME_VERSION/$(basename "$input_file")"
    for folder in "${extra_folders[@]}"; do
        if [[ -d "$folder" ]]; then
            cp -r "$folder" "$temp_dir/$SCRIPT_NAME_VERSION/"
        else
            echo "Advertencia: La carpeta '$folder' no existe y no ser� incluida." >&2
        fi
    done

    # Crear el archivo ZIP con la carpeta ra�z como $SCRIPT_NAME
    echo "Creando el archivo comprimido: "$output_file"..."
    (cd "$temp_dir" && zip -r "$output_file" "$SCRIPT_NAME_VERSION") > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        echo "Archivo comprimido correctamente: "$output_file""
    else
        echo "Error al comprimir el archivo y las carpetas."
        exit 1
    fi

    # Eliminar el directorio temporal
    rm -rf "$temp_dir"
}

# Limpiamos la pantalla antes de empezar
#clear

# Compilamos el fichero y Movemos el fichero compilado a la carpeta raiz del script
echo "Compilando el Script '$SCRIPT_ORIGINAL' como '$SCRIPT_COMPILED'..."
shc -f $SCRIPT_ORIGINAL -o $SCRIPT_COMPILED -r
rm ./$SCRIPT_NAME.sh.x.c

# Comprimimos el fichero en el fichero de salida
compress_file_and_folders -i "${SCRIPT_COMPILED}" -o "${SCRIPT_ZIP_FILE}"
mv ./$SCRIPT_COMPILED ../data/$SCRIPT_COMPILED
echo ""