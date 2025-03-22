# 🍎 Install Docker Desktop on macOS

This guide explains how to install Docker Desktop on macOS using the terminal and the graphical installer.

## ✅ Requirements

- **macOS 11 (Big Sur)** or later.
- A Mac with **Intel** or **Apple Silicon (M1/M2)**.
- **Virtualization** must be enabled (by default it is).
- Optional but recommended: **Homebrew** installed.

---

## 📦 Step 1: Install Docker Desktop via Homebrew (Recommended)

If you have [Homebrew](https://brew.sh) installed, you can install Docker Desktop with:

```bash
brew install --cask docker
```

After installation, launch Docker Desktop from the Applications folder or with:

```bash
open -a Docker
```

> 🕒 Wait until the Docker whale icon in the menu bar finishes loading — it may take a few seconds the first time.

---

## 💡 Alternative: Manual Download

If you prefer not to use Homebrew, download the installer manually:

👉 [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

1. Download the `.dmg` file for your architecture (Intel or Apple Silicon).
2. Open the `.dmg` and drag Docker to the **Applications** folder.
3. Open Docker from **Applications**.

---

## ✅ Step 2: Verify Installation

Once Docker is running, verify it's working with:

```bash
docker --version
```

And test it:

```bash
docker run hello-world
```

You should see a success message from Docker.

---

## 👤 Optional: Start Docker Automatically on Login

In Docker Desktop settings, enable **"Start Docker Desktop when you log in"**.

---

## 📄 More Info

Official Docker Desktop for Mac documentation:  
👉 [https://docs.docker.com/desktop/install/mac-install/](https://docs.docker.com/desktop/install/mac-install/)
