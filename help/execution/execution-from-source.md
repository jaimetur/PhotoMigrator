# Execution from Source Repository

> [!IMPORTANT]  
> ### ✅ Prerequisites:
> - You have to make sure that you have the following tools instaled on your system:
>   - Python 3.8 or higher - [Install Instructions](https://github.com/jaimetur/PhotoMigrator/blob/main/help/install-python/install-python.md)
>   - Git - [Install Instructions](https://github.com/jaimetur/PhotoMigrator/blob/main/help/install-git/install-git.md)

Here are simple instructions to clone the GitHub repository, create a Python virtual environment, install dependencies, and run the main script.  

Find below the needed steps:

### 🔗 1. Clone the repository
   ```bash
   git clone https://github.com/jaimetur/PhotoMigrator.git
   ```

### 📂 2. Change directory to the cloned repository
   ```bash
   cd PhotoMigrator
   ```

### 🐍 3. Create a Python virtual environment:  
   ```bash
   python3 -m venv venv
   ```

### 🐍 4. Activate the virtual environment:  
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


### 📦 5. Install dependencies:  
   ```bash
   pip3 install -r requirements.txt
   ```


### 📝 6. Edit the configuration file:

Open the file `Config.ini` included in the package with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md).


### 🚀 7. Run the Tool to show the command line help:
   ```bash
   python3 ./src/PhotoMigrator.py -h
   ```

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 