# Deploy CLI Interface from Docker

This guide explains how to run the PhotoMigrator Command Line Interface (CLI) with Docker Compose on Linux, Windows, and macOS.

> [!IMPORTANT]
> This guide is for the command line interface (CLI) image.
>
> If you want to run the browser-based Web Interface with Docker Compose, use:
> [Deploy Web Interface from Docker](deploy-web-interface-from-docker.md)

## ✅ Prerequisites

- Docker must be installed and running on your system.
- Installation help:
  - [Install Docker on Windows](../install-docker/install-docker-windows.md)
  - [Install Docker on Linux](../install-docker/install-docker-linux.md)
  - [Install Docker on MacOS](../install-docker/install-docker-macos.md)

After installation, verify:

```bash
docker --version
docker compose version
```

## Docker Images

PhotoMigrator currently publishes different Docker images for different use cases:

- `jaimetur/photomigrator` -> Web Interface image
- `jaimetur/photomigrator-linux` -> CLI image used in this guide

The examples below intentionally use `jaimetur/photomigrator-linux` because that image launches `PhotoMigrator.py` directly and supports CLI arguments such as `-h`, `--source`, or `--target`.

> [!NOTE]
> - On Windows and macOS, Docker Desktop is the expected setup.
> - On Linux, if you want to run Docker without `sudo`, follow Docker's post-install steps:
>   https://docs.docker.com/engine/install/linux-postinstall/

---
## 1. Run the CLI from the packaged launcher

This option downloads a small ZIP package that includes:

- the `docker-cli/` folder with:
  - `PhotoMigrator.sh`
  - `PhotoMigrator.bat`
  - `docker.conf`
  - `Config.ini`
  - bundled `help/` and `docs/`

### 1.1. Download the ZIP package

Direct download:

- [`PhotoMigrator_v4.5.0_docker.zip`](https://github.com/jaimetur/PhotoMigrator/releases/download/v4.5.0/PhotoMigrator_v4.5.0_docker.zip)

- **Linux/macOS**
  ```bash
  curl -L -o PhotoMigrator_v4.5.0_docker.zip https://github.com/jaimetur/PhotoMigrator/releases/download/v4.5.0/PhotoMigrator_v4.5.0_docker.zip
  ```

- **Windows (PowerShell)**
  ```bash
  curl.exe -L -o PhotoMigrator_v4.5.0_docker.zip https://github.com/jaimetur/PhotoMigrator/releases/download/v4.5.0/PhotoMigrator_v4.5.0_docker.zip
  ```

### 1.2. Unzip the package

- **Linux/macOS**
  ```bash
  7z x PhotoMigrator_v4.5.0_docker.zip
  cd PhotoMigrator/docker-cli
  ```

- **Windows (PowerShell)**
  ```bash
  powershell -Command "Expand-Archive -Path PhotoMigrator_v4.5.0_docker.zip -DestinationPath ./"
  cd PhotoMigrator\docker-cli
  ```

### 1.3. Adjust `docker.conf` if needed

`docker.conf` controls which CLI image tag is pulled by `PhotoMigrator.sh`:

```ini
# Configuration file for the Docker container

RELEASE_TAG=latest-stable
TZ=Europe/Madrid
```

To list available CLI tags:

```bash
curl -s "https://registry.hub.docker.com/v2/repositories/jaimetur/photomigrator-linux/tags?page_size=100" | jq '.results[].name'
```

### 1.4. Edit `Config.ini`

Open `Config.ini` and update your credentials and settings.

More details:
[Configuration File](../00-configuration-file.md)

### 1.5. Run the tool

- **Linux/macOS**
  ```bash
  chmod +x ./PhotoMigrator.sh
  ./PhotoMigrator.sh [OPTIONS]
  ```

- **Windows (Command Prompt or PowerShell)**
  ```bat
  PhotoMigrator.bat [OPTIONS]
  ```

Examples:

- Show CLI help
  ```bash
  ./PhotoMigrator.sh -h
  ```

- Show CLI help on Windows
  ```bat
  PhotoMigrator.bat -h
  ```

- Run an automated migration
  ```bash
  ./PhotoMigrator.sh --source=./MyTakeout --target=immich-photos
  ```

- Run an automated migration on Windows
  ```bat
  PhotoMigrator.bat --source=./MyTakeout --target=immich-photos
  ```

> [!NOTE]
> - `PhotoMigrator.sh` pulls `jaimetur/photomigrator-linux`.
> - `PhotoMigrator.bat` also pulls `jaimetur/photomigrator-linux` and runs that Linux container through Docker Desktop.
> - If `Config.ini` is missing, the CLI container creates a default one inside the mounted folder and exits so you can edit it.
> - A published `jaimetur/photomigrator-windows` image is not required for normal Windows usage.

---
## 2. Run the CLI image directly with Docker

This method works on Linux, Windows, and macOS. On Windows and macOS it runs through Docker Desktop's Linux container support.

### 2.1. Pull the CLI image

```bash
docker pull jaimetur/photomigrator-linux:[RELEASE_TAG]
```

Examples:

- Latest stable release
  ```bash
  docker pull jaimetur/photomigrator-linux:latest-stable
  ```

- Latest published CLI image
  ```bash
  docker pull jaimetur/photomigrator-linux:latest
  ```

- Specific version
  ```bash
  docker pull jaimetur/photomigrator-linux:4.5.0
  ```

### 2.2. Download `Config.ini`

- **Linux/macOS**
  ```bash
  curl -L -o Config.ini https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/Config.ini
  ```

- **Windows (PowerShell)**
  ```bash
  curl.exe -L -o Config.ini https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/Config.ini
  ```

### 2.3. Edit `Config.ini`

Open `Config.ini` and set your credentials before running cloud operations.

### 2.4. Run the CLI container

For non-interactive commands such as `-h`, do not allocate a TTY. For commands that may ask for confirmation, keep `-it`.

- **Linux/macOS help example**
  ```bash
  docker run --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable -h
  ```

- **Windows PowerShell help example**
  ```bash
  docker run --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable -h
  ```

- **Windows Command Prompt help example**
  ```bash
  docker run --rm -v "%cd%":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable -h
  ```

- **Linux/macOS interactive migration example**
  ```bash
  docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable --source=./MyTakeout --target=immich-photos
  ```

- **Windows PowerShell interactive migration example**
  ```bash
  docker run -it --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable --source=./MyTakeout --target=immich-photos
  ```

- **Windows Command Prompt interactive migration example**
  ```bash
  docker run -it --rm -v "%cd%":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable --source=./MyTakeout --target=immich-photos
  ```

### 2.5. Headless or scripted runs

If you do not want interactive confirmations:

```bash
docker run --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable --no-request-user-confirmation [OPTIONS]
```

> [!IMPORTANT]
> - Use `sudo` only on Linux hosts where your user is not allowed to access Docker.
> - Do not use `sudo` on Windows.
> - `jaimetur/photomigrator` is the Web Interface image, so it is not the correct image for CLI flags such as `-h`.

---

## 🏠 [Back to Main Page](../../README.md)
