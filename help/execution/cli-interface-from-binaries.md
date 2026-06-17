# Execution from Compiled Binaries \(easiest way)

### 📥 1. Copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

### 📝 2. Edit the configuration file:

Open the file `Config.ini` included in the package with any text editor and update it with your credentials and settings.

> For more information, refer to [Configuration File](../00-configuration-file.md) .

### 🚀 3. Execute the Tool depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**PhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux, you have to call the downloaded binary using its full versioned name, for example '**PhotoMigrator_vx.y.z_linux_x64.bin**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

  - If you run it from macOS, you have to call the downloaded binary using its full versioned name, for example '**PhotoMigrator_vx.y.z_macos_arm64.command**'.

### 🖥️ 4. Launch the default interactive UI:
  - Windows:
    ```powershell
    .\\PhotoMigrator.exe
    ```
  - Linux / Synology SSH:
    ```bash
    ./PhotoMigrator_vx.y.z_linux_x64.bin
    ```
  - macOS:
    ```bash
    chmod +x ./PhotoMigrator_vx.y.z_macos_arm64.command
    xattr -dr com.apple.quarantine ./PhotoMigrator_vx.y.z_macos_arm64.command
    ./PhotoMigrator_vx.y.z_macos_arm64.command
    ```

### 🍎 5. macOS first-launch note
If macOS shows a warning such as "Apple cannot check it for malicious software", remove the downloaded quarantine attribute before the first execution:

```bash
chmod +x ./PhotoMigrator_vx.y.z_macos_arm64.command
xattr -dr com.apple.quarantine ./PhotoMigrator_vx.y.z_macos_arm64.command
./PhotoMigrator_vx.y.z_macos_arm64.command
```
Replace `x.y.z` and the architecture suffix with the exact file name you downloaded from the release page.

After that first unblock, you can execute the same `.command` file from Terminal or launch it directly from Finder.

This now opens the desktop GUI by default when a graphical environment with `tkinter` is available.

By default, the interactive interfaces use `./Config.ini` from the folder where you execute the binary.

You can force the terminal UI explicitly with:

```bash
./PhotoMigrator_vx.y.z_macos_arm64.command --tui   # macOS
./PhotoMigrator_vx.y.z_linux_x64.bin --tui         # Linux / Synology SSH
```

Or launch the desktop GUI explicitly with:

```bash
./PhotoMigrator_vx.y.z_macos_arm64.command --gui   # macOS
./PhotoMigrator_vx.y.z_linux_x64.bin --gui         # Linux / Synology SSH
```

You can also preload a custom configuration file when launching the interactive interfaces:

```bash
./PhotoMigrator_vx.y.z_macos_arm64.command --gui --configuration-file ./Config.ini   # macOS
./PhotoMigrator_vx.y.z_linux_x64.bin --gui --configuration-file ./Config.ini         # Linux / Synology SSH
./PhotoMigrator_vx.y.z_macos_arm64.command --tui --configuration-file /volume1/shared/PhotoMigrator/custom.ini   # macOS
./PhotoMigrator_vx.y.z_linux_x64.bin --tui --configuration-file /volume1/shared/PhotoMigrator/custom.ini         # Linux / Synology SSH
./PhotoMigrator_vx.y.z_macos_arm64.command --configuration-file ./Config.ini   # macOS
./PhotoMigrator_vx.y.z_linux_x64.bin --configuration-file ./Config.ini         # Linux / Synology SSH
```

In all the examples above, replace `x.y.z` and the architecture suffix with the exact binary name included in the release you downloaded.

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
