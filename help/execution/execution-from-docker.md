# Execution from Docker Container: \(recommended)

> [!IMPORTANT] 
> ### ✅ Prerequisites:
> - Docker need to be installed & running in your system.
> - To install and run Docker (if it is not installed yet), you can follow the next instructions:  
>     - [Install Docker on Windows](/help/install-docker/install-docker-windows.md)  
>     - [Install Docker on Linux](/help/install-docker/install-docker-linux.md)  
>     - [Install Docker on MacOS](/help/install-docker/install-docker-macos.md)  


Once you have Docker installed and running on your system, you have twoo options to run the Tool from a Docker Container Image:
## 1. Run Docker Container directly:

### 1.1. First Pull the image for the desired release:
  ```bash
  docker pull jaimetur/cloudphotomigrator:[RELEASE_TAG]
  ```

#### Where,
  - **[RELEASE_TAG]** is the Tag of the release that you want to pull.
    
    You can obtain the different RELEASE_TAG using below command:
    ```bash
    curl -s "https://registry.hub.docker.com/v2/repositories/jaimetur/cloudphotomigrator/tags?page_size=100" | jq '.results[].name'
    ```
    The result should be something like this:  
      "latest"  
      "latest-stable"  
      "3.2.0"  
      "3.1.0"  

#### Example:
  - For latest release:
    ```bash
    docker pull jaimetur/cloudphotomigrator:latest
    ```
  - For specific release.
    ```
    docker pull jaimetur/cloudphotomigrator:3.1.0
    ```


### 1.2. Execute the pulled image with docker:
- For Linux / MacOS: 
  ```bash
  docker run -it --rm -v "$(pwd)":/docker -e TZ=[TIMEZONE] jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (PowerShell): 
  ```bash
  docker run -it --rm -v "${PWD}:/docker" -e TZ=[TIMEZONE] jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (Command Prompt): 
  ```bash
  docker run -it --rm -v "%cd%":/docker -e TZ=[TIMEZONE] jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```

#### Where,
  - **[TIMEZONE]** is the Time Zone that you want to use. (i.e: Europe/Madrid)
  - **[RELEASE_TAG]** is the Tag of the release that you want to execute.
  - **[OPTIONS]** are the arguments that you want to pass to the Tool. (i.e: -h)

#### Example for Linux / MacOS:
  - Execute the Tool to show the command line help:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/cloudphotomigrator:latest -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/cloudphotomigrator:latest --source=./MyTakeout --target=immich-photos
    ```

> [!IMPORTANT]
> - If your system requires elevation to run docker commands, you have to call it using 'sudo' and enter admin password.
> - Example:
>   ```bash
>   sudo docker run -it --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/cloudphotomigrator:latest -h
>   ```

## 2. Run Docker from a Pre-built Shell Script (recommended):

This is the recommended option, since it will download a small package that contains:
- A shell script to run the docker container in an easier way.
- Documentation folder.
- Help folder.
- Default Configuration file (Config.ini).
- docker.conf file to easilly select the docker container image that you want to run.

If you chose this option, just need to follow the next steps:

### 2.1. Download the ZIP package:

Download the latest version of the Docker package from the [Releases page](https://github.com/jaimetur/CloudPhotoMigrator/releases), or use the following command:

- **Linux/macOS:**
    ```bash
    curl -L -o CloudPhotoMigrator_v3.2.0-beta_docker.zip https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.2.0-beta/CloudPhotoMigrator_v3.2.0-beta_docker.zip
    ```
  
- **Windows (PoowerShell):**
    ```bash
    curl.exe -L -o CloudPhotoMigrator_v3.2.0-beta_docker.zip https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.2.0-beta/CloudPhotoMigrator_v3.2.0-beta_docker.zip
    ```


### 2.2. Unzip the downloaded package:

- **Linux/macOS:**
    ```bash
    7z x CloudPhotoMigrator_v3.2.0-beta_docker.zip
    cd CloudPhotoMigrator/docker
    ```

- **Windows (PoowerShell):**
    ```bash
    powershell -Command "Expand-Archive -Path CloudPhotoMigrator_v3.2.0-beta_docker.zip -DestinationPath ./"
    cd CloudPhotoMigrator\docker
    ```


### 2.3. Edit Docker Configuration file:   

If you want to pull a different release image (default: latest) you can change the file 'docker.conf'.  

```
# Configuration file for the Docker container

RELEASE_TAG=latest      # Set the RELEASE_TAG for the image that you want to pull and launch in Docker container
TZ=Europe/Madrid        # Set the Time Zone for the Docker container (Important to see correct Timestamps in Logs and files/folder suffix)
```

You can obtain the different RELEASE_TAG using below command:
```bash
curl -s "https://registry.hub.docker.com/v2/repositories/jaimetur/cloudphotomigrator/tags?page_size=100" | jq '.results[].name'
```
The result should be something like this:  
  "latest"  
  "latest-stable"  
  "3.2.0"  
  "3.1.0"  

### 2.4. Edit Tool Configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/0-configuration-file.md) .


### 2.5. Run the Tool:

Make sure Docker is running, then:

- **Linux / MacOS:**
    ```bash
    chmod +x ./CloudPhotoMigrator.sh
    ./CloudPhotoMigrator.sh [OPTIONS]
    ``` 
- **Windows (Command Prompt):**
    ```bash
    CloudPhotoMigrator.bat [OPTIONS]
    ```

#### Where,
  - **[OPTIONS]** are the arguments that you want to pass to the Tool (i.e: -h)
 
#### Exampe for Linux / MacOS:
  - Execute the Tool to show the command line help:
    ```bash
    ./CloudPhotoMigrator.sh -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    ./CloudPhotoMigrator.sh --source=./MyTakeout --target=immich-photos
    ```
    
> [!NOTE]
> - The required Docker image is pulled the first time you run the script or if the remote image has changed.
> - If `Config.ini` is missing, the tool will automatically create a default one and ask you to edit it before continuing.

> [!IMPORTANT]
> - If your system requires elevation to run docker commands, you have to call it using 'sudo' and enter admin password.
> - Example:
>   ```bash
>   sudo ./CloudPhotoMigrator.sh -h
>   ```

---
## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 
