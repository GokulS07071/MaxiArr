#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}Creating directory structure for MaxiArr stack...${NC}"

directories=(
    "config/sonarr"
    "config/radarr"
    "config/prowlarr"
    "config/rdtclient"
    "config/qbittorrent"
    "config/gluetun"
    "config/seerr"
    "data/media/movies"
    "data/media/tv"
    "data/downloads/rdt"
    "data/downloads/rdt/radarr"
    "data/downloads/rdt/sonarr"
    "data/downloads/torrents"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "  ${GREEN}[Created]${NC} $dir"
    else
        echo -e "  ${YELLOW}[Exists]${NC}  $dir"
    fi
done

# If running as root (e.g., via sudo), adjust ownership of all directories to PUID:PGID from .env
if [ "$(id -u)" -eq 0 ]; then
    puid=$(grep -E "^PUID=" .env | cut -d= -f2 | tr -d '\r')
    pgid=$(grep -E "^PGID=" .env | cut -d= -f2 | tr -d '\r')
    puid=${puid:-${SUDO_UID:-1000}}
    pgid=${pgid:-${SUDO_GID:-1000}}
    
    echo -e "\n${YELLOW}Adjusting ownership of directories to $puid:$pgid...${NC}"
    for dir in "${directories[@]}"; do
        if [ -d "$dir" ]; then
            chown -R "$puid:$pgid" "$dir"
        fi
    done
else
    # Check if any directories are not writable by the current user
    non_writable=()
    for dir in "${directories[@]}"; do
        if [ -d "$dir" ] && [ ! -w "$dir" ]; then
            non_writable+=("$dir")
        fi
    done

    if [ ${#non_writable[@]} -ne 0 ]; then
        echo -e "\n${YELLOW}Warning: The following directories are not writable by the current user:${NC}"
        for dir in "${non_writable[@]}"; do
            echo -e "  - $dir"
        done
        echo -e "${YELLOW}Please run the script with sudo (e.g., 'sudo ./setup.sh') to fix ownership.${NC}"
    fi
fi

echo -e "\n${GREEN}Folder setup completed successfully!${NC}"
echo -e "${CYAN}You can now run: docker compose up -d${NC}"
