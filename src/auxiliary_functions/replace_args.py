import re
import sys

def replace_args_syntax(file_path):
    """
    Reemplaza todas las ocurrencias de 'args.<variable>' por 'ARGS["variable-modificada"]' en un archivo.
    La variable modificada cambia los guiones bajos (_) por guiones medios (-).

    :param file_path: Ruta del archivo a procesar
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Expresión regular para encontrar args.<variable> con múltiples palabras separadas por guiones bajos
    pattern = re.compile(r'args\.([a-zA-Z_]+)')

    def replacement(match):
        var_name = match.group(1).replace('_', '-')
        return f"ARGS['{var_name}']"

    modified_content = pattern.sub(replacement, content)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

    print(f"Procesado: {file_path}")

if __name__ == "__main__":
    replace_args_syntax('OrganizeTakeoutPhotos_test.py')
