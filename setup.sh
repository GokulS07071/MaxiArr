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
    "data/media/movies"
    "data/media/tv"
    "data/downloads/rdt"
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

echo -e "\n${GREEN}Folder setup completed successfully!${NC}"
echo -e "${CYAN}You can now run: docker compose up -d${NC}"
