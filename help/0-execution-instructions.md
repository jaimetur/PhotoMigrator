# 1. Instructions to execute from Compiled Binaries: \(simplest way)

### 1.1 You can copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

### 1.2. Edit the configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/config-file.md) .

### 1.3 Execute the Tool depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**CloudPhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**CloudPhotoMigrator.run**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.


---
# 2. Instructions to execute from Docker Container: \(recommended)

> [!IMPORTANT] 
> ### ✅ Prerequisites:
> - Install Docker in your system (if it is not installed yet) and run it.  You can find instructions of how to install Docker in the following links:  
>     - [Install Docker on Windows](/help/install-docker-windows.md)  
>     - [Install Docker on Linux](/help/install-docker-linux.md)  
>     - [Install Docker on MacOS](/help/install-docker-macos.md)  


Once you have Docker installed and running on your system, just follow these steps to download, extract, configure and run the tool on Docker.

### 2.1. Download the ZIP package:

Download the latest version of the Docker package from the [Releases page](https://github.com/jaimetur/CloudPhotoMigrator/releases), or use this command:

```
wget https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.1.0-beta1/CloudPhotoMigrator_v3.1.0-beta1_docker.zip
```


### 2.2. Unzip the downloaded package:

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


### 2.3. Edit the configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/config-file.md) .


### 2.4. Run the Tool to show the command line help:

Make sure Docker is running, then:

- **Linux / MacOS:**
    ```bash
    ./CloudPhotoMigrator.sh -h
    ```

- **Windows (Command Prompt):**
    ```bash
    CloudPhotoMigrator.bat -h
    ```


---
# 3. Instructions to execute from Source Repository:

> [!IMPORTANT]  
> ### ✅ Prerequisites:
> You have to make sure that you have Python 3.8 or higher on your system before to do the following steps.

Here are simple instructions to clone the GitHub repository, create a Python virtual environment, install dependencies, and run the main script.  

Find below the needed steps:

### 3.1. Clone the repository
   ```bash
   git clone https://github.com/jaimetur/CloudPhotoMigrator.git
   ```

### 3.2. Change directory to the cloned repository
   ```bash
   cd CloudPhotoMigrator
   ```

### 3.3. Create a Python virtual environment:  
   ```bash
   python3 -m venv venv
   ```

### 3.4. Activate the virtual environment:  
   - On Linux / MacOS:  
     ```bash
     source venv/bin/activate
     ```
   - On Windows (Command Prompt):  
     ```bash
     venv\Scripts\activate
     ```
   - On Windows (PowerShell):  
     ```bash
     venv\Scripts\Activate.ps1
     ```

### 3.5. Install dependencies:  
   ```bash
   pip3 install -r requirements.txt
   ```


### 3.6. Edit the configuration file:

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](/help/config-file.md) .


### 3.7. Run the Tool to show the command line help:
   ```bash
   python3 ./src/CloudPhotoMigrator.py -h
   ```

---
## Notes

- If `Config.ini` is missing, the tool will automatically create a default one and ask you to edit it before continuing.
- The required Docker image is pulled the first time you run the script.


---
## Requirements

- [Docker](https://www.docker.com/products/docker-desktop) must be installed and running.
