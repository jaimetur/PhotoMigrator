import curses

def debug_keypress(stdscr):
    curses.curs_set(0)
    stdscr.addstr(0, 0, "Pulsa teclas (teclado numerico, etc.). 'q' o ESC para salir.\n")
    row = 2

    while True:
        key = stdscr.getch()
        # Limpia la línea de diagnóstico cada vez
        stdscr.move(row, 0)
        stdscr.clrtoeol()
        stdscr.addstr(row, 0, f"Tecla pulsada: {key} (hex: {hex(key)})")
        stdscr.refresh()

        if key in [ord('q'), 27]:  # 'q' o ESC -> salir
            break
        row += 1
        if row >= curses.LINES:
            # Si llegamos al fondo, reiniciamos en la línea 2
            row = 2

curses.wrapper(debug_keypress)
