# Instructions to execute from Docker Container: \(recommended)

> [!IMPORTANT] 
> ### ✅ Prerequisites:
> - Install Docker in your system (if it is not installed yet) and run it.  You can find instructions of how to install Docker in the following links:  
>     - [Install Docker on Windows](/help/install-docker-windows.md)  
>     - [Install Docker on Linux](/help/install-docker-linux.md)  
>     - [Install Docker on MacOS](/help/install-docker-macos.md)  


Once you have Docker installed and running on your system, just follow these steps to download, extract, configure and run the tool on Docker.

### 1. Download the ZIP package:

Download the latest version of the Docker package from the [Releases page](https://github.com/jaimetur/CloudPhotoMigrator/releases), or use this command:

```
curl -L -o CloudPhotoMigrator_v3.1.0-beta1_docker.zip https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.1.0-beta1/CloudPhotoMigrator_v3.1.0-beta1_docker.zip
```


### 2. Unzip the downloaded package:

- **Linux/macOS:**
    ```bash
    unzip CloudPhotoMigrator_v3.1.0-beta1_docker.zip -d CloudPhotoMigrator
    cd CloudPhotoMigrator
    ```

- **Windows (Command Prompt):**
    ```bash
    powershell -Command "Expand-Archive -Path CloudPhotoMigrator_v3.1.0-beta1_docker.zip -DestinationPath CloudPhotoMigrator"
    cd CloudPhotoMigrator
    ```

### 3. Edit the .env file (optional):   

If you want to pull a different container image (default: latest) you can change the .env file  

```
# Set the RELEASE_TAG for the image that you want to pull
RELEASE_TAG=latest
```


### 4. Edit the configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/0-configuration-file.md) .


### 5. Run the Tool to show the command line help:

Make sure Docker is running, then:

- **Linux / MacOS:**
    ```bash
    ./CloudPhotoMigrator.sh -h

    ```
  or, if your system requires elevation to execute docker:
    ```bash
    sudo ./CloudPhotoMigrator.sh -h
    ```

- **Windows (Command Prompt):**
    ```bash
    CloudPhotoMigrator.bat -h
    ```

> [!NOTE]
> - The required Docker image is pulled the first time you run the script or if the remote image has changed.
> - If `Config.ini` is missing, the tool will automatically create a default one and ask you to edit it before continuing.


---
## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 