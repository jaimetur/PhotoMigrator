# Execution from Compiled Binaries \(easiest way)

### 📥 1. Copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

### 📝 2. Edit the configuration file:

Open the file `Config.ini` included in the package with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](../00-configuration-file.md) .

### 🚀 3. Execute the Tool depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**PhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**PhotoMigrator.run**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

### 🖥️ 4. Launch the interactive CLI TUI:
  - Windows:
    ```powershell
    .\\PhotoMigrator.exe
    ```
  - Linux / macOS / Synology SSH:
    ```bash
    ./PhotoMigrator.run
    ```

You can also force the terminal UI explicitly with:

```bash
PhotoMigrator --tui
```

Notes:
- The CLI TUI is shown automatically when the binary is launched without arguments in a compatible interactive terminal.
- If the terminal does not support the required interactive features, PhotoMigrator falls back to the previous legacy GUI/console flow.

---

## 🏠 [Back to Main Page](../../README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span> 
