# 🐧 Install Docker Engine on Linux (Debian/Ubuntu)

This guide explains how to install Docker Engine on a Debian-based Linux system such as Ubuntu using the terminal.

> [!WARNING]
> ⚠️ **Run all commands as root** or prepend `sudo` to each one.

## ✅ Step 1: Update the Package Index

```bash
sudo apt-get update
```

## 📦 Step 2: Install Required Packages

```bash
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

## 🔐 Step 3: Add Docker’s Official GPG Key

```bash
sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

## 📁 Step 4: Set Up the Docker Repository

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

## 🔄 Step 5: Update the Package Index (Again)

```bash
sudo apt-get update
```

## 🐳 Step 6: Install Docker Engine

```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 🚀 Step 7: Test the Docker Installation

```bash
sudo docker run hello-world
```

If you see a welcome message from Docker, it means everything is working correctly.

---

## 👤 Optional: Run Docker as a Non-root User

To use Docker without `sudo`:

```bash
sudo usermod -aG docker $USER
```

Then **log out and log back in**, or run:

```bash
newgrp docker
```

Test it:

```bash
docker run hello-world
```

---

## 🧼 Optional: Enable Docker to Start on Boot

```bash
sudo systemctl enable docker
```

---

## 📄 More Info

Official docs:  
👉 [https://docs.docker.com/engine/install/ubuntu/](https://docs.docker.com/engine/install/ubuntu/)

---

## 🏠 [Back to Main Page](/README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span> 