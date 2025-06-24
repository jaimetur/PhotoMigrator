import os
import posixpath

from Core.GlobalVariables import MSG_TAGS


def change_working_dir(change_dir=None):
    if change_dir:
        """ Definir la ruta de trabajo deseada """
        WORKING_DIR = r"R:\jaimetur\PhotoMigrator"
        # Verificar si la carpeta existe y cambiar a ella si existe
        if os.path.exists(WORKING_DIR) and os.path.isdir(WORKING_DIR):
            os.chdir(WORKING_DIR)
            current_directory = os.getcwd()
            print(f"{MSG_TAGS['INFO']}Directorio cambiado a: {os.getcwd()}")


def is_inside_docker():
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"


def resolve_path(user_path):
    """
    Converts a user_path into a valid absolute path.

    Inside Docker:
      - If the path has a Windows drive letter (e.g. C:), raise an error.
      - If it's an absolute path and doesn't start with /docker, raise an error.
      - If it's absolute and starts with /docker, accept it as is.
      - If it's relative, join it under /docker, then normalize. If the result
        escapes /docker (e.g. /docker/../somefolder => /somefolder), raise an error.
    Outside Docker:
      - Return the absolute path normally.
    """

    # 1) Skip non-string or empty inputs
    if not isinstance(user_path, str) or user_path.strip() == "":
        return user_path

    # 2) Clean up the string and unify slashes
    path_clean = user_path.strip().replace("\\", "/")

    # 3) Normalize (handles ".", "..", etc.)
    path_clean = posixpath.normpath(path_clean)

    # 4) Split any Windows drive letter (e.g. "C:/stuff" => drive="C:", tail="/stuff")
    drive, tail = os.path.splitdrive(path_clean)

    if is_inside_docker():
        # (a) If there's a Windows drive letter, raise an error
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            raise ValueError(
                f"Cannot use paths with a Windows drive letter '{drive}' inside Docker."
                f"\nWrong Path detected: {user_path}"
                f"\nPlease provide a path under /docker or under the execution folder."
            )

        # (b) Check if path is absolute in a Unix sense
        if path_clean.startswith("/"):
            # Must start with "/docker" or raise an error
            if not path_clean.startswith("/docker"):
                raise ValueError(
                    f"Absolute path '{path_clean}' is outside the '/docker' folder."
                    f"\nPlease provide a path under /docker or under the execution folder."
                )
            # Normalize again and ensure it still stays under /docker
            final_path = posixpath.normpath(path_clean)
            if not final_path.startswith("/docker"):
                raise ValueError(
                    f"Path '{user_path}' escapes from '/docker' after normalization."
                    f"\nResult: '{final_path}'"
                    f"\nPlease provide a path under /docker or under the execution folder."
                )
            return final_path

        # (c) If it's relative, join it under /docker and then normalize again
        else:
            joined_path = posixpath.join("/docker", path_clean)
            final_path = posixpath.normpath(joined_path)

            # If after normalization it no longer starts with /docker, that means
            # we used '..' to escape the /docker directory => raise an error
            if not final_path.startswith("/docker"):
                raise ValueError(
                    f"Relative path '{user_path}' escapes from '/docker' after normalization.\n"
                    f"Resulting path: '{final_path}'\n"
                    "Please do not use '..' to go outside /docker."
                )
            return final_path
    else:
        # Outside Docker, return absolute path on the local system
        return os.path.abspath(path_clean)
