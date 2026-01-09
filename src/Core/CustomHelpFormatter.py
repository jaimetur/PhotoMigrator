import argparse
import re
import textwrap

from colorama import Fore, Style

from Core.GlobalVariables import MAX_HELP_POSITION, MAX_SHORT_ARGUMENT_LENGTH, IDENT_ARGUMENT_DESCRIPTION, IDENT_USAGE_DESCRIPTION, SHORT_LONG_ARGUMENTS_SEPARATOR


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        # Configure the maximum width of the help text output
        kwargs['width'] = MAX_HELP_POSITION  # Total help text width
        kwargs['max_help_position'] = MAX_HELP_POSITION  # Start position of descriptions
        super().__init__(*args, **kwargs)

    def _tokenize_usage(self, usage_text):
        """
        Tokenize the usage string, keeping bracket blocks together (supports nested brackets).

        We:
          1) Replace newlines with spaces so the usage becomes a single logical line.
          2) Parse tokens, treating any "[ ... ]" (including nested brackets) as a single token.
          3) Return a structure compatible with argparse formatter: [ (indent, tokens) ].
        """
        # 1) Replace line breaks with spaces (avoid splitting into multiple lines here)
        flattened = usage_text.replace('\n', ' ')

        def parse_brackets(s):
            tokens = []
            i = 0
            n = len(s)

            while i < n:
                # Skip leading spaces
                if s[i].isspace():
                    i += 1
                    continue

                # If '[' is found, parse the full (possibly nested) bracket block
                if s[i] == '[':
                    start = i
                    bracket_count = 1  # Found one '['
                    i += 1

                    # Move forward until all bracket levels are closed
                    while i < n and bracket_count > 0:
                        if s[i] == '[':
                            bracket_count += 1
                        elif s[i] == ']':
                            bracket_count -= 1
                        i += 1

                    # i is now just after the matching closing bracket
                    tokens.append(s[start:i])  # Include the whole block with brackets
                else:
                    # Normal token (does not start with '[')
                    start = i
                    # Advance until we reach a space or a '['
                    while i < n and not s[i].isspace() and s[i] != '[':
                        i += 1
                    tokens.append(s[start:i])

            return tokens

        tokens = parse_brackets(flattened)

        # Return as a single “line” with empty original indent
        return [('', tokens)]

    def _build_lines_with_forced_tokens(
            self,
            tokenized_usage,
            forced_tokens,
            width,
            first_line_indent='',
            subsequent_indent=' ' * IDENT_USAGE_DESCRIPTION,
    ):
        """
        Rebuild usage text into lines, forcing a line break before certain tokens.

        forced_tokens is a dict:
            { "<token_prefix>": <must_be_alone_bool> }

        If a token starts with <token_prefix>:
          - Always break the line before it (unless it's the first token on the line).
          - If must_be_alone_bool is True, the token is placed alone on its own line.
        """
        final_lines = []

        for (orig_indent, tokens) in tokenized_usage:
            if not tokens:
                final_lines.append(orig_indent)
                continue

            current_line = first_line_indent
            current_len = len(first_line_indent)
            first_token = True
            line_number = 0

            for token in tokens:
                match_forced = next(
                    (forced_token for forced_token in forced_tokens if token.startswith(forced_token)),
                    None
                )

                if match_forced is not None:
                    must_be_alone = forced_tokens[match_forced]

                    # Force a line break before the token (if we are not at the beginning)
                    if not first_token:
                        final_lines.append(current_line)
                        current_line = subsequent_indent
                        current_len = len(subsequent_indent)
                        first_token = True
                        line_number += 1

                    if must_be_alone:
                        # Token must be alone on its own line
                        forced_line = (subsequent_indent if line_number > 0 else first_line_indent) + token
                        final_lines.append(forced_line)
                        current_line = subsequent_indent
                        current_len = len(subsequent_indent)
                        first_token = True
                        line_number += 1
                        continue

                # Normal logic for adding tokens
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
                        current_len = len(subsequent_indent) + len(token)
                        first_token = False
                    else:
                        current_line += ' ' + token
                        current_len = needed_len

            # Append remaining line
            if current_line.strip():
                final_lines.append(current_line)
                line_number += 1

        return '\n'.join(final_lines)

    def _format_usage(self, usage, actions, groups, prefix, **kwargs):
        """
        Override default argparse usage formatting:
          - Removes certain verbose blocks.
          - Fixes spacing.
          - Tokenizes usage with bracket-aware tokenizer.
          - Rebuilds usage with forced line breaks for specific tokens.
          - Colors usage output in green.
        """

        def remove_chain(usage_text, chain_to_remove):
            # 1) Join all lines into one (replace newlines with spaces)
            usage_single_line = usage_text.replace('\n', ' ')
            # 2) Replace 2+ consecutive spaces by a single space
            usage_single_line = re.sub(r' {2,}', ' ', usage_single_line)
            # 3) Remove the given chain
            usage_single_line = usage_single_line.replace(chain_to_remove, '')
            return usage_single_line

        # 1) Base usage from parent class
        usage = super()._format_usage(usage, actions, groups, prefix)

        # 2) Remove block with <ACTION> <DUPLICATES_FOLDER> ... (custom)
        usage = remove_chain(usage, "[<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...] ...]")

        # 3) Remove spaces before "...]" and before the last bracket
        usage = usage.replace(" ...] ]", "...]]")

        # 4) Remove block with <ALBUMS_NAME_PATTERN> ...
        usage = remove_chain(usage, "[<ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN> ...]")

        # 5) Remove stray spaces before closing brackets
        usage = usage.replace(" ]", "]")

        # 6) Tokenize with custom nested-bracket logic
        tokenized = self._tokenize_usage(usage)

        # 7) Forced tokens dictionary (break line before these tokens)
        force_new_line_for_tokens = {
            "[-from <FROM_DATE>]": False,  # Break before token, but still allow grouping
            "[-country <COUNTRY_NAME>]": False,  # Break before token, but still allow grouping
            "[-gpthInfo [= [true,false]]]": False,  # Break before token, but still allow grouping
            "[-i <INPUT_FOLDER>]": False,  # Break before token, but still allow grouping
            "[-source <SOURCE>]": False,  # Break before token, but still allow grouping
            "[-move [= [true,false]": False,  # Break before token, but still allow grouping (note: prefix without final brackets)
            "[-gTakeout <TAKEOUT_FOLDER>]": False,  # Break before token, but still allow grouping
            "[-uAlb <ALBUMS_FOLDER>]": False,  # Break before token, but still allow grouping
            "[-uAll <INPUT_FOLDER>]": False,  # Break before token, but still allow grouping
            "[-fixSym <FOLDER_TO_FIX>]": False,  # Break before token, but still allow grouping
            # Examples:
            # "[-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]": True,  # Must be alone
        }

        # 8) Use the real width set by argparse
        max_width = getattr(self, '_width', 90)

        # 9) Rebuild usage with indent rules
        ident_spaces = IDENT_USAGE_DESCRIPTION
        usage = self._build_lines_with_forced_tokens(
            tokenized_usage=tokenized,
            forced_tokens=force_new_line_for_tokens,
            width=max_width,
            first_line_indent='',
            subsequent_indent=' ' * ident_spaces
        )

        # 10) Colorize usage
        usage = f'{Fore.GREEN}{usage}{Style.RESET_ALL}'
        return usage

    def _format_action(self, action):
        """
        Override how each argument/action is rendered in help:
          - Wrap help text with custom indentation.
          - Insert section headers based on detecting specific sentences.
          - Highlight "CAUTION:" in red.
        """

        def wrap_text(text, initial_indent="", subsequent_indent=""):
            # 1) Split into lines
            lines = text.splitlines()
            # 2) Apply textwrap.fill() line-by-line (preserve manual line breaks)
            wrapped_lines = [
                textwrap.fill(
                    line,
                    width=self._width,
                    initial_indent=initial_indent,
                    subsequent_indent=subsequent_indent
                )
                for line in lines
            ]
            # 3) Rejoin with newlines
            return "\n".join(wrapped_lines)

        # Argument header (invocation)
        parts = [self._format_action_invocation(action)]

        # Help text block
        if action.help:
            help_text = wrap_text(
                action.help,
                initial_indent=" " * IDENT_ARGUMENT_DESCRIPTION,
                subsequent_indent=" " * IDENT_ARGUMENT_DESCRIPTION
            )

            # Insert section header: AUTOMATIC MIGRATION PROCESS
            if help_text.find("Select the <SOURCE> for the AUTOMATIC-MIGRATION Process") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                AUTOMATIC MIGRATION PROCESS:
                ----------------------------{Style.RESET_ALL}
                Following arguments allow you execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service. 

                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: GENERAL ARGUMENTS
            if help_text.find("Specify the input folder that you want to process.") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                GENERAL ARGUMENTS:
                ------------------{Style.RESET_ALL}
                Following general arguments have different purposses depending on the Execution Mode. 
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: GOOGLE PHOTOS TAKEOUT MANAGEMENT
            if help_text.find("Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                GOOGLE PHOTOS TAKEOUT MANAGEMENT:
                ---------------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Google Photos Takeout Folder. 
                In this mode, you can use more than one optional arguments from the below list.
                If only the argument -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the Tool will use the default values for the rest of the arguments for this extra mode.
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: SYNOLOGY PHOTOS MANAGEMENT (legacy/detection string)
            if help_text.find("and will create one Album per subfolder into Synology Photos.") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                SYNOLOGY PHOTOS MANAGEMENT:
                ---------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Synology Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: IMMICH PHOTOS MANAGEMENT (legacy/detection string)
            if help_text.find("and will create one Album per subfolder into Immich Photos.") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                IMMICH PHOTOS MANAGEMENT:
                -------------------------{Style.RESET_ALL}
                Following arguments allow you to interact with Immich Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: SYNOLOGY/IMMICH PHOTOS MANAGEMENT
            if help_text.find("The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER>") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                SYNOLOGY/IMMICH PHOTOS MANAGEMENT:
                ----------------------------------{Style.RESET_ALL}
                To use following features, it is mandatory to use the argument '--client=[synology, immich]' to specify which Photo Service do you want to use.   

                You can optionally use the argument '--id=[1-3]' to specify the account id for a particular account defined in Config.ini.                  

                Following arguments allow you to interact with Synology/Immich Photos. 
                If more than one optional arguments are detected, only the first one will be executed.
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Insert section header: OTHER STANDALONE FEATURES
            if help_text.find("The Tool will try to fix all symbolic links for Albums") != -1:
                text_to_insert = textwrap.dedent(f"""
                {Fore.YELLOW}
                OTHER STANDALONE FEATURES:
                --------------------------{Style.RESET_ALL}
                Following arguments can be used to execute the Tool in any of the useful Extra Standalone Features included. 
                If more than one Feature is detected, only the first one will be executed.
                """)
                text_to_insert = wrap_text(text_to_insert) + '\n\n'
                parts.insert(-1, f"{text_to_insert}")

            # Highlight "CAUTION:" part in red if present
            if help_text.find("CAUTION: ") != -1:
                start_index_for_color = help_text.find("CAUTION: ")
                end_index_for_color = len(help_text)
                colored = (
                    f"\n{help_text[0:start_index_for_color]}"
                    f"{Fore.RED}{help_text[start_index_for_color:end_index_for_color]}"
                    f"{Style.RESET_ALL}{help_text[end_index_for_color:]}"
                )
                parts.append(f"{colored}")
            else:
                parts.append(f"\n{help_text}")  # Extra newline before help text

        return "".join(parts)

    def _format_action_invocation(self, action):
        """
        Customize how option strings are displayed:
          - Align short option to a fixed width and add a separator
          - Keep long options as-is
          - Color the whole invocation in green
        """
        if not action.option_strings:
            # Positional args
            return super()._format_action_invocation(action)

        # Combine short and long options with extra spacing if needed
        option_strings = []
        for opt in action.option_strings:
            # Short option: pad to MAX_SHORT_ARGUMENT_LENGTH and append separator
            if opt.startswith("-") and not opt.startswith("--"):
                option_strings.append(f"{opt.ljust(MAX_SHORT_ARGUMENT_LENGTH)}{SHORT_LONG_ARGUMENTS_SEPARATOR}")
            else:
                option_strings.append(f"{opt}")

        # Join options and append metavar if present
        formatted_options = " ".join(option_strings).rstrip(",")
        metavar = f" {action.metavar}" if action.metavar else ""
        return f"{Fore.GREEN}{formatted_options}{metavar}{Style.RESET_ALL}"

    def _join_parts(self, part_strings):
        # Ensure each argument/help block is separated by a newline
        return "\n".join(part for part in part_strings if part)
