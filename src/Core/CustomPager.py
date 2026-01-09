import argparse
import os
import platform
import re
import sys

from Core.GlobalVariables import TOOL_NAME_VERSION, LOGGER

if platform.system() == "Windows":
    try:
        import curses
    except ImportError:
        raise ImportError("Install 'windows-curses' for Windows support: pip install windows-curses")
else:
    import curses


class PagedParser(argparse.ArgumentParser):
    """
    We override ArgumentParser so that print_help() uses a pager.
    """

    def custom_pager(self, text):
        """
        Curses-based pager that dynamically adapts the text to the terminal size.
        """

        # Regular expression to detect ANSI escape codes
        ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

        usage_first_line = -1
        usage_last_line = -1
        caution_ranges = []  # List to store line ranges for each “CAUTION:” block
        optional_arguments_line = -1  # Line index that contains "optional arguments:"

        lines = text.splitlines()

        # Determine start/end indices for the "usage" section
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)  # Remove ANSI sequences (colorama)
            if 'usage' in clean_line.lower() and usage_first_line == -1:  # Detect the first line with usage
                usage_first_line = i
            if TOOL_NAME_VERSION in clean_line:  # Detect the last usage line (but do NOT paint TOOL_NAME_VERSION in green)
                usage_last_line = i - 1  # Stop one line before TOOL_NAME_VERSION
                break  # No need to keep searching

        # Determine all "CAUTION:" blocks
        caution_start = -1
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)
            if 'CAUTION:' in clean_line:  # Detect any occurrence of “CAUTION:”
                if caution_start == -1:  # If we have not started a block, mark the start
                    caution_start = i
            elif caution_start != -1 and (re.match(r"^\s*-\w", clean_line) or clean_line.strip() == ""):
                caution_ranges.append((caution_start, i - 1))  # Save the block range until the previous line
                caution_start = -1  # Reset to detect further blocks

        # Find the line that contains "optional arguments:"
        for i, line in enumerate(lines):
            clean_line = ANSI_ESCAPE.sub('', line)
            if 'optional arguments:' in clean_line.lower():
                optional_arguments_line = i
                break  # Only need the first occurrence

        # Check if terminal supports colors
        def check_color_support():
            curses.start_color()
            if not curses.has_colors():
                LOGGER.warning("Your terminal does not support colors")
                return False

            max_pairs = curses.COLOR_PAIRS
            if max_pairs < 4:
                LOGGER.warning(f"Your terminal only supports {max_pairs} color pairs. The tool needs 4.")
                return False

            return True

        def pager(stdscr):
            # Check if terminal supports colors
            color_support = check_color_support()
            if color_support:
                curses.start_color()
                curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Green (args and usage)
                curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Yellow (separators and previous lines)
                curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Red (CAUTION blocks)
                curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Yellow (optional arguments)
            curses.curs_set(0)  # Hide cursor

            total_lines = len(lines)
            page_size = curses.LINES - 2  # Terminal height minus space for the help message
            index = 0

            while True:
                stdscr.clear()
                prev_line = None  # Store the previous line (used to color the line above separators)

                for i, line in enumerate(lines[index:index + page_size]):
                    try:
                        clean_line = ANSI_ESCAPE.sub('', line)  # Remove ANSI sequences (colorama)
                        line_number = index + i  # Absolute line number in the full help text

                        if color_support:
                            # Paint all lines in the usage block in green (except the TOOL_NAME_VERSION line)
                            if usage_first_line <= line_number <= usage_last_line:
                                stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(1))
                            # Paint all lines within any “CAUTION:” block in red
                            elif any(start <= line_number <= end for start, end in caution_ranges):
                                stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(3))
                            # Paint the “optional arguments:” line in yellow
                            elif line_number == optional_arguments_line:
                                stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(4))
                            else:
                                # Detect whether the current line is a separator (--- or more dashes)
                                is_separator = re.match(r"^\s*-{3,}", clean_line)

                                # If we find a separator, also paint the previous line
                                if is_separator and prev_line is not None:
                                    stdscr.addstr(i - 1, 0, prev_line[:curses.COLS], curses.color_pair(2))

                                # Paint in green if it looks like an argument (-arg, --arg)
                                # if re.match(r"^\s*-\w", clean_line):
                                if re.match(r"^\s*--?\w", clean_line):
                                    stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(1))
                                # Paint in yellow if it is a separator
                                elif is_separator:
                                    stdscr.addstr(i, 0, clean_line[:curses.COLS], curses.color_pair(2))
                                else:
                                    stdscr.addstr(i, 0, clean_line[:curses.COLS])

                                # Save current line as previous line for the next iteration
                                prev_line = clean_line

                        # If terminal does not support colors
                        else:
                            stdscr.addstr(i, 0, clean_line[:curses.COLS])

                    except curses.error:
                        # Ignore errors when the terminal cannot display the full text
                        pass

                # Help message (footer)
                try:
                    stdscr.addstr(
                        page_size,
                        0,
                        "[Use: Arrows (↓/↑) to scroll line by line, PgUp/PgDown or +/- to scroll by page, Space/Enter to advance a page, Q/Esc to exit]",
                        curses.A_REVERSE
                    )
                except curses.error:
                    pass  # Not enough space for the footer

                stdscr.refresh()

                # Auto-exit if end is reached
                if index >= total_lines - page_size:
                    break

                # Assign key codes for numeric keypad operations
                NUMPAD_PLUS     = [584, 465]        # Codes for NUMPAD_PLUS on LINUX, WINDOWS, MACOS
                NUMPAD_MINUS    = [268, 464]        # Codes for NUMPAD_MINUS on LINUX, WINDOWS, MACOS
                NUMPAD_MULTIPLY = [267, 463, 42]    # Codes for NUMPAD_MULTIPLY on LINUX, WINDOWS, MACOS
                NUMPAD_DIVIDE   = [266, 458, 47]    # Codes for NUMPAD_DIVIDE on LINUX, WINDOWS, MACOS
                NUMPAD_ENTER    = [343, 459]        # Codes for NUMPAD_ENTER on LINUX, WINDOWS, MACOS
                BACKSPACE       = [263, 8, 127]     # Codes for BACKSPACE on LINUX, WINDOWS, MACOS

                # Read user input
                key = stdscr.getch()

                # Exit with 'q' or Esc
                if key in [ord('q'), ord('Q'), 27]:
                    break

                # Move 1 line down
                elif key == curses.KEY_DOWN:
                    index = min(total_lines - 1, index + 1)

                # Move 1 line up
                elif key == curses.KEY_UP:
                    index = max(0, index - 1)

                # Advance 1 page
                elif key in [curses.KEY_NPAGE, ord(' '), ord('\n'), curses.KEY_ENTER, ord('+')] or \
                        key in NUMPAD_ENTER or key in NUMPAD_PLUS or key in NUMPAD_MULTIPLY:
                    index = min(total_lines - page_size, index + page_size)

                # Go back 1 page
                elif key in [curses.KEY_PPAGE, curses.KEY_BACKSPACE, ord('-')] or \
                        key in BACKSPACE or key in NUMPAD_MINUS or key in NUMPAD_DIVIDE:
                    index = max(0, index - page_size)

        curses.wrapper(pager)

        # Print the full help text again outside curses so it remains visible after exiting
        print(text)

        # # For debugging purposes
        # print("Usage range:", usage_first_line, "-", usage_last_line)
        # print("Caution ranges:", caution_ranges)
        # print("Optional arguments line:", optional_arguments_line)

    def get_terminal_height(self, default_height=20):
        """
        Get the terminal height to adjust how many lines are displayed.
        If the size cannot be detected, use a default value.
        """
        try:
            return os.get_terminal_size().lines - 2  # Subtract 2 to leave space for the custom footer
        except OSError:
            return default_height  # If size cannot be obtained, use default

    def is_interactive(self):
        """
        Detect whether the script is running in a valid interactive terminal.
        On Windows it does not depend on TERM, on Unix it does.
        """
        if platform.system() == 'Windows':
            return sys.stdout.isatty()
        else:
            return sys.stdout.isatty() and os.environ.get('TERM') is not None

    def print_help(self, file=None):
        # Generate help text using formatter_class (CustomHelpFormatter).
        help_text = self.format_help()
        try:
            if self.is_interactive():
                self.custom_pager(help_text)
            else:
                # Print directly when not interactive
                print(help_text)
        except Exception:
            print(help_text)
            print("Pagination is not possible on this terminal.")
