# Instructions to execute from Docker Container: \(recommended)

> [!IMPORTANT] 
> ### ✅ Prerequisites:
> - Docker need to be installed & running in your system.
> - To install and run Docker (if it is not installed yet), you can follow the next instructions:  
>     - [Install Docker on Windows](/help/install-docker-windows.md)  
>     - [Install Docker on Linux](/help/install-docker-linux.md)  
>     - [Install Docker on MacOS](/help/install-docker-macos.md)  


Once you have Docker installed and running on your system, you have twoo options to run the Tool from a Docker Container Image:
## 1. Run Docker Container directly:

### 1.1. First Pull the image for the desired release:
  ```bash
  docker pull jaimetur/cloudphotomigrator:[RELEASE_TAG]
  ```

#### Where,
  - **[RELEASE_TAG]** is the Tag of the release that you want to pull.

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
  docker run -it --rm -v "$(pwd)":/docker jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (PowerShell): 
  ```bash
  docker run -it --rm -v "${PWD}:/docker" jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```
- For Windows (Command Prompt): 
  ```bash
  docker run -it --rm -v "%cd%":/docker jaimetur/cloudphotomigrator:[RELEASE_TAG] [OPTIONS]
  ```

#### Where,
  - **[RELEASE_TAG]** is the Tag of the release that you want to execute.
  - **[OPTIONS]** are the arguments that you want to pass to the Tool (i.e: -h)

#### Example for Linux / MacOS:
  - Execute the Tool to show the command line help:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker jaimetur/cloudphotomigrator:latest -h
    ```
  - Execute the Tool to do an Automated Migration:
    ```bash
    docker run -it --rm -v "$(pwd)":/docker jaimetur/cloudphotomigrator:latest --source=./MyTakeout --target=immich-photos
    ```

> [!IMPORTANT]
> - If your system requires elevation to run docker commands, you have to call it using 'sudo' and enter admin password.
> - Example:
>   ```bash
>   sudo docker run -it --rm -v "$(pwd)":/docker jaimetur/cloudphotomigrator:latest -h
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
    curl -L -o CloudPhotoMigrator_v3.1.0-beta2_docker.zip https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.1.0-beta2/CloudPhotoMigrator_v3.1.0-beta2_docker.zip
    ```
  
- **Windows (PoowerShell):**
    ```bash
    curl.exe -L -o CloudPhotoMigrator_v3.1.0-beta2_docker.zip https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.1.0-beta2/CloudPhotoMigrator_v3.1.0-beta2_docker.zip
    ```


### 2.2. Unzip the downloaded package:

- **Linux/macOS:**
    ```bash
    unzip CloudPhotoMigrator_v3.1.0-beta2_docker.zip -d CloudPhotoMigrator
    cd CloudPhotoMigrator
    ```

- **Windows (PoowerShell):**
    ```bash
    powershell -Command "Expand-Archive -Path CloudPhotoMigrator_v3.1.0-beta2_docker.zip -DestinationPath CloudPhotoMigrator"
    cd CloudPhotoMigrator
    ```


### 2.3. Edit the docker.conf file (optional):   

If you want to pull a different release image (default: latest) you can change the .env file  

```
RELEASE_TAG=latest      # Set the RELEASE_TAG for the image that you want to pull
TZ=Europe/Madrid        # Set the Time Zone for the Docker container
```


### 2.4. Edit the configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/0-configuration-file.md) .


### 2.5. Run the Tool:

Make sure Docker is running, then:

- **Linux / MacOS:**
    ```bash
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