# 🐍 How to Install Python 3.11 on Windows, Linux, and macOS

## 🪟 Windows (via Command Line)

Open PowerShell as Administrator (press `Win + X` and choose "Windows PowerShell (Admin)"). Then run the following commands:

```
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" -OutFile "$env:TEMP\python-3.11.7-amd64.exe"
Start-Process -FilePath "$env:TEMP\python-3.11.7-amd64.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
python --version
```

✅ If you see something like `Python 3.11.x`, Python is successfully installed.

---

## 🐧 Linux (Debian/Ubuntu)

Open a terminal and run:

```
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
python3.11 --version
```

📌 You can make Python 3.11 your default with:

```
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
```

---

## 🍎 macOS

### Option 1: Homebrew (recommended)

Open Terminal and run:

```
brew update
brew install python@3.11
brew link --overwrite python@3.11 --force
python3.11 --version
```

📌 You can alias it to `python`:

```
echo 'alias python=python3.11' >> ~/.zshrc && source ~/.zshrc
```

---

## 🛠️ Optional: Set Up pip (if not already installed)

Check pip version:

```
python -m pip --version
```

If not installed, run:

```
python -m ensurepip --upgrade
```

You're all set! 🚀

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 