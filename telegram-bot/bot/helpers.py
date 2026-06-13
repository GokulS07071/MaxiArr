import io
import re
import html
import logging
import socket
import ipaddress
from urllib.parse import urlparse
import httpx
from bot.config import SONARR_URL, RADARR_URL, SONARR_API_KEY, RADARR_API_KEY

logger = logging.getLogger("telegram_bot.helpers")

# Trusted domains for remote media/image lookups
TRUSTED_IMAGE_DOMAINS = [
    "tmdb.org",
    "thetvdb.com",
    "placeholder.com",
    "unsplash.com"
]

def escape(text) -> str:
    """Escape dynamic string variables to be safe for Telegram HTML parse mode."""
    return html.escape(str(text)) if text else ""

def get_poster_url(item: dict) -> str:
    """Retrieve poster cover image URL from item metadata, falling back to a placeholder."""
    for img in item.get("images", []):
        url = img.get("remoteUrl") or img.get("url", "")
        if url:
            return url
    return "https://via.placeholder.com/500x750.png?text=No+Poster"

def make_progress_bar(percentage: float, width: int = 10) -> str:
    """Create a textual progress bar."""
    filled = int(round(percentage / 100.0 * width))
    return "█" * filled + "░" * (width - filled)

def format_timeleft(time_str: str) -> str:
    """Parse timeleft format (d.hh:mm:ss or hh:mm:ss) into a human-readable display like '3d 15h 41m'."""
    if not time_str or time_str == "unknown" or time_str == "00:00:00":
        return "N/A"
        
    # Pattern 1: days.hours:minutes:seconds (e.g., 3.15:41:46)
    match_days = re.match(r"^(\d+)\.(\d{1,2}):(\d{2}):(\d{2})$", time_str)
    if match_days:
        d = int(match_days.group(1))
        h = int(match_days.group(2))
        m = int(match_days.group(3))
        return f"{d}d {h}h {m}m"
        
    # Pattern 2: hours:minutes:seconds (e.g., 15:41:46 or 00:04:12)
    match_hours = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})$", time_str)
    if match_hours:
        h = int(match_hours.group(1))
        m = int(match_hours.group(2))
        s = int(match_hours.group(3))
        if h > 0:
            return f"{h}h {m}m"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"
            
    return time_str

def _is_ip_private(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or link-local."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False

def _validate_domain_and_prevent_ssrf(url: str, trusted_urls: list[str]) -> bool:
    """Ensure the URL target is not on a private network, and check domain whitelist."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return False
        
    # 1. Bypass check if host matches one of our explicitly trusted local client API endpoints
    for trusted_url in trusted_urls:
        if trusted_url:
            trusted_parsed = urlparse(trusted_url)
            if trusted_parsed.hostname == host and trusted_parsed.port == parsed.port:
                return True
                
    # 2. Prevent SSRF by validating that hostname itself is not a private IP
    if _is_ip_private(host):
        logger.warning(f"SSRF prevention triggered: {host} is a private IP.")
        return False
        
    # 3. Resolve hostname and verify that none of the resolved IPs are private/loopback
    try:
        addr_info = socket.getaddrinfo(host, None)
        for _, _, _, _, sockaddr in addr_info:
            ip = sockaddr[0]
            if _is_ip_private(ip):
                logger.warning(f"SSRF prevention triggered: {host} resolves to private IP {ip}.")
                return False
    except socket.gaierror:
        logger.warning(f"Failed to resolve host {host} for SSRF validation.")
        return False
        
    # 4. Check domain suffix whitelist
    host_lower = host.lower()
    for domain in TRUSTED_IMAGE_DOMAINS:
        if host_lower == domain or host_lower.endswith("." + domain):
            return True
            
    logger.warning(f"Rejected image download: domain '{host}' is not in the trusted whitelist.")
    return False

async def download_image_bytes(url: str, app_type: str = None) -> io.BytesIO | None:
    """Download image files from remote web URLs or local relative API endpoints into memory bytes."""
    if not url:
        return None
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Resolve relative URL to absolute endpoint using local URLs
    if url.startswith("/"):
        if app_type == "movie":
            url = f"{RADARR_URL}{url}"
            headers["X-Api-Key"] = RADARR_API_KEY
        elif app_type == "series":
            url = f"{SONARR_URL}{url}"
            headers["X-Api-Key"] = SONARR_API_KEY
        else:
            return None

    # Perform SSRF and domain validation on the final URL
    trusted_endpoints = [RADARR_URL, SONARR_URL]
    if not _validate_domain_and_prevent_ssrf(url, trusted_endpoints):
        logger.error(f"Image download URL validation failed: {url}")
        return None
            
    try:
        logger.info(f"Downloading image bytes from: {url}")
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type or url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    bio = io.BytesIO(response.content)
                    bio.name = "poster.jpg"
                    return bio
            logger.warning(f"Download failed: HTTP status {response.status_code} for {url}")
    except Exception as e:
        logger.error(f"Error downloading image bytes: {e}")
    return None
