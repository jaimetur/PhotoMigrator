# 🐳 Install Docker on Windows Using PowerShell

This guide explains how to install Docker Desktop on Windows using PowerShell.

## ✅ Prerequisites

- **Windows 10 or 11** (64-bit), version 1903 or higher.
- **WSL 2** or **Hyper-V** enabled.
- **Virtualization** must be enabled in BIOS.

## 📥 Step 1: Open PowerShell as Administrator

Right-click the Start menu and select **“Windows PowerShell (Admin)”**.

## 🌐 Step 2: Download the Docker Desktop Installer

Run the following command in PowerShell to download the latest Docker Desktop installer:

```powershell
Invoke-WebRequest -UseBasicParsing -OutFile "DockerDesktopInstaller.exe" -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
```

## 🛠️ Step 3: Run the Installer

Once downloaded, start the installer:

```powershell
Start-Process ".\DockerDesktopInstaller.exe" -Wait
```

This will launch the Docker Desktop graphical setup wizard. Follow the instructions.  
It is recommended to leave the **WSL 2 backend** option enabled if available.

## 🔄 Step 4: Reboot (If Required)

After installation, you may be prompted to restart your computer. Do so if necessary.

## ✅ Step 5: Verify Docker Installation

After rebooting, open a new PowerShell window and check that Docker is installed:

```powershell
docker --version
```

You can also test Docker with:

```powershell
docker run hello-world
```

---

## 💡 Optional: Enable WSL 2 (If Not Already Enabled)

To enable WSL 2 support, run the following command:

```powershell
wsl --install
```

Or follow the manual instructions in the official guide:  
👉 [WSL Installation Guide](https://docs.microsoft.com/en-us/windows/wsl/install)

---

## 🐧 Notes

- Docker Desktop requires either **WSL 2** or **Hyper-V** to run.
- You may need to log in with a Docker Hub account after installation.

---

## [[🏠 Back to Main Page](https://github.com/jaimetur/PhotoMigrator/tree/main)](https://github.com/jaimetur/PhotoMigrator/tree/main)



---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span> 