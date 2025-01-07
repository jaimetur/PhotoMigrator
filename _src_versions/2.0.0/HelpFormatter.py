import argparse
import textwrap

class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        # Configura la anchura máxima del texto de ayuda
        kwargs['width'] = 90  # Ancho total del texto de ayuda
        kwargs['max_help_position'] = 55  # Ajusta la posición de inicio de las descripciones
        super().__init__(*args, **kwargs)
    def _format_action(self, action):
        # Encabezado del argumento
        parts = [self._format_action_invocation(action)]
        # Texto de ayuda, formateado e identado
        if action.help:
            help_text = textwrap.fill(
                action.help,
                width=self._width,
                initial_indent="        ",
                subsequent_indent="        "
            )
            parts.append(f"\n{help_text}")  # Salto de línea adicional
            
            # Add EXTRA MODES: after -nl, --no-log-file argument
            if help_text.lower().find('skip saving output messages to execution log file')!=-1:
                 parts.append(f"\n\n\nEXTRA MODES:\n------------\n")
                 extra_description = f"Following optional arguments can be used to execute the Script in any of the usefull additionals Extra Modes included. When an Extra Mode is detected only this module will be executed (ignoring the normal steps). If more than one Extra Mode is detected, only the first one will be executed.\n"
                 extra_description = textwrap.fill(
                extra_description,
                width=self._width,
                initial_indent="",
                subsequent_indent=""
            )
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
        