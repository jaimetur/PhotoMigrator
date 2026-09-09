import os
import sys
from pathlib import Path

import uvicorn


THIS_FILE = Path(__file__).resolve()
SRC_ROOT = THIS_FILE.parent
PROJECT_ROOT = SRC_ROOT.parent
LOCAL_WEB_ROOT = PROJECT_ROOT / ".web-dev"
LOCAL_CONFIG_DIR = LOCAL_WEB_ROOT / "config"
LOCAL_CONFIG_GENERATED_DIR = LOCAL_CONFIG_DIR / "generated"
LOCAL_DATA_DIR = LOCAL_WEB_ROOT / "data"
LOCAL_VOLUMES_DIR = LOCAL_WEB_ROOT / "volumes"
LOCAL_BACKUPS_DIR = LOCAL_WEB_ROOT / "backups"
LOCAL_STATE_PATH = LOCAL_CONFIG_DIR / "web_interface_state.json"
LOCAL_DB_PATH = LOCAL_CONFIG_DIR / "web_interface.db"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "Config.ini"


def _ensure_runtime_dirs():
    """Create the directories selected by the effective environment."""
    paths = (
        Path(os.environ["PHOTOMIGRATOR_CONFIG_PATH"]).parent,
        Path(os.environ["PHOTOMIGRATOR_STATE_PATH"]).parent,
        Path(os.environ["PHOTOMIGRATOR_WEB_DB_PATH"]).parent,
        Path(os.environ["PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR"]),
        Path(os.environ["PHOTOMIGRATOR_DOCKER_BASE_PATH"]),
        Path(os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_DATA"]),
        Path(os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1"]),
        Path(os.environ["PHOTOMIGRATOR_WEB_BACKUP_DIR"]),
    )
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _set_default_env(name, value):
    if not os.environ.get(name):
        os.environ[name] = str(value)


def _configure_local_web_environment():
    _set_default_env("PHOTOMIGRATOR_CONFIG_PATH", DEFAULT_CONFIG_PATH)
    _set_default_env("PHOTOMIGRATOR_STATE_PATH", LOCAL_STATE_PATH)
    _set_default_env("PHOTOMIGRATOR_WEB_DB_PATH", LOCAL_DB_PATH)
    _set_default_env("PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH", DEFAULT_CONFIG_PATH)
    _set_default_env("PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR", LOCAL_CONFIG_GENERATED_DIR)
    _set_default_env("PHOTOMIGRATOR_DOCKER_BASE_PATH", LOCAL_DATA_DIR)
    _set_default_env("PHOTOMIGRATOR_WEB_USER_ROOT_DATA", LOCAL_DATA_DIR)
    _set_default_env("PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1", LOCAL_VOLUMES_DIR)
    _set_default_env(
        "PHOTOMIGRATOR_WEB_DELETE_ROOTS",
        ",".join(
            (
                str(LOCAL_DATA_DIR),
                str(LOCAL_CONFIG_DIR),
                str(LOCAL_VOLUMES_DIR),
            )
        ),
    )
    _set_default_env("PHOTOMIGRATOR_WEB_BACKUP_DIR", LOCAL_BACKUPS_DIR)
    _set_default_env("PHOTOMIGRATOR_BOOTSTRAP_ADMIN_USER", "admin")
    _set_default_env("PHOTOMIGRATOR_BOOTSTRAP_ADMIN_PASS", "admin123")
    _set_default_env("PHOTOMIGRATOR_WEB_SECRET", "photomigrator-local-dev-secret")
    _ensure_runtime_dirs()


def main():
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))

    _configure_local_web_environment()

    host = os.environ.get("PHOTOMIGRATOR_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("PHOTOMIGRATOR_WEB_PORT", "6078"))
    reload_enabled = os.environ.get("PHOTOMIGRATOR_WEB_RELOAD", "0") == "1"

    # `SRC_ROOT` is the import root when this script is executed directly.
    # Import the web package from it so this does not depend on PyCharm marking
    # `src` as a source root.
    from web_interface.app import app

    # Passing the app object also makes the dependency visible to binary
    # packagers. Uvicorn needs an import string only for its reload subprocess.
    app_target = "web_interface.app:app" if reload_enabled else app
    uvicorn.run(app_target, host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
