# Deploy Web Interface from Docker

This guide explains how to run the PhotoMigrator Web Interface with Docker Compose on Linux, Windows, and macOS.

> [!IMPORTANT]
> This guide is for the browser-based Interface (WEB) image.
>
> If you want to run the Command line-based Interface with Docker Compose, use:
> [Deploy CLI Interface from Docker](/help/docker-deployments/deploy-cli-interface-from-docker.md)

## ✅ Prerequisites

- Docker must be installed and running.
- Installation help:
  - [Install Docker on Windows](/help/install-docker/install-docker-windows.md)
  - [Install Docker on Linux](/help/install-docker/install-docker-linux.md)
  - [Install Docker on MacOS](/help/install-docker/install-docker-macos.md)

After installation, verify:

```bash
docker --version
docker compose version
```

## Docker Images
The Web Interface image is:

```bash
jaimetur/photomigrator
```

> [!NOTE]
> - On Windows and macOS, Docker Desktop is the expected setup.
> - On Linux, if you want to run Docker without `sudo`, follow Docker's post-install steps:
>   https://docs.docker.com/engine/install/linux-postinstall/

---
## 1. Download the ready-to-use Docker files

For the Web Interface, the repository already includes ready-to-use files:

- [`docker-web/docker-compose.yml`](/docker-web/docker-compose.yml)
- [`docker-web/.env`](/docker-web/.env)

They are designed to work as-is for a local deployment on Linux, Windows, and macOS.

They are also included in the Docker ZIP package:

