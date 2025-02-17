from GlobalVariables import SCRIPT_NAME_VERSION
import argparse
import os, sys
import platform
import re

if platform.system() == "Windows":
    try:
        import curses
    except ImportError:
        raise ImportError("Instala 'windows-curses' para soporte en Windows: pip install windows-curses")
else:
    import curses

class PagedParser(argparse.ArgumentParser):
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

    def get_terminal_height(self, default_height=20):
        """
        Obtiene la altura de la terminal para ajustar el número de líneas mostradas.
        Si no puede determinar el tamaño, usa un valor predeterminado.
        """
        try:
            return os.get_terminal_size().lines - 2  # Resta 2 para dejar espacio al mensaje custom
        except OSError:
            return default_height  # Si no se puede obtener, usa el valor predeterminado
    
    def is_interactive(self):
        """
        Detecta si el script se está ejecutando en un entorno interactivo.
        """
        return sys.stdout.isatty()

    def print_help(self, file=None):
        # Genera el texto de ayuda usando el formatter_class (CustomHelpFormatter).
        help_text = self.format_help()
        if self.is_interactive():
            self.custom_pager(help_text)
        else:
            # Muestra el texto directamente si no es interactivo
            print(help_text)