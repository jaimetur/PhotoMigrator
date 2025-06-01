# 📦 How to Install Git on Windows, Linux, and macOS

## 🪟 Windows (via Command Line)

Open PowerShell as Administrator (press `Win + X` and choose "Windows PowerShell (Admin)"). Then run the following commands:

```
Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe" -OutFile "$env:TEMP\Git-Installer.exe"
Start-Process -FilePath "$env:TEMP\Git-Installer.exe" -ArgumentList "/VERYSILENT" -Wait
git --version
```

✅ If you see something like `git version 2.x.x`, Git is successfully installed.

---

## 🐧 Linux (Debian/Ubuntu)

Open a terminal and run:

```
sudo apt update
sudo apt install git
git --version
```

📌 For other distributions:  
Fedora: `sudo dnf install git`  
Arch Linux: `sudo pacman -S git`

---

## 🍎 macOS

### Option 1: Xcode Command Line Tools (recommended)

Open Terminal and run:

```
git --version
```

If Git is not installed, macOS will prompt you to install the Command Line Tools. Click "Install" and wait for it to finish.

### Option 2: Homebrew (if you have Homebrew installed)

```
brew update
brew install git
git --version
```

---

## 🛠️ Basic Git Configuration (recommended)

```
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

You’re all set! 🚀

---

## [[🏠 Back to Main Page](https://github.com/jaimetur/PhotoMigrator/tree/main)](https://github.com/jaimetur/PhotoMigrator/tree/main)


---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 