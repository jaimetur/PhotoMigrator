from GLOBALS import SCRIPT_NAME_VERSION

import textwrap
import argparse
import re
import os, sys
import platform
from colorama import  Fore, Style

if platform.system() == "Windows":
    try:
        import curses
    except ImportError:
        raise ImportError("Instala 'windows-curses' para soporte en Windows: pip install windows-curses")
else:
    import curses

class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        # Configura la anchura máxima del texto de ayuda
        kwargs['width'] = 88  # Ancho total del texto de ayuda
        kwargs['max_help_position'] = 55  # Ajusta la posición de inicio de las descripciones
        super().__init__(*args, **kwargs)

    def _tokenize_usage(self, usage_text):
        # 1) Sustituimos saltos de línea por espacio (para no partir el texto en varias líneas).
        flattened = usage_text.replace('\n', ' ')
        def parse_brackets(s):
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
            subsequent_indent = ' ' * 32
        ):
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
        # 4) Tokenizamos con la nueva lógica (anidado)
        tokenized = self._tokenize_usage(usage)
        # 5) Diccionario de tokens forzados
        force_new_line_for_tokens = {
            "[-gitf <TAKEOUT_FOLDER>]": False   # Salto de línea antes, pero sigue reagrupando
            ,"[-irEmpAlb]": False   # Salto de línea antes, pero sigue reagrupando
            ,"[-fixSym <FOLDER_TO_FIX>]": False   # Salto de línea antes, pero sigue reagrupando
            ,"[-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]": True  # Va solo
        }
        # 6) Ancho real
        max_width = getattr(self, '_width', 90)
        # 7) Reconstruimos con indentaciones
        ident_spaces = 32
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
            ident_spaces = 13
            help_text = justificar_texto(action.help, initial_indent=" " * ident_spaces, subsequent_indent=" " * ident_spaces)

            # EXTRA MODES for Google Photos Takeout Management: two lines before "Specify the Takeout folder to process."
            if help_text.find("Specify the Takeout folder to process.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                GOOGLE PHOTOS TAKEOUT MANAGEMENT:
                ---------------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Google Photos Takeout Folder. 
                In this mode, you can use more than one optional arguments from the below list.
                If only the argument -gtif, --google-takeout-input-folder <TAKEOUT_FOLDER> is detected, then the script will use the default values for the rest of the arguments for this extra mode.
                """)
                TEXT_TO_INSERT = justificar_texto(TEXT_TO_INSERT)+'\n\n'
                parts.insert(-1,f"{TEXT_TO_INSERT}")

            # EXTRA MODES for Synology Photos Management: two lines before the string
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

            # EXTRA MODES for Immich Photos Management: two lines before the string
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

            # OTHERS STANDALONE EXTRA MODES: two lines before "Find duplicates in specified folders."
            if help_text.find("Find duplicates in specified folders.")!=-1:
                TEXT_TO_INSERT =textwrap.dedent(f"""
                {Fore.YELLOW}
                OTHER STANDALONE EXTRA MODES:
                -----------------------------{Style.RESET_ALL}
                Following arguments can be used to execute the Script in any of the usefull additionals Extra Modes included.
                If more than one Extra Mode is detected, only the first one will be executed.
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
        if not action.option_strings:
            # Para argumentos posicionales
            return super()._format_action_invocation(action)
        else:
            # Combina los argumentos cortos y largos con espacio adicional si es necesario
            option_strings = []
            for opt in action.option_strings:
                # Argumento corto, agrega una coma detrás
                if opt.startswith("-") and not opt.startswith("--"):
                    if len(opt) == 9:
                        option_strings.append(f"{opt},")
                    if len(opt) == 8:
                        option_strings.append(f"{opt}, ")
                    if len(opt) == 7:
                        option_strings.append(f"{opt},  ")
                    if len(opt) == 6:
                        option_strings.append(f"{opt},   ")
                    if len(opt) == 5:
                        option_strings.append(f"{opt},    ")
                    if len(opt) == 4:
                        option_strings.append(f"{opt},     ")
                    elif len(opt) == 3:
                        option_strings.append(f"{opt},      ")
                    elif len(opt) == 2:
                        option_strings.append(f"{opt},       ")
                else:
                    option_strings.append(f"{opt}")

            # Combina los argumentos cortos y largos, y agrega el parámetro si aplica
            formatted_options = " ".join(option_strings).rstrip(",")
            metavar = f" {action.metavar}" if action.metavar else ""
            return f"{Fore.GREEN}{formatted_options}{metavar}{Style.RESET_ALL}"

    def _join_parts(self, part_strings):
        # Asegura que cada argumento quede separado por un salto de línea
        return "\n".join(part for part in part_strings if part)

class PagedArgumentParser(argparse.ArgumentParser):
    """
    Sobrescribimos ArgumentParser para que 'print_help()' use un paginador.
    """
    global SCRIPT_DESCRIPTION

    def custom_pager(self, text):
        """
        Paginador con curses que adapta dinámicamente el texto al tamaño de la terminal.
        """

        # Expresión regular para detectar códigos ANSI
        ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

        global usage_first_line, usage_last_line
        usage_first_line = -1
        usage_last_line = -1
        caution_ranges = []  # Lista para almacenar rangos de líneas de "CAUTION:"
        optional_arguments_line = -1  # Línea que contiene "optional arguments:"

        lines = text.splitlines()

        # Determinar los índices de inicio y fin de la sección "usage"
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)  # Eliminar secuencias ANSI de colorama
            if 'usage' in clean_line.lower() and usage_first_line == -1:  # Detectar la primera línea con "usage"
                usage_first_line = i
            if SCRIPT_NAME_VERSION in clean_line:  # Detectar la última línea de "usage" (pero NO pintarla en verde)
                usage_last_line = i - 1  # Detener una línea antes de SCRIPT_NAME_VERSION
                break  # No hace falta seguir buscando

        # Determinar todos los bloques de "CAUTION:"
        caution_start = -1
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)
            if 'CAUTION:' in clean_line:  # Detectar cualquier aparición de "CAUTION:"
                if caution_start == -1:  # Si no hemos iniciado un bloque, marcar el inicio
                    caution_start = i
            elif caution_start != -1 and (re.match(r"^\s*-\w", clean_line) or clean_line.strip() == ""):
                caution_ranges.append((caution_start, i - 1))  # Guardar el rango hasta la línea anterior
                caution_start = -1  # Reiniciar para detectar más bloques

        # Buscar la línea que contiene "optional arguments:"
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)
            if 'optional arguments:' in clean_line.lower():
                optional_arguments_line = i
                break  # No hace falta seguir buscando más de una vez

        def pager(stdscr):
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Verde (para argumentos y usage)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Magenta (para separadores y líneas anteriores)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Rojo (para secciones de CAUTION)
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # Amarillo con fondo azul (para "optional arguments")
            curses.curs_set(0)  # Ocultar el cursor
            total_lines = len(lines)
            page_size = curses.LINES - 2  # Altura de la terminal menos espacio para el mensaje
            index = 0

            while True:
                stdscr.clear()
                prev_line = None  # Variable para almacenar la línea anterior

                for i, line in enumerate(lines[index:index+page_size]):
                    try:
                        clean_line = ANSI_ESCAPE.sub('', line)  # Eliminar secuencias ANSI de colorama
                        line_number = index + i  # Línea absoluta en el texto

                        # Pintar todas las líneas dentro del bloque "usage" en verde (excepto la línea con SCRIPT_NAME_VERSION)
                        if usage_first_line <= line_number <= usage_last_line:
                            stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(1))  # Verde
                        # Pintar todas las líneas dentro de cualquier bloque "CAUTION:" en rojo
                        elif any(start <= line_number <= end for start, end in caution_ranges):
                            stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(3))  # Rojo
                        # Pintar la línea que contiene "optional arguments:" en amarillo
                        elif line_number == optional_arguments_line:
                            stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(4))  # Amarillo
                        else:
                            # Detectar si la línea actual es un separador (--- o más guiones)
                            is_separator = re.match(r"^\s*-{3,}", clean_line)

                            # Si encontramos un separador, pintamos también la línea anterior
                            if is_separator and prev_line is not None:
                                stdscr.addstr(i - 1, 0, prev_line[:curses.COLS], curses.color_pair(2))  # Magenta

                            # Pintar en verde si es un argumento (-arg, --arg)
                            if re.match(r"^\s*-\w", clean_line):
                                stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(1))  # Verde
                            # Pintar en magenta si es un separador
                            elif is_separator:
                                stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(2))  # Magenta
                            else:
                                stdscr.addstr(i, 0, clean_line[:curses.COLS])  # Normal

                            # Guardar la línea actual como la anterior para la siguiente iteración
                            prev_line = clean_line

                    except curses.error:
                        pass  # Ignorar errores si la terminal no puede mostrar el texto completo

                # Mensaje de ayuda
                try:
                    stdscr.addstr(
                        page_size, 0,
                        "[Use: Arrows (↓/↑) to scroll line by line, PgUp/PgDown or +/- to scroll by page, Space/Enter to advance a page, Q/Esc to exit]",
                        curses.A_REVERSE
                    )
                except curses.error:
                    pass  # Ignorar errores si no hay suficiente espacio para el mensaje

                stdscr.refresh()

                # Salir automáticamente si se alcanza el final
                if index >= total_lines - page_size:
                    break

                # Asignamos los códigos de las teclas +- y */ del teclado numérico
                NUMPAD_PLUS     = [584, 465]        # Codigos para NUMPAD_PLUS en LINUX, WINDOWS, MACOS
                NUMPAD_MINUS    = [268, 464]        # Codigos para NUMPAD_MINUS en LINUX, WINDOWS, MACOS
                NUMPAD_MULTIPLY = [267, 463, 42]    # Codigos para NUMPAD_MULTIPLY en LINUX, WINDOWS, MACOS
                NUMPAD_DIVIDE   = [266, 458, 47]    # Codigos para NUMPAD_DIVIDE en LINUX, WINDOWS, MACOS
                NUMPAD_ENTER    = [343, 459]        # Codigos para NUMPAD_ENTER en LINUX, WINDOWS, MACOS
                BACKSPACE       = [263, 8, 127]     # Codigos para BACKSPACE en LINUX, WINDOWS, MACOS

                # Leer entrada del usuario
                key = stdscr.getch()
                if key in [ord('q'), ord('Q'), 27]:  # Salir con 'q' o Esc
                    break
                elif key == curses.KEY_DOWN:  # Avanzar 1 línea
                    index = min(total_lines - 1, index + 1)
                elif key == curses.KEY_UP:  # Retroceder 1 línea
                    index = max(0, index - 1)
                elif key in [curses.KEY_NPAGE, ord(' '), ord('\n'), curses.KEY_ENTER, ord('+')] or key in NUMPAD_ENTER or key in NUMPAD_PLUS or key in NUMPAD_MULTIPLY:  # Avanzar 1 página
                    index = min(total_lines - page_size, index + page_size)
                elif key in [curses.KEY_PPAGE, curses.KEY_BACKSPACE, ord('-')] or key in BACKSPACE or key in NUMPAD_MINUS or key in NUMPAD_DIVIDE:  # Retroceder 1 página
                    index = max(0, index - page_size)

        curses.wrapper(pager)

        # Imprimir el texto de ayuda completo de nuevo fuera de curses para que se vea al salir
        print(text)

        # # For debugging purposses
        # print("Usage range:", usage_first_line, "-", usage_last_line)
        # print("Caution ranges:", caution_ranges)
        # print("Optional arguments line:", optional_arguments_line)


    def is_interactive(self):
        """
        Detecta si el script se está ejecutando en un entorno interactivo.
        """
        return sys.stdout.isatty()

    def get_terminal_height(self, default_height=20):
        """
        Obtiene la altura de la terminal para ajustar el número de líneas mostradas.
        Si no puede determinar el tamaño, usa un valor predeterminado.
        """
        try:
            return os.get_terminal_size().lines - 2  # Resta 2 para dejar espacio al mensaje custom
        except OSError:
            return default_height  # Si no se puede obtener, usa el valor predeterminado

    def print_help(self, file=None):
        # Genera el texto de ayuda usando el formatter_class (CustomHelpFormatter).
        help_text = self.format_help()
        if self.is_interactive():
            self.custom_pager(help_text)
        else:
            # Muestra todo el texto directamente si no es interactivo
            print(help_text)