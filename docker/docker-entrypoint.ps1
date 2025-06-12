# Variables de ruta
$DOCKER_CONF_FILE = "C:\docker\docker.conf"
$DEFAULT_DOCKER_CONF_FILE = "C:\app\default_docker.conf"

$CONFIG_FILE = "C:\docker\Config.ini"
$DEFAULT_CONFIG = "C:\app\default_config.ini"

# Modo interactivo
if ($args.Count -ge 1 -and $args[0] -eq "bash") {
    Write-Host "🔧 Entering interactive shell..."
    cmd.exe
    exit
}

# Verificar existencia de docker.conf
if (-Not (Test-Path $DOCKER_CONF_FILE)) {
    Write-Host "❌ docker.conf not found in the current folder."
    Write-Host "Creating a default docker.conf file..."
    Copy-Item $DEFAULT_DOCKER_CONF_FILE $DOCKER_CONF_FILE
}

Write-Host "🚀 Initializing container and launching PhotoMigrator..."

# Validar Config.ini
Write-Host "Looking for: Config.ini"
if (-Not (Test-Path $CONFIG_FILE)) {
    Write-Host "❌ Config.ini not found in the current folder."
    Write-Host "Creating a default configuration file..."
    Copy-Item $DEFAULT_CONFIG $CONFIG_FILE
    Write-Host "Please edit Config.ini with your settings and run the script again."
    exit 1
}

# Ejecutar el script principal
Write-Host "▶️ Launching: PhotoMigrator.py" $args
python C:\app\src\PhotoMigrator.py @args
