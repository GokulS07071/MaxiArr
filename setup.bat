@echo off
SETLOCAL EnableExtensions

echo Creating directory structure for MaxiArr stack...

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

for %%d in (
    "config\sonarr"
    "config\radarr"
    "config\prowlarr"
    "config\rdtclient"
    "config\qbittorrent"
    "config\gluetun"
    "config\seerr"
    "data\media\movies"
    "data\media\tv"
    "data\downloads\rdt"
    "data\downloads\rdt\radarr"
    "data\downloads\rdt\sonarr"
    "data\downloads\torrents"
) do (
    if not exist "%%~d" (
        mkdir "%%~d"
        echo   [Created] %%~d
    ) else (
        echo   [Exists]  %%~d
    )
)

echo.
echo Folder setup completed successfully!
echo You can now run: docker compose up -d
