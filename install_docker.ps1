$ErrorActionPreference = "Stop"

Write-Host "--- HARDCORE DOCKER INSTALLATION ---"
$installerPath = "D:\recruitment_platform\DockerDesktopInstaller.exe"

if (-not (Test-Path $installerPath)) {
    Write-Host "Downloading Docker Desktop Installer using BITS (Background Intelligent Transfer Service) for max speed & reliability..."
    Import-Module BitsTransfer
    Start-BitsTransfer -Source "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -Destination $installerPath
} else {
    Write-Host "Installer already found at $installerPath"
}

Write-Host "Executing silent installation (this may take a few minutes)..."
$process = Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license" -Wait -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "Docker installed successfully!"
} elseif ($process.ExitCode -eq 3010) {
    Write-Host "Docker installed, but a REBOOT is required!"
} else {
    Write-Host "Installation failed with exit code: $($process.ExitCode)"
}

Write-Host "Starting Docker Engine..."
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

Write-Host "Setup complete. This window will close in 10 seconds."
Start-Sleep -Seconds 10
