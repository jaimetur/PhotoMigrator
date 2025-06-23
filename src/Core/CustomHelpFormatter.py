import argparse
import re
import textwrap

from colorama import Fore, Style

from Core.GlobalVariables import MAX_HELP_POSITION, MAX_SHORT_ARGUMENT_LENGTH, IDENT_ARGUMENT_DESCRIPTION, IDENT_USAGE_DESCRIPTION


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        # Configura la anchura máxima del texto de ayuda
        kwargs['width'] = MAX_HELP_POSITION  # Ancho total del texto de ayuda
        kwargs['max_help_position'] = MAX_HELP_POSITION  # Ajusta la posición de inicio de las descripciones
        super().__init__(*args, **kwargs)

    def _tokenize_usage(self, usage_text):
        # 1) Sustituimos saltos de línea por espacio (para no partir el texto en varias líneas).
        flattened = usage_text.replace('\n', ' ')
        def parse_brackets(s):
            print("entro en parse_brackets")
            tokens = []
            i = 0
            n = len(s)
            while i < n:
                # Saltamos espacios iniciales
                if s[i].isspace():
                    i += 1
                    continue
                # Si encontramos un '[' => parseamos el contenido (anidado) hasta el corchete de cierre emparejado
                if s[i] == '[':
                    start = i
                    bracket_count = 1  # hemos encontrado un '['
                    i += 1
                    # Avanzamos hasta cerrar todos los corchetes '[' pendientes
                    while i < n and bracket_count > 0:
                        if s[i] == '[':
                            bracket_count += 1
                        elif s[i] == ']':
                            bracket_count -= 1
                        i += 1
                    # i está ahora justo detrás del corchete de cierre
                    tokens.append(s[start:i])  # incluimos el bloque completo con sus corchetes
                else:
                    # Caso: token "normal" (no empieza por '[')
                    start = i
                    # Avanzamos hasta encontrar un espacio o un '['
                    while i < n and not s[i].isspace() and s[i] != '[':
                        i += 1
                    tokens.append(s[start:i])
            return tokens
        tokens = parse_brackets(flattened)
        # Devolvemos como una sola "línea" con indent vacío
        return [('', tokens)]

    def _build_lines_with_forced_tokens(
            self,
            tokenized_usage,
            forced_tokens,
            width,
            first_line_indent = '',
            subsequent_indent = ' ' * IDENT_USAGE_DESCRIPTION
        ):
        print("entro en _build_lines_with_forced_tokens")
        final_lines = []
        for (orig_indent, tokens) in tokenized_usage:
            if not tokens:
                final_lines.append(orig_indent)
                continue

            current_line = first_line_indent
            current_len  = len(first_line_indent)
            first_token  = True
            line_number  = 0
            for token in tokens:
                match_forced = next((forced_token for forced_token in forced_tokens if token.startswith(forced_token)), None)
                if match_forced is not None:
                    must_be_alone = forced_tokens[match_forced]
                    # Forzamos salto de línea antes (si no estamos al inicio)
                    if not first_token:
                        final_lines.append(current_line)
                        current_line = subsequent_indent
                        current_len  = len(subsequent_indent)
                        first_token  = True
                        line_number += 1
                    if must_be_alone:
                        # Va solo en su línea
                        forced_line = (subsequent_indent if line_number > 0 else first_line_indent) + token
                        final_lines.append(forced_line)
                        current_line = subsequent_indent
                        current_len  = len(subsequent_indent)
                        first_token  = True
                        line_number += 1
                        continue
                # Lógica normal de añadir token
                if first_token:
                    current_line += token
                    current_len += len(token)
                    first_token = False
                else:
                    needed_len = current_len + 1 + len(token)
                    if needed_len > width:
                        final_lines.append(current_line)
                        line_number += 1
                        current_line = subsequent_indent + token
                        current_len  = len(subsequent_indent) + len(token)
                        first_token  = False
                    else:
                        current_line += ' ' + token
                        current_len = needed_len
            # Al acabar los tokens, si la línea no está vacía, la agregamos
            if current_line.strip():
                final_lines.append(current_line)
                line_number += 1
        return '\n'.join(final_lines)

    def _format_usage(self, usage, actions, groups, prefix, **kwargs):
        def remove_chain(usage, chain_to_remove):
            print("entro en remove_chain")
            # 1) Unir todas las líneas (sustituir saltos de línea por espacio)
            usage_single_line = usage.replace('\n', ' ')
            # 2) Reemplazar 2 o más espacios consecutivos por uno solo
            usage_single_line = re.sub(r' {2,}', ' ', usage_single_line)
            # 3) Remover 'chain_to_remove'
            usage_single_line = usage_single_line.replace(chain_to_remove, '')
            return usage_single_line
        # 1) Uso básico de la clase padre
        usage = super()._format_usage(usage, actions, groups, prefix)
        # 2) Eliminamos el bloque con <DUPLICATES_ACTION> ...
        # usage = remove_chain(usage, "[<ACTION>> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...] ...]")
        usage = remove_chain(usage, "[<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...] ...]")
        # 3) Quitamos los espacios antes de los ... y antes del último corchete
        usage = usage.replace(" ...] ]", "...]]")
        # 4) Eliminamos el bloque con <ALBUMS_NAME_PATTERN> ...
        usage = remove_chain(usage, "[<ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN> ...]")
        # 5) Quitamos los espacios antes del último corchete
        usage = usage.replace(" ]", "]")
        # 6) Tokenizamos con la nueva lógica (anidado)
        tokenized = self._tokenize_usage(usage)
        # 7) Diccionario de tokens forzados
        force_new_line_for_tokens = {
            "[-from <FROM_DATE>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-country <COUNTRY_NAME>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-gpthInfo [= [true,false]]]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-i <INPUT_FOLDER>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-gTakeout <TAKEOUT_FOLDER>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-iuAlb <ALBUMS_FOLDER>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-uAlb <ALBUMS_FOLDER>]": False,   # Salto de línea antes, pero sigue reagrupando
            # "[-irEmpAlb]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-fixSym <FOLDER_TO_FIX>]": False,   # Salto de línea antes, pero sigue reagrupando
            "[-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]": True,  # Va solo
        }
        # 6) Ancho real
        max_width = getattr(self, '_width', 90)
        # 7) Reconstruimos con indentaciones
        ident_spaces = IDENT_USAGE_DESCRIPTION
        usage = self._build_lines_with_forced_tokens(
            tokenized_usage   = tokenized,
            forced_tokens     = force_new_line_for_tokens,
            width             = max_width,
            first_line_indent = '',         # Sin espacios en la primera línea
            subsequent_indent = ' ' * ident_spaces    # 32 espacios en líneas siguientes, por ejemplo
        )
        usage = f'{Fore.GREEN}{usage}{Style.RESET_ALL}'
        return usage

    def _format_action(self, action):
        def justificar_texto(text, initial_indent="", subsequent_indent=""):
            print("entro en justificar_texto")
            # 1. Separar en líneas
            lines = text.splitlines()
            # 2. Aplicar fill() a cada línea
            wrapped_lines = [
                 textwrap.fill(
                     line,
                     width=self._width,
                     initial_indent=initial_indent,
                     subsequent_indent=subsequent_indent
                 )
                 for line in lines
            ]
            # 3. Unirlas de nuevo con saltos de línea
            return "\n".join(wrapped_lines)
        # Encabezado del argumento
        parts = [self._format_action_invocation(action)]

        # Texto de ayuda, formateado e identado
        if action.help:
            help_text = justificar_texto(action.help, initial_indent=" " * IDENT_ARGUMENT_DESCRIPTION, subsequent_indent=" " * IDENT_ARGUMENT_DESCRIPTION)

            # AUTOMATIC-MIGRATION PROCESS: two lines before "Select the <SOURCE> for the AUTOMATIC-MIGRATION Process"
            if help_text.find("Select the <SOURCE> for the AUTOMATIC-MIGRATION Process")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                AUTOMATIC MIGRATION PROCESS:
                ----------------------------{Style.RESET_ALL}
                Following arguments allow you execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service. 

                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")


            # AUTOMATIC-MIGRATION PROCESS: two lines before "Select the <SOURCE> for the AUTOMATIC-MIGRATION Process"
            if help_text.find("Specify the input folder that you want to process.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                GENERAL ARGUMENTS:
                ------------------{Style.RESET_ALL}
                Following general arguments have different purposses depending on the Execution Mode. 
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")


            # FEATURES for Google Photos Takeout Management: two lines before "Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata"
            if help_text.find("Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                GOOGLE PHOTOS TAKEOUT MANAGEMENT:
                ---------------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Google Photos Takeout Folder. 
                In this mode, you can use more than one optional arguments from the below list.
                If only the argument -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the Tool will use the default values for the rest of the arguments for this extra mode.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # FEATURES for Synology Photos Management: two lines before the string
            if help_text.find("and will create one Album per subfolder into Synology Photos.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                SYNOLOGY PHOTOS MANAGEMENT:
                ---------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Synology Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # FEATURES for Immich Photos Management: two lines before the string
            if help_text.find("and will create one Album per subfolder into Immich Photos.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                IMMICH PHOTOS MANAGEMENT:
                -------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Immich Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # FEATURES for Synology/Immich Photos Management: two lines before the string
            if help_text.find("will create one Album per subfolder into the selected Photo client.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                SYNOLOGY/IMMICH PHOTOS MANAGEMENT:
                ----------------------------------{Style.RESET_ALL}
                To use following features, it is mandatory to use the argument '--client=[synology, immich]' to specify which Photo Service do you want to use.   
                
                You can optionally use the argument '--id=[1-3]' to specify the account id for a particular account defined in Config.ini.                  
                
                Following arguments allow you to interact with Synology/Immich Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # OTHERS STANDALONE FEATURES: two lines before "The Tool will try to fix all symbolic links for Albums"
            if help_text.find("The Tool will try to fix all symbolic links for Albums")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                OTHER STANDALONE FEATURES:
                --------------------------{Style.RESET_ALL}
                Following arguments can be used to execute the Tool in any of the usefull additionals Extra Standalone Features included. 
                If more than one Feature is detected, only the first one will be executed.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # if Detect CAUTION part on help_text, color it on Red
            if help_text.find("CAUTION: ")!=-1:
                start_index_for_color = help_text.find("CAUTION: ")
                # end_index_for_color = help_text.find(" Use")
                end_index_for_color = len(help_text)
                TEXT_TO_INSERT = f"\n{help_text[0:start_index_for_color]}{Fore.RED}{help_text[start_index_for_color:end_index_for_color]}{Style.RESET_ALL}{help_text[end_index_for_color:]}"
                parts.append(f"{TEXT_TO_INSERT}")
            else:
                parts.append(f"\n{help_text}")  # Salto de línea adicional

        return "".join(parts)

    def _format_action_invocation(self, action):
        print("entro en _format_action_invocation")
        if not action.option_strings:
            # Para argumentos posicionales
            return super()._format_action_invocation(action)
        else:
            # Combina los argumentos cortos y largos con espacio adicional si es necesario
            option_strings = []
            for opt in action.option_strings:
                # Argumento corto, agrega una coma detrás
                if opt.startswith("-") and not opt.startswith("--"):
                    option_strings.append(f"{opt.ljust(MAX_SHORT_ARGUMENT_LENGTH)};")
                else:
                    option_strings.append(f"{opt}")

            # Combina los argumentos cortos y largos, y agrega el parámetro si aplica
            formatted_options = " ".join(option_strings).rstrip(",")
            metavar = f" {action.metavar}" if action.metavar else ""
            return f"{Fore.GREEN}{formatted_options}{metavar}{Style.RESET_ALL}"

    def _join_parts(self, part_strings):
        # Asegura que cada argumento quede separado por un salto de línea
        return "\n".join(part for part in part_strings if part)

