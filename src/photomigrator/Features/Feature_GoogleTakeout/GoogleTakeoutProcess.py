import re
import subprocess

from colorama import init

from photomigrator.Core import GlobalVariables as GV


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def run_command(command, capture_output=False, capture_errors=True, print_messages=True, step_name=""):
    """
    Ejecuta un comando. Muestra en consola actualizaciones de progreso sin loguearlas.
    Loguea solo líneas distintas a las de progreso. Corrige pegado de líneas en consola.
    """
    from photomigrator.Core.CustomLogger import suppress_console_output_temporarily
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_stream(stream, is_error=False):
        init(autoreset=True)

        progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)$')
        last_was_progress = False
        printed_final = set()

        while True:
            raw = stream.readline()
            if not raw:
                break

            # Limpiar ANSI y espacios finales
            ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', raw).rstrip()

            # Prefijo para agrupar barras
            common_part = line.split(' : ')[0] if ' : ' in line else line

            # 1) ¿Es barra de progreso?
            m = progress_re.search(line)
            if m:
                n, total = int(m.group(1)), int(m.group(2))

                # 1.a) Barra vacía (0/x)
                if n == 0:
                    if not print_messages:
                        # Log inicial
                        log_msg = f"{step_name}{line}"
                        if is_error:
                            GV.LOGGER.error(log_msg)
                        else:
                            GV.LOGGER.info(log_msg)
                    # nunca imprimo 0/x en pantalla
                    last_was_progress = True
                    continue

                # 1.b) Progreso intermedio (1 <= n < total)
                if n < total:
                    if print_messages:
                        print(f"\r{GV.TAG_INFO}{step_name}{line}", end='', flush=True)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    # impresión en pantalla
                    if print_messages:
                        print(f"\r{GV.TAG_INFO}{step_name}{line}", end='', flush=True)
                        print()
                    # log final
                    log_msg = f"{step_name}{line}"
                    if is_error:
                        GV.LOGGER.error(log_msg)
                    else:
                        GV.LOGGER.info(log_msg)

                    printed_final.add(common_part)

                last_was_progress = False
                continue

            # 2) Mensaje normal: si venía de progreso vivo, forzamos salto
            if last_was_progress and print_messages:
                print()
            last_was_progress = False

            # 3) Impresión normal
            if print_messages:
                if is_error:
                    print(f"{GV.COLORTAG_ERROR}{step_name}{line}")
                else:
                    if "ERROR" in line:
                        print(f"{GV.COLORTAG_ERROR}{step_name}{line}")
                    elif "WARNING" in line:
                        print(f"{GV.COLORTAG_WARNING}{step_name}{line}")
                    elif "DEBUG" in line:
                        print(f"{GV.COLORTAG_DEBUG}{step_name}{line}")
                    elif "VERBOSE" in line:
                        print(f"{GV.COLORTAG_VERBOSE}{step_name}{line}")
                    else:
                        print(f"{GV.COLORTAG_INFO}{step_name}{line}")

            # 4) Logging normal
            if is_error:
                GV.LOGGER.error(f"{step_name}{line}")
            else:
                if "ERROR" in line:
                    GV.LOGGER.error(f"{step_name}{line}")
                elif "WARNING" in line:
                    GV.LOGGER.warning(f"{step_name}{line}")
                elif "DEBUG" in line:
                    GV.LOGGER.debug(f"{step_name}{line}")
                elif "VERBOSE" in line:
                    GV.LOGGER.verbose(f"{step_name}{line}")
                else:
                    GV.LOGGER.info(f"{step_name}{line}")

        # 5) Al cerrar stream, si quedó un progreso vivo, cerramos línea
        if last_was_progress and print_messages:
            print()

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    with suppress_console_output_temporarily(GV.LOGGER):
        if not capture_output and not capture_errors:
            return subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace").returncode
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True, encoding = "utf-8", errors = "replace"
            )
            if capture_output:
                handle_stream(process.stdout, is_error=False)
            if capture_errors:
                handle_stream(process.stderr, is_error=True)

            process.wait()  # Esperar a que el proceso termine
            return process.returncode
