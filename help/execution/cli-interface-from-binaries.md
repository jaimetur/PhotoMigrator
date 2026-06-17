# Execution from Compiled Binaries \(easiest way)

### 📥 1. Copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

### 📝 2. Edit the configuration file:

Open the file `Config.ini` included in the package with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](../00-configuration-file.md) .

### 🚀 3. Execute the Tool depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**PhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**PhotoMigrator.run**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

### 🖥️ 4. Launch the default interactive UI:
  - Windows:
    ```powershell
    .\\PhotoMigrator.exe
    ```
  - Linux / macOS / Synology SSH:
    ```bash
    ./PhotoMigrator.run
    ```

This now opens the desktop GUI by default when a graphical environment with `tkinter` is available.

By default, the interactive interfaces use `./Config.ini` from the folder where you execute the binary.

You can force the terminal UI explicitly with:

```bash
PhotoMigrator --tui
```

Or launch the desktop GUI explicitly with:

```bash
PhotoMigrator --gui
```

You can also preload a custom configuration file when launching the interactive interfaces:

```bash
PhotoMigrator --gui --configuration-file ./Config.ini
PhotoMigrator --tui --configuration-file /volume1/shared/PhotoMigrator/custom.ini
PhotoMigrator --configuration-file ./Config.ini
```

Notes:
- The desktop GUI is now the first launcher option when the binary is started without arguments.
- If `tkinter` or a graphical display is not available, PhotoMigrator falls back to the CLI TUI on compatible interactive terminals.
- If neither interactive UI can be started, PhotoMigrator falls back to the same output as `--help`.

---

## 🏠 [Back to Main Page](../../README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span> 
