# MaxiArr: Homelab Media Stack with AllDebrid Automation

A self-contained Docker Compose media stack for automated media management using **AllDebrid** (via **RDT-Client**) as the primary downloader, alongside **Sonarr**, **Radarr**, and **Prowlarr**. It also includes an optional **qBittorrent** client routed through **Gluetun VPN** for traditional torrent downloads.

---

## 1. Quick Start

### Step 1: Bootstrap Folder Layout
Run the appropriate bootstrap script for your operating system to automatically create the required directory structure:

*   **Windows (Command Prompt/PowerShell)**:
    ```cmd
    setup.bat
    ```
*   **Linux / macOS / WSL (Bash)**:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```

This will bootstrap the following folder layout relative to your workspace root:

```
├── config/
│   ├── gluetun/
│   ├── prowlarr/
│   ├── qbittorrent/
│   ├── radarr/
│   ├── rdtclient/
│   ├── seerr/
│   └── sonarr/
└── data/
    ├── downloads/
    │   ├── rdt/
    │   │   ├── radarr/
    │   │   └── sonarr/
    │   └── torrents/
    └── media/
        ├── movies/
        └── tv/
```

### Step 2: Start the Containers
*   **To run the primary AllDebrid stack (Sonarr, Radarr, Prowlarr, RDT-Client)**:
    ```bash
    docker compose up -d
    ```
*   **To run the optional traditional torrent client behind VPN (Gluetun + qBittorrent)**:
    1. Open your `.env` or `docker-compose.yml` and configure your VPN details in the `gluetun` service environment block.
    2. Start the stack with the profile:
       ```bash
       docker compose --profile torrent-vpn up -d
       ```

---

## 2. Web UI Directory

Once running, access the UIs from your local machine:

| App | Host Port | Internal Port | URL |
| :--- | :--- | :--- | :--- |
| **Sonarr** | `8989` | `8989` | [http://localhost:8989](http://localhost:8989) |
| **Radarr** | `7878` | `7878` | [http://localhost:7878](http://localhost:7878) |
| **Prowlarr** | `9696` | `9696` | [http://localhost:9696](http://localhost:9696) |
| **RDT-Client** | `6500` | `6500` | [http://localhost:6500](http://localhost:6500) |
| **Seerr** | `5055` | `5055` | [http://localhost:5055](http://localhost:5055) |
| **qBittorrent** *(Optional)* | `8080` (Via Gluetun) | `8080` | [http://localhost:8080](http://localhost:8080) |

> [!NOTE]
> If you start `qbittorrent` for the first time, check the container logs to find the temporary Web UI password:
> ```bash
> docker logs qbittorrent
> ```

---

## 3. Step-by-Step Configuration

### A. RDT-Client Setup (AllDebrid Bridge)
RDT-Client acts as a fake qBittorrent client. Sonarr/Radarr add torrents to RDT-Client via standard torrent APIs, and RDT-Client feeds them to AllDebrid, downloads the completed files locally, and informs Sonarr/Radarr.

1. Open [http://localhost:6500](http://localhost:6500).
2. Go to **Settings > Provider**.
3. Select **AllDebrid** as your provider and paste your **AllDebrid API Key**. Save settings.
4. Go to **Settings > General** or **Download Client**:
   *   **Download Path**: `/data/downloads/rdt`
   *   **Mapped Path**: `/data/downloads/rdt`
5. Enable the **qBittorrent-compatible API** (it is typically enabled by default on port `6500`).
6. Set up a Web UI username and password under RDT-Client credentials for security.

---

### B. Prowlarr Setup (Indexer Manager)
Prowlarr coordinates tracker indexers and pushes them to Sonarr and Radarr. The API keys are automatically set at startup based on your `.env` configuration.

1. Open [http://localhost:9696](http://localhost:9696).
2. Go to **Settings > Apps** and click the **(+)** button.
3. Select **Sonarr**:
   *   **Prowlarr Server**: `http://prowlarr:9696`
   *   **Sonarr Server**: `http://sonarr:8989`
   *   **API Key**: Use the value of `SONARR_API_KEY` configured in your `.env` file.
   *   **Sync Level**: `Full Sync` or `Add and Remove Only`.
   *   Click **Test**, then **Save**.
4. Repeat the same step for **Radarr**:
   *   **Prowlarr Server**: `http://prowlarr:9696`
   *   **Radarr Server**: `http://radarr:7878`
   *   **API Key**: Use the value of `RADARR_API_KEY` configured in your `.env` file.
   *   Click **Test**, then **Save**.
