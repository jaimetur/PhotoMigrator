import textwrap
import argparse
import re
import os, sys
import platform

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
        kwargs['width'] = 80  # Ancho total del texto de ayuda
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
            "[-sg]": False                # Salto de línea antes, pero sigue reagrupando
            ,"[-sde]": False                # Salto de línea antes, pero sigue reagrupando
            ,"[-ide]": False                # Salto de línea antes, pero sigue reagrupando
            ,"[-fs <FOLDER_TO_FIX>]": True  # # Va solo
            ,"[-fd <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]]": True  # Va solo
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
        return usage

    def _format_action(self, action):
        def procesar_saltos_de_linea(text, initial_indent="", subsequent_indent=""):
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
            ident_spaces = 8
            help_text = procesar_saltos_de_linea(action.help, initial_indent=" " * ident_spaces, subsequent_indent=" " * ident_spaces)
            # help_text = textwrap.fill(action.help, width=self._width, initial_indent=" " * ident_spaces, subsequent_indent=" " * ident_spaces)
            parts.append(f"\n{help_text}")  # Salto de línea adicional
            # Add EXTRA MODES: after "Skip saving output messages to execution log file."
            if help_text.find('Skip saving output messages to execution log file.')!=-1:
                parts.append(f"\n\n\nEXTRA MODES:\n------------\n")
                extra_description = f"Following optional arguments can be used to execute the Script in any of the usefull additionals Extra Modes included. When an Extra Mode is detected only this module will be executed (ignoring the normal steps). If more than one Extra Mode is detected, only the first one will be executed.\n"
                extra_description = procesar_saltos_de_linea(extra_description)
                # extra_description = textwrap.fill(extra_description, width=self._width, initial_indent="", subsequent_indent="")
                parts.append(extra_description+'\n')
            # Add EXTRA MODES for Google Photos Takeout Management: after "The Script will do the whole process".
            if help_text.find("The Script will do the whole process")!=-1:
                parts.append(f"\n\n\nEXTRA MODES: Google Photos Takeout Management:\n----------------------------------------\n")
                extra_description = f"Following Extra Modes allow you to interact with Google Photos Takeout Folder. \nIf more than one Extra Mode is detected, only the first one will be executed.\n"
                extra_description = procesar_saltos_de_linea(extra_description)
                # extra_description = textwrap.fill(extra_description, width=self._width, initial_indent="", subsequent_indent="")
                parts.append(extra_description+'\n')
            # Add EXTRA MODES for Synology Photos Management: after "The Script will do the whole process".
            if help_text.find("Remove Duplicates files in <OUTPUT_FOLDER> after fixing them")!=-1:
                parts.append(f"\n\n\nEXTRA MODES: Synology Photos Management:\n----------------------------------------\n")
                extra_description = f"Following Extra Modes allow you to interact with Synology Photos. \nIf more than one Extra Mode is detected, only the first one will be executed.\n"
                extra_description = procesar_saltos_de_linea(extra_description)
                # extra_description = textwrap.fill(extra_description, width=self._width, initial_indent="", subsequent_indent="")
                parts.append(extra_description+'\n')
            # Add EXTRA MODES for Immich Photos Management: after "any Album is duplicated, will remove it from Synology Photos database.".
            if help_text.find("The Script will connect to Synology Photos and will download all the")!=-1:
                parts.append(f"\n\n\nEXTRA MODES: Immich Photos Management:\n--------------------------------------\n")
                extra_description = f"Following Extra Modes allow you to interact with Immich Photos. \nIf more than one Extra Mode is detected, only the first one will be executed.\n"
                extra_description = procesar_saltos_de_linea(extra_description)
                # extra_description = textwrap.fill(extra_description, width=self._width, initial_indent="", subsequent_indent="")
                parts.append(extra_description+'\n')

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
                    if len(opt) == 4:
                        option_strings.append(f"{opt},")
                    elif len(opt) == 3:
                        option_strings.append(f"{opt}, ")
                    elif len(opt) == 2:
                        option_strings.append(f"{opt},  ")
                else:
                    option_strings.append(f"{opt}")

            # Combina los argumentos cortos y largos, y agrega el parámetro si aplica
            formatted_options = " ".join(option_strings).rstrip(",")
            metavar = f" {action.metavar}" if action.metavar else ""
            return f"{formatted_options}{metavar}"
    def _join_parts(self, part_strings):
        # Asegura que cada argumento quede separado por un salto de línea
        return "\n".join(part for part in part_strings if part)

class PagedArgumentParser(argparse.ArgumentParser):
    """
    Sobrescribimos ArgumentParser para que 'print_help()' use un paginador.
    """
    def custom_pager(self, text):
        """
        Paginador con curses que adapta dinámicamente el texto al tamaño de la terminal.
        """
        def pager(stdscr):
            curses.curs_set(0)  # Ocultar el cursor
            lines = text.splitlines()
            total_lines = len(lines)
            page_size = curses.LINES - 2  # Altura de la terminal menos espacio para el mensaje
            index = 0

            while True:
                # Asegurarse de que el número de líneas no exceda los límites
                stdscr.clear()
                for i, line in enumerate(lines[index:index + page_size]):
                    try:
                        stdscr.addstr(i, 0, line[:curses.COLS])  # Ajustar texto al ancho de la terminal
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
                elif key == curses.KEY_NPAGE or key in [ord(' '), ord('\n'), curses.KEY_ENTER, ord('+')] or key in NUMPAD_ENTER or key in NUMPAD_PLUS or key in NUMPAD_MULTIPLY:  # Avanzar 1 página
                    index = min(total_lines - page_size, index + page_size)
                elif key == curses.KEY_PPAGE or key in [curses.KEY_BACKSPACE, 8, ord('-')] or key in BACKSPACE or key in NUMPAD_MINUS or key in NUMPAD_DIVIDE:  # Retroceder 1 página
                    index = max(0, index - page_size)

        curses.wrapper(pager)

        # Imprimir el texto de ayuda completo de nuevo fuera de curses para que se vea al salir
        print(text)

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