- [`PhotoMigrator_v4.1.0_docker.zip`](https://github.com/jaimetur/PhotoMigrator/releases/download/v4.1.0/PhotoMigrator_v4.1.0_docker.zip)

### What you can use without modifying anything

If you download those two files and run `docker compose up -d`, Docker will:

- pull the published `jaimetur/photomigrator` image
- publish the Web Interface on port `6078`
- create host folders automatically if `../config`, `../data`, or `../volumes` do not exist yet
- store the application database and generated files inside those mounted folders

By default, the application will bootstrap the first local admin account with:

- Username: `admin`
- Password: `admin123`

That is acceptable for a local test on your own machine. If you plan to expose the container beyond localhost or keep it running permanently, customize the security-related variables shown later in this guide.

### Download commands

- **Linux/macOS**
  ```bash
  mkdir -p docker-web
  cd docker-web
  curl -L -o docker-compose.yml https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/docker-web/docker-compose.yml
  curl -L -o .env https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/docker-web/.env
  ```

- **Windows (PowerShell)**
  ```bash
  New-Item -ItemType Directory -Force docker-web | Out-Null
  Set-Location docker-web
  curl.exe -L -o docker-compose.yml https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/docker-web/docker-compose.yml
  curl.exe -L -o .env https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/docker-web/.env
  ```

If you already cloned the repository, you can simply use the existing `docker-web/docker-compose.yml` and `docker-web/.env` files.

---
## 2. Start the Web Interface

From the folder that contains `docker-compose.yml` and `.env`:

```bash
docker compose pull
docker compose up -d
```

Then open:

- `http://localhost:6078`

Useful commands:

- Show logs
  ```bash
  docker compose logs -f
  ```

- Stop the stack
  ```bash
  docker compose down
  ```

- Pull a newer image and recreate the container
  ```bash
  docker compose pull
  docker compose up -d
  ```

---
## 3. Files used by Docker Compose

### `docker-compose.yml`

For production/local use, you normally do not need to edit `docker-compose.yml`. All normal customization is done through `.env`.

Current file:

```yaml
# PhotoMigrator Web Interface compose file for production.
services:
  photomigrator:
    image: jaimetur/photomigrator:${IMAGE_TAG}
    container_name: ${CONTAINER_NAME}
    ports:
      - "${PORT}:6078"
    env_file:
      - .env
    volumes:
      - ${CONFIG_DIR}:/app/config
      - ${DATA_DIR}:/app/data
      - ${VOLUMES_DIR}:/app/volumes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import sys,urllib.request; urllib.request.urlopen('http://127.0.0.1:6078/healthz', timeout=5); sys.exit(0)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

### `.env`

The tracked `docker-web/.env` file is a portable default configuration that works on Linux, Windows, and macOS:

```env
# PhotoMigrator Web Interface defaults for docker compose.
# These values work as-is for a local deployment on Linux, Windows, and macOS.

TZ=Europe/Madrid
CONTAINER_NAME=photomigrator
PORT=6078
PORT_DEV=6071
IMAGE_TAG=latest-stable
CONFIG_DIR=../config
DATA_DIR=../data
VOLUMES_DIR=../volumes
APP_DIR=../
PHOTOMIGRATOR_WEB_DELETE_ROOTS=/app/data,/app/config,/app/volumes
PHOTOMIGRATOR_WEB_MAX_JOB_OUTPUT_LINES=100000
PHOTOMIGRATOR_DEFAULT_GOOGLE_TAKEOUT_PATH=
```

The relative paths above are intentional. They avoid Linux-only absolute paths such as `/volume1` and make the same file usable from:

- Linux
- Windows with Docker Desktop
- macOS with Docker Desktop

---
## 4. Which `.env` values are mandatory to change?

### Mandatory changes

For a local test deployment on your own machine:

- none

You can use `docker-compose.yml` and `.env` exactly as downloaded.

### Strongly recommended changes before exposing the service on a network

Add these variables to `.env`:

```env
PHOTOMIGRATOR_WEB_SECRET=replace-with-a-long-random-secret
PHOTOMIGRATOR_BOOTSTRAP_ADMIN_USER=your-admin-user
PHOTOMIGRATOR_BOOTSTRAP_ADMIN_PASS=your-admin-password
```

If you do not set them, the app falls back to:

- user `admin`
- password `admin123`
- secret `change-me-photomigrator-web-secret`

Those defaults are convenient for a local first run, but they are not appropriate for a long-lived or network-exposed deployment.

### Common optional changes

You can customize these values if you want:

```env
TZ=Europe/Madrid
PORT=6078
IMAGE_TAG=latest-stable
CONFIG_DIR=../config
DATA_DIR=../data
VOLUMES_DIR=../volumes
PHOTOMIGRATOR_DEFAULT_GOOGLE_TAKEOUT_PATH=
PHOTOMIGRATOR_WEB_MAX_JOB_OUTPUT_LINES=100000
PHOTOMIGRATOR_WEB_DELETE_ROOTS=/app/data,/app/config,/app/volumes
```

What they control:

- `TZ`: timezone inside the container
- `PORT`: host port published for the Web Interface
- `IMAGE_TAG`: which published image tag to pull
- `CONFIG_DIR`: where the web app stores its database, generated config cache, backups, and exported files
- `DATA_DIR`: default root for user-managed input/output folders inside the UI
- `VOLUMES_DIR`: optional extra mounted root shown in the UI folder browser
- `PHOTOMIGRATOR_DEFAULT_GOOGLE_TAKEOUT_PATH`: default value pre-filled in the Google Takeout path field
- `PHOTOMIGRATOR_WEB_MAX_JOB_OUTPUT_LINES`: in-memory output limit shown in the job panel
- `PHOTOMIGRATOR_WEB_DELETE_ROOTS`: allowed roots for "Remove Selected" operations from the web file browser

### Optional cloud credentials and runtime overrides

If you prefer not to store some secrets in the UI-managed config, you can inject them through `.env`:

```env
IMMICH_URL=http://immich-server:2283
IMMICH_API_KEY_ADMIN=your_admin_api_key
# IMMICH_API_KEY_ADMIN_FILE=/run/secrets/immich_admin_api_key
```

Environment variables override the values stored in `Config.ini` at runtime.

---
## 5. Cross-platform notes

### Linux

- `sudo` may be required only if your Linux user does not have permission to access Docker.
- Relative bind-mount paths such as `../config` or `../data` work directly.

### Windows

- Use Docker Desktop.
- Run the commands from PowerShell or Command Prompt in the folder that contains `docker-compose.yml`.
- Do not use `sudo`.
- The provided relative paths in `.env` are valid for Docker Desktop and avoid shell-specific absolute path syntax.

### macOS

- Use Docker Desktop.
- The same `docker-compose.yml` and `.env` files work without path changes.

---
## 6. Notes about configuration storage

The Web Interface can start without a manually prepared `Config.ini`.

On first run it can work with the bundled default configuration template and the persistent state stored under the mounted config folder. You can then:

- edit configuration values from the browser
- import/export `Config.ini`
- keep runtime secrets in `.env` if preferred

If you already have an existing `Config.ini`, you can still place it in `CONFIG_DIR` or import it later from the Web Interface.

---

## 🏠 [Back to Main Page](/README.md)
