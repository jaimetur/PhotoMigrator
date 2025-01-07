#!/bin/bash
SCRIPT_NAME="OrganizeTakeoutPhotos"
PLATTFORM="macos"
SCRIPT_ORIGINAL="$SCRIPT_NAME.py"
SCRIPT_COMPILED="$SCRIPT_NAME.run"

# Limpiamos la pantalla antes de empezar
clear

# Función para comprimir un fichero y carpetas
compress_file_and_folders() {
    local input_file=""
    local output_file=""
    local extra_folders=()
    local extra_files=()
    local temp_dir=""

    # Parsear los argumentos
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -i|--input-file) input_file="$2"; shift ;;
            -o|--output-file) output_file="$2"; shift ;;
            *) echo "Opción desconocida: $1" >&2; exit 1 ;;
        esac
        shift
    done

    # Definir carpetas y ficheros adicionales a incluir
    # extra_folders=("./exif_tool" "./gpth_tool")
    extra_files=("./nas.config" "./README.md")

    # Comprobar si los parámetros son válidos
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
    
    # Creamos dentro del directorio temporal la carpeta "./Zip_files"
    mkdir -p "$temp_dir/$SCRIPT_NAME_VERSION/Zip_files/"

    # Comprobar si la carpeta se creó correctamente
    if [[ ! -d "$temp_dir/$SCRIPT_NAME_VERSION" ]]; then
        echo "Error: No se pudo crear la carpeta temporal '$temp_dir/$SCRIPT_NAME'."
        exit 1
    fi

    # Copiar el archivo y las carpetas indicadas (opcional) al directorio temporal
    cp "$input_file" "$temp_dir/$SCRIPT_NAME_VERSION/$(basename "$input_file")"
    for folder in "${extra_folders[@]}"; do
        if [[ -d "$folder" ]]; then
            cp -r "$folder" "$temp_dir/$SCRIPT_NAME_VERSION/"
        else
            echo "Advertencia: La carpeta '$folder' no existe y no será incluida." >&2
        fi
    done
    
    # Copiar los extra_files (opcional) al directorio temporal
    for file in "${extra_files[@]}"; do
        cp "$file" "$temp_dir/$SCRIPT_NAME_VERSION/"
    done

    # Guardamos el directorio de trabajo
    working_dir=$(pwd)
    
    # Crear el archivo ZIP con la carpeta raíz como $SCRIPT_NAME
    echo "Creando el archivo comprimido: "$output_file"..."
    (cd "$temp_dir" && zip -r "$output_file" "$SCRIPT_NAME_VERSION")# > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        echo "Archivo comprimido correctamente: "$output_file""
    else
        echo "Error al comprimir el archivo y las carpetas."
        exit 1
    fi
    
    # Volvemos al directorio de ejecución
    cd "$working_dir"

    # Eliminar el directorio temporal
    rm -rf "$temp_dir"
}

# Función para extraer el valor entre comillas después de SCRIPT_VERSION
get_script_version() {
    local file="$1" # Nombre del archivo pasado como argumento

    # Comprobar si el archivo existe
    if [[ ! -f "$file" ]]; then
        echo "Error: El archivo $file no existe." >&2
        return 1
    fi

    # Buscar la línea que comienza con SCRIPT_VERSION y extraer el contenido entre comillas
    local script_version
    script_version=$(grep -E '^SCRIPT_VERSION' "$file" | sed -E 's/^SCRIPT_VERSION.*"([^"]*)".*/\1/')

    # Verificar si se encontró un valor válido
    if [[ -z "$script_version" ]]; then
        echo "Error: No se encontró un valor entre comillas después de SCRIPT_VERSION en el archivo." >&2
        return 1
    fi

    # Devolver el valor encontrado
    echo "$script_version"
    return 0
}
SCRIPT_VERSION=$(get_script_version $SCRIPT_ORIGINAL)

if [[ $? -eq 0 ]]; then
    echo "SCRIPT_VERSION encontrado: $SCRIPT_VERSION"
else
    echo "No se pudo obtener SCRIPT_VERSION."
fi

SCRIPT_NAME_VERSION="$SCRIPT_NAME"_"$SCRIPT_VERSION"
SCRIPT_ZIP_FILE="../built_versions/${SCRIPT_NAME_VERSION}_${PLATTFORM}.zip"
SCRIPT_ZIP_FILE=$(cd "$(dirname "$SCRIPT_ZIP_FILE")" && pwd)/$(basename "$SCRIPT_ZIP_FILE")

# Borramos los archivos temporales de la compilación anterior si los hubiera
echo "Borrando archivos temporales de compilaciones previas..."
rm $SCRIPT_NAME.spec
rm -d -r build
rm -d -r dist
echo ""

# Compilamos el fichero y Movemos el fichero compilado a la carpeta raiz del script
echo "Compilando el Script $SCRIPT_ORIGINAL como $SCRIPT_COMPILED..."
pyinstaller --runtime-tmpdir /var/tmp --onefile --add-data "gpth_tool_"$PLATTFORM":gpth_tool" --add-data "exif_tool_"$PLATTFORM":exif_tool" $SCRIPT_ORIGINAL

# Comprimimos el fichero en el fichero de salida
echo ""
echo "Comprimiendo script compilado '"${SCRIPT_COMPILED}"' a '"${SCRIPT_ZIP_FILE}"'..."
mv -f ./dist/$SCRIPT_NAME ../$SCRIPT_COMPILED
compress_file_and_folders -i "../${SCRIPT_COMPILED}" -o "${SCRIPT_ZIP_FILE}"

# Borramos los archivos temporales de la compilación
echo "Borrando archivos temporales de la compilación..."
rm $SCRIPT_NAME.spec
rm -d -r build
rm -d -r dist

echo ""
echo "Compilación concluida con éxito."
echo "Script compilado: "${SCRIPT_COMPILED}""
echo "Script comprimido: "${SCRIPT_ZIP_FILE}""
echo ""





