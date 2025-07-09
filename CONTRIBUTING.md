# 🤝 Contributing to PhotoMigrator

First of all, **thank you** for considering contributing to **PhotoMigrator** — your help makes the project better for everyone! 🚀

Whether you want to fix a bug, suggest a feature, improve documentation, or just report an issue, this guide will help you get started.

---

## 🧭 How to contribute

### 1. **Check for open issues**
Before starting anything, take a look at the [Issues](https://github.com/jaimetur/PhotoMigrator/issues) tab to see if your idea or bug has already been reported.

If it hasn’t, feel free to [open a new issue](https://github.com/jaimetur/PhotoMigrator/issues/new/choose).

---

### 2. **Fork the repository**
Click the **Fork** button at the top right of the repository, then:

```bash
git clone https://github.com/jaimetur/PhotoMigrator.git
cd PhotoMigrator
```

---

### 3. **Create a new branch**
```bash
git checkout -b your-feature-name
```

Use a descriptive name like `fix-date-parsing` or `add-logging-option`.

---

### 4. **Make your changes**
Please keep your changes focused and well-structured. Add comments when needed and make sure your code follows the existing style.

If you’re adding a feature or fixing a bug, write or update unit tests if applicable.

---

### 5. **Test your changes**
Make sure everything works as expected by running:

```bash
python -m unittest
```

Or use the existing testing instructions (coming soon in `/tests`).

---

### 6. **Commit and push**
```bash
git add .
git commit -m "✨ Add X feature"  # Use descriptive commit messages
git push origin your-feature-name
```

---

### 7. **Open a Pull Request**
Go to your fork on GitHub and click **“Compare & pull request”**. Add a clear description of:
- What you changed and why
- Any related issues (use `Closes #123`)
- Screenshots or logs if helpful

---

## 🧪 Local development setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional tools:
- `black` for formatting
- `flake8` for linting

---

## ✅ Contribution tips

- Keep pull requests small and focused
- Write clear commit messages
- Be respectful and open to feedback
- Ask in `#contributing-chat` on Discord if you're unsure

---

## 💙 Thank you!

Whether it's fixing a typo or building a major feature — your help means a lot. Let's make **PhotoMigrator** better together!
