# Instructions to execute from compiled binaries:
You can copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

Then you just need to call it depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**CloudPhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**CloudPhotoMigrator.run**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

---


# Instructions to run Docker Container:

> [!IMPORTANT] 
> ### ✅ Prerequisites
> - Install Docker in your system (if it is not installed yet) and run it.  You can find instructions of how to install Docker in the following links:  
>     - [Install Docker on Windows](/help/install-docker-windows.md)  
>     - [Install Docker on Linux](/help/install-docker-linux.md)  
>     - [Install Docker on MacOS](/help/install-docker-macos.md)  


Once you have Docker installed and running on your system, just follow these steps to download, extract, configure and run the tool on Docker.

### 1. Download the ZIP package

Download the latest version of the Docker package from the [Releases page](https://github.com/jaimetur/CloudPhotoMigrator/releases), or use this command:

```bash
wget https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.1.0-beta1/CloudPhotoMigrator_v3.1.0-beta1_docker.zip
```

---

### 2. Unzip the downloaded package

- **Linux/macOS:**

```bash
unzip CloudPhotoMigrator_v3.1.0-beta1_docker.zip -d CloudPhotoMigrator
cd CloudPhotoMigrator
```

- **Windows (Command Prompt):**

```cmd
powershell -Command "Expand-Archive -Path CloudPhotoMigrator_v3.1.0-beta1_docker.zip -DestinationPath CloudPhotoMigrator"
cd CloudPhotoMigrator
```

---

### 3. Edit the configuration

Open `Config.ini` in any text editor and update it with your credentials and settings.

> For more information, refer to the `docs/` and `help/` folders.

---

### 4. Run the tool

Make sure Docker is running, then:

- **Linux/macOS:**

```bash
./CloudPhotoMigrator.sh [options]
```

- **Windows (Command Prompt):**

```cmd
CloudPhotoMigrator.bat [options]
```

You can also run the help command:

```bash
./CloudPhotoMigrator.sh -h
```

or

```cmd
CloudPhotoMigrator.bat -h
```

---

# Instructions to execute from source repository:

> [!IMPORTANT]  
> ### ✅ Prerequisites
> You have to make sure that you have Python 3.8 or higher on your system before to do the following steps.

Here are simple instructions to clone the GitHub repository, create a Python virtual environment, install dependencies, and run the main script.  

Find below the needed steps:

1. Clone the repository
   ```
   git clone https://github.com/jaimetur/CloudPhotoMigrator.git
   ```

2. Change directory to the cloned repository
   ```
   cd CloudPhotoMigrator
   ```

3. Create a Python virtual environment:  
   ```
   python3 -m venv venv
   ```

4. Activate the virtual environment:  
   - On macOS/Linux:  
     ```
     source venv/bin/activate
     ```
   - On Windows (Command Prompt):  
     ```
     venv\Scripts\activate
     ```
   - On Windows (PowerShell):  
     ```
     venv\Scripts\Activate.ps1
     ```

5. Install dependencies:  
   ```
   pip3 install -r requirements.txt
   ```

6. Run the main script to show the command line help:  
   ```
   python3 ./src/CloudPhotoMigrator.py -h
   ```

---


## Notes

- If `Config.ini` is missing, the tool will automatically create a default one and ask you to edit it before continuing.
- The required Docker image is pulled the first time you run the script.

---

## Requirements

- [Docker](https://www.docker.com/products/docker-desktop) must be installed and running.
