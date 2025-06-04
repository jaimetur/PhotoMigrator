# Execution from Docker Container: \(recommended)

> [!IMPORTANT] 
> ### ✅ Prerequisites:
> - Docker need to be installed & running in your system.
> - To install and run Docker (if it is not installed yet), you can follow the next instructions:  
>     - [Install Docker on Windows](https://github.com/jaimetur/PhotoMigrator/blob/main/help/install-docker/install-docker-windows.md)  
>     - [Install Docker on Linux](https://github.com/jaimetur/PhotoMigrator/blob/main/help/install-docker/install-docker-linux.md)  
>     - [Install Docker on MacOS](https://github.com/jaimetur/PhotoMigrator/blob/main/help/install-docker/install-docker-macos.md)  


Once you have Docker installed and running on your system, you have two options to run the Tool from a Docker Container Image:
## 🚀 1. Run Docker from a Pre-built Shell Script (recommended):

This is the recommended option, since it will download a small package that contains:
- A shell script to run the docker container in an easier way.
- Documentation folder.
- Help folder.
- Default Configuration file (Config.ini).
- docker.conf file to easilly select the docker container image that you want to run.

If you chose this option, just need to follow the next steps:

### 📥 1.1. Download the ZIP package:

Download the latest version of the Docker package from the [Releases page](https://github.com/jaimetur/PhotoMigrator/releases), or use the following command:

- **Linux/macOS:**
    ```bash
    curl -L -o PhotoMigrator_v3.3.1-alpha_docker.zip https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.1-alpha/PhotoMigrator_v3.3.1-alpha_docker.zip
    ```
  
- **Windows (PoowerShell):**
    ```bash
    curl.exe -L -o PhotoMigrator_v3.3.1-alpha_docker.zip https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.1-alpha/PhotoMigrator_v3.3.1-alpha_docker.zip
    ```


### 📦 1.2. Unzip the downloaded package:

- **Linux/macOS:**
    ```bash
    sudo apt install 7zip
    7z x PhotoMigrator_v3.3.1-alpha_docker.zip
    cd PhotoMigrator/docker
    ```

- **Windows (PoowerShell):**
    ```bash
    powershell -Command "Expand-Archive -Path PhotoMigrator_v3.3.1-alpha_docker.zip -DestinationPath ./"
    cd PhotoMigrator\docker
    ```


### 📝 1.3. Edit Docker Configuration file: `docker.conf`

If you want to pull a different release image (default: latest-stable) you can change the file `docker.conf` included in the package.  

```
# Configuration file for the Docker container

RELEASE_TAG=latest      # Set the RELEASE_TAG for the image that you want to pull and launch in Docker container (latest-stable: for the latest-stable version, latest: for the latest betas, or any other version)
TZ=Europe/Madrid        # Set the Time Zone for the Docker container (Important to see correct Timestamps in Logs and files/folder suffix)
```

You can obtain the different RELEASE_TAG using below command:
```bash
curl -s "https://registry.hub.docker.com/v2/repositories/jaimetur/photomigrator/tags?page_size=100" | jq '.results[].name'
```
The result should be something like this:  
  "latest"  
  "latest-stable"  
  "3.3.1"  
  "3.2.0"  
  "3.1.0"  


### 📝 1.4. Edit Tool Configuration file: `Config.ini`

Open the file `Config.ini` included in the package with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md).


### 🚀 1.5. Run the Tool:

Make sure Docker is running, then:

- **Linux / MacOS:**
    ```bash
    chmod +x ./PhotoMigrator.sh
    ./PhotoMigrator.sh [OPTIONS]
    ``` 
- **Windows (Command Prompt):**
    ```bash
    PhotoMigrator.bat [OPTIONS]
    ```

#### Where,
  - **[OPTIONS]** are the arguments that you want to pass to the Tool (i.e: -h)
 
#### Exampe for Linux / MacOS:
  - Execute the Tool to show the command line help:
    ```bash
    ./PhotoMigrator.sh -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    ./PhotoMigrator.sh --source=./MyTakeout --target=immich-photos
    ```
    
> [!NOTE]
> - The required Docker image is pulled the first time you run the script or if the remote image has changed.
> - If `Config.ini` is missing, the tool will automatically create a default one and ask you to edit it before continuing.

> [!IMPORTANT]
> - If your system requires elevation to run docker commands, you have to call it using 'sudo' and enter admin password.
> - Example:
>   ```bash
>   sudo ./PhotoMigrator.sh -h
>   ```


---
## 🐳 2. Run Docker Container directly:

### 📥 2.1. First Pull the image for the desired release:
  ```bash
  docker pull jaimetur/photomigrator:[RELEASE_TAG]
  ```

#### Where,
  - **[RELEASE_TAG]** is the Tag of the release that you want to pull.
    
    You can obtain the different RELEASE_TAG using below command:
    ```bash
    curl -s "https://registry.hub.docker.com/v2/repositories/jaimetur/photomigrator/tags?page_size=100" | jq '.results[].name'
    ```
    The result should be something like this:  
      "latest"  
      "latest-stable"  
      "3.3.1"  
      "3.2.0"  
      "3.1.0"  

#### Example:
  - For latest release:
    ```bash
    docker pull jaimetur/photomigrator:latest
    ```
  - For specific release.
    ```
    docker pull jaimetur/photomigrator:3.2.0
    ```

### 📥 2.2. Download Configuration File: `Config.ini`
- **Linux/macOS:**
    ```bash
    curl -L -o Config.ini https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/Config.ini
    ```
- **Windows (PoowerShell):**
  ```bash
  curl.exe -L -o Config.ini https://raw.githubusercontent.com/jaimetur/PhotoMigrator/main/Config.ini
  ```

### 📝 2.3. Edit Tool Configuration file: `Config.ini`

Open the file `Config.ini` downloaded in the step before with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md).


### 🐳 2.4. Execute the pulled image with docker:
- For Linux / MacOS: 
  ```bash
  docker run -it --rm -v "$(pwd)":/docker -e TZ=[TIMEZONE] jaimetur/photomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (PowerShell): 
  ```bash
  docker run -it --rm -v "${PWD}:/docker" -e TZ=[TIMEZONE] jaimetur/photomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (Command Prompt): 
  ```bash
  docker run -it --rm -v "%cd%":/docker -e TZ=[TIMEZONE] jaimetur/photomigrator:[RELEASE_TAG] [OPTIONS]
  ```

#### Where,
  - **[TIMEZONE]** is the Time Zone that you want to use. (i.e: Europe/Madrid)
  - **[RELEASE_TAG]** is the Tag of the release that you want to execute. (recommended: `latest-stable`or `latest`)
  - **[OPTIONS]** are the arguments that you want to pass to the Tool. (i.e: -h)

#### Example for Linux / MacOS:
  - Execute the Tool to show the command line help:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator:latest -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator:latest --source=./MyTakeout --target=immich-photos
    ```
#### Example for Windows:
  - Execute the Tool to show the command line help:
    ```bash
    docker run -it --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/photomigrator:latest -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    docker run -it --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/photomigrator:latest --source=./MyTakeout --target=immich-photos
    ```

> [!IMPORTANT]
> - If your system requires elevation to run docker commands, you have to call it using 'sudo' and enter admin password.
> - Example:
>   ```bash
>   sudo docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator:latest -h
>   ```

---

## [[🏠 Back to Main Page](https://github.com/jaimetur/PhotoMigrator/tree/main)](https://github.com/jaimetur/PhotoMigrator/tree/main)



---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 