5. Go to **Indexers**, click **Add New**, select your preferred authorized/public trackers, and Prowlarr will automatically sync them to both Sonarr and Radarr.

---

### C. Sonarr Setup
1. Open [http://localhost:8989](http://localhost:8989).
2. Go to **Settings > Media Management**:
   *   Click **Add Root Folder** and select `/data/media/tv`.
   *   Toggle **Advanced Settings** (top) to *Shown*.
   *   Ensure **Use Hardlinks instead of Copy** is enabled.
3. Go to **Settings > Download Clients** and click **(+)**:
   *   Select **qBittorrent** (since RDT-Client emulates it).
   *   **Name**: `RDT Client`
   *   **Host**: `rdtclient` *(Docker service name resolver)*
   *   **Port**: `6500`
   *   **Username**: *(Your RDT-Client Web UI username)*
   *   **Password**: *(Your RDT-Client Web UI password)*
   *   **Category**: `sonarr`
   *   Click **Test** and **Save**.

---

### D. Radarr Setup
1. Open [http://localhost:7878](http://localhost:7878).
2. Go to **Settings > Media Management**:
   *   Click **Add Root Folder** and select `/data/media/movies`.
   *   Ensure **Use Hardlinks instead of Copy** is enabled.
3. Go to **Settings > Download Clients** and click **(+)**:
   *   Select **qBittorrent**.
   *   **Name**: `RDT Client`
   *   **Host**: `rdtclient`
   *   **Port**: `6500`
   *   **Username**: *(Your RDT-Client Web UI username)*
   *   **Password**: *(Your RDT-Client Web UI password)*
   *   **Category**: `radarr`
   *   Click **Test** and **Save**.

---

### E. Optional: Traditional Torrent Client (qBittorrent via Gluetun)
If you also want a normal client for direct torrenting through VPN:

1. In the qBittorrent Web UI, set the default save path to `/data/downloads/torrents`.
2. In Sonarr and Radarr, add another Download Client:
   *   Select **qBittorrent**.
   *   **Name**: `qBittorrent VPN`
   *   **Host**: `gluetun` *(Because qBittorrent shares Gluetun's network workspace)*
   *   **Port**: `8080`
   *   **Category**: `sonarr` or `radarr`
   *   Click **Test** and **Save**.

---

### F. Optional: Telegram Media Assistant Bot
You can search and add media to Sonarr and Radarr, plus monitor active download queues, directly from Telegram:

1. Open Telegram and message [@BotFather](https://t.me/BotFather) to create a new bot and get an API Token.
2. In your `.env` file, set `TELEGRAM_BOT_TOKEN=your_token_here`.
3. Rebuild and start the bot service:
   ```bash
   docker compose up -d --build telegram-bot
   ```
4. Find your bot in Telegram, click **Start**, and send your search queries!

For more details on local configuration, manual testing, and command list, see the [Telegram Bot README](file:///f:/Projects/Personal/MaxiArr/telegram-bot/README.md).

---

### G. Seerr Setup (Request & Discovery Manager)
Seerr is the unified successor to Overseerr and Jellyseerr. It allows users to browse and request movies and TV shows, which are automatically sent to Sonarr/Radarr.

1. Open [http://localhost:5055](http://localhost:5055).
2. Choose to sign in using your **Plex account** or create a local **Seerr account**.
3. During setup, configure your media library connections (Plex, Jellyfin, or Emby) if applicable.
4. Add **Radarr** and **Sonarr** services under **Settings > Services**:
   *   Click **Add Service**.
   *   Select **Radarr**:
       *   **Hostname/IP**: `radarr` (using Docker DNS resolver)
       *   **Port**: `7878`
       *   **API Key**: Use the value of `RADARR_API_KEY` from your `.env` file.
       *   Click **Test** and **Save**.
   *   Select **Sonarr**:
       *   **Hostname/IP**: `sonarr`
       *   **Port**: `8989`
       *   **API Key**: Use the value of `SONARR_API_KEY` from your `.env` file.
       *   Click **Test** and **Save**.

---

## 4. Troubleshooting & Zero-Copy Hardlinks
*   **Path Mapping issues**: By using a single root mount `- ./data:/data` across Sonarr, Radarr, and RDT-Client, the containers share a unified view of the files. Downloads go to `/data/downloads/rdt` and media goes to `/data/media/tv`. Since they belong to the same mount point, Sonarr and Radarr can perform instant hardlinks or atomic moves without generating file copies or wearing down SSD write limits.
*   **Check logs**:
    ```bash
    docker compose logs -f sonarr
    docker compose logs -f rdtclient
    ```
