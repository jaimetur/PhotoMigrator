# -*- coding: utf-8 -*-
import logging
import shutil
from pathlib import Path

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import ARGS, LOGGER, TIMESTAMP
from Features.GoogleTakeout.ClassTakeoutFolder import organize_files_by_date
from Utils.FileUtils import DEFAULT_FOLDER_EXCLUSION_PATTERNS, merge_exclusion_patterns, remove_empty_dirs


def _build_output_folder(input_folder: Path, output_folder: str = "", output_folder_suffix: str = "processed") -> Path:
    if str(output_folder or "").strip():
        return Path(output_folder).expanduser().resolve()
    suffix = str(output_folder_suffix or "processed").strip().lstrip("_") or "processed"
    return Path(f"{input_folder}_{suffix}_{TIMESTAMP}").resolve()


def _validate_output_folder(input_folder: Path, output_folder: Path) -> None:
    input_resolved = input_folder.resolve()
    output_resolved = output_folder.resolve(strict=False)

    if input_resolved == output_resolved:
        raise ValueError("Input and output folder must be different.")
    if output_resolved.exists():
        raise FileExistsError(f"Output folder already exists: '{output_resolved}'")
    if input_resolved in output_resolved.parents:
        raise ValueError("Output folder cannot be created inside the input folder.")
    if output_resolved in input_resolved.parents:
        raise ValueError("Output folder cannot be a parent of the input folder.")


def organize_local_folder_by_date(
    input_folder: str,
    output_folder: str = "",
    folder_structure: str = "year/month",
    output_folder_suffix: str = "processed",
    move_original_files: bool = False,
    step_name: str = "",
    log_level=None,
):
    with set_log_level(LOGGER, log_level):
        source_folder = Path(input_folder).expanduser().resolve()
        if not source_folder.exists() or not source_folder.is_dir():
            raise FileNotFoundError(f"Input folder does not exist: '{source_folder}'")

        destination_folder = _build_output_folder(
            input_folder=source_folder,
            output_folder=output_folder,
            output_folder_suffix=output_folder_suffix,
        )
        _validate_output_folder(source_folder, destination_folder)

        action = "Moving" if move_original_files else "Copying"
        LOGGER.info(f"{step_name}Input folder                : '{source_folder}'")
        LOGGER.info(f"{step_name}Output folder               : '{destination_folder}'")
        LOGGER.info(f"{step_name}Folder structure            : '{folder_structure}'")
        LOGGER.info(f"{step_name}Move original files         : '{move_original_files}'")
        LOGGER.info(f"{step_name}{action} source folder into output...")

        destination_folder.parent.mkdir(parents=True, exist_ok=True)
        if move_original_files:
            shutil.move(str(source_folder), str(destination_folder))
        else:
            shutil.copytree(str(source_folder), str(destination_folder))

        exclude_subfolders = merge_exclusion_patterns(
            ARGS.get("exclude-folders", []) if isinstance(ARGS, dict) else [],
            default_patterns=DEFAULT_FOLDER_EXCLUSION_PATTERNS,
        )
        replacements = []
        if folder_structure != "flatten":
            replacements = organize_files_by_date(
                input_folder=str(destination_folder),
                type=folder_structure,
                exclude_subfolders=exclude_subfolders,
                folder_analyzer=None,
                step_name=f"{step_name}[Organize By Date] : " if step_name else "",
                log_level=log_level,
            )

        remove_empty_dirs(str(destination_folder), log_level=log_level)
        LOGGER.info(f"{step_name}Assets reorganized           : {len(replacements)}")
        return {
            "input_folder": str(source_folder),
            "output_folder": str(destination_folder),
            "folder_structure": folder_structure,
            "move_original_files": bool(move_original_files),
            "assets_reorganized": len(replacements),
        }
