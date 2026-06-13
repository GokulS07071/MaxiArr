import logging

import httpx

logger = logging.getLogger("telegram_bot.agent")


class MediaAgent:
    def __init__(self, sonarr_url: str, sonarr_api_key: str, radarr_url: str, radarr_api_key: str):
        self.sonarr_url = sonarr_url.rstrip("/")
        self.sonarr_api_key = sonarr_api_key
        self.radarr_url = radarr_url.rstrip("/")
        self.radarr_api_key = radarr_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    # --- RADARR (Movies) ---

    async def search_movie(self, term: str) -> list[dict]:
        """Search for a movie in Radarr's catalog (lookup)."""
        url = f"{self.radarr_url}/api/v3/movie/lookup"
        headers = {"X-Api-Key": self.radarr_api_key}
        params = {"term": term}
        try:
            logger.info(f"Searching Radarr for: {term}")
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching Radarr: {e}")
            return []

    async def get_radarr_quality_profiles(self) -> list[dict]:
        """Get quality profiles configured in Radarr."""
        url = f"{self.radarr_url}/api/v3/qualityprofile"
        headers = {"X-Api-Key": self.radarr_api_key}
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return [{"id": p["id"], "name": p["name"]} for p in response.json()]
        except Exception as e:
            logger.error(f"Error getting Radarr quality profiles: {e}")
            return []

    async def _get_radarr_root_folder(self) -> str | None:
        url = f"{self.radarr_url}/api/v3/rootfolder"
        headers = {"X-Api-Key": self.radarr_api_key}
        try:
            res = await self.client.get(url, headers=headers)
            res.raise_for_status()
            folders = res.json()
            if folders:
                return folders[0]["path"]
        except Exception as e:
            logger.error(f"Error getting Radarr root folders: {e}")
        return None

    async def add_movie(self, movie_data: dict, quality_profile_id: int) -> tuple[bool, int | None, str]:
        """Add a movie to Radarr library."""
        root_folder = await self._get_radarr_root_folder()
        if not root_folder:
            return (
                False,
                None,
                "Could not resolve Radarr root folder. Check your settings.",
            )

        url = f"{self.radarr_url}/api/v3/movie"
        headers = {"X-Api-Key": self.radarr_api_key}

        # Check if movie already exists
        existing_movie = await self.find_existing_movie(movie_data.get("tmdbId"))
        if existing_movie:
            return (
                True,
                existing_movie.get("id"),
                f"Movie is already in Radarr: '{movie_data.get('title')}'.",
            )

        payload = {
            "title": movie_data.get("title"),
            "tmdbId": movie_data.get("tmdbId"),
            "year": movie_data.get("year"),
            "images": movie_data.get("images", []),
            "titleSlug": movie_data.get("titleSlug"),
            "rootFolderPath": root_folder,
            "qualityProfileId": quality_profile_id,
            "monitored": True,
            "addOptions": {"searchForMovie": False},
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                return True, data.get("id"), f"Added '{movie_data.get('title')}'!"
            else:
                return (
                    False,
                    None,
                    f"Radarr returned status {response.status_code}: {response.text}",
                )
        except Exception as e:
            logger.error(f"Failed to add movie to Radarr: {e}")
            return False, None, f"Failed to add movie: {str(e)}"

    async def find_existing_movie(self, tmdb_id: int) -> dict | None:
        """Find a movie in the existing library by TMDb ID."""
        url = f"{self.radarr_url}/api/v3/movie"
        headers = {"X-Api-Key": self.radarr_api_key}
        try:
            response = await self.client.get(url, headers=headers)
            if response.status_code == 200:
                for movie in response.json():
                    if movie.get("tmdbId") == tmdb_id:
                        return movie
        except Exception as e:
            logger.error(f"Error checking existing movie: {e}")
        return None

    async def get_movie_releases(self, movie_id: int) -> list[dict]:
        """Fetch releases for a movie from indexers."""
        url = f"{self.radarr_url}/api/v3/release"
        headers = {"X-Api-Key": self.radarr_api_key}
        params = {"movieId": movie_id}
        try:
            logger.info(f"Getting movie releases for Radarr ID: {movie_id}")
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting movie releases: {e}")
            return []

    # --- SONARR (TV Shows) ---

    async def search_series(self, term: str) -> list[dict]:
        """Search for a series in Sonarr's catalog (lookup)."""
        url = f"{self.sonarr_url}/api/v3/series/lookup"
        headers = {"X-Api-Key": self.sonarr_api_key}
        params = {"term": term}
        try:
            logger.info(f"Searching Sonarr for: {term}")
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching Sonarr: {e}")
            return []

    async def get_sonarr_quality_profiles(self) -> list[dict]:
        """Get quality profiles configured in Sonarr."""
        url = f"{self.sonarr_url}/api/v3/qualityprofile"
        headers = {"X-Api-Key": self.sonarr_api_key}
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return [{"id": p["id"], "name": p["name"]} for p in response.json()]
        except Exception as e:
            logger.error(f"Error getting Sonarr quality profiles: {e}")
            return []

    async def _get_sonarr_root_folder(self) -> str | None:
        url = f"{self.sonarr_url}/api/v3/rootfolder"
        headers = {"X-Api-Key": self.sonarr_api_key}
        try:
            res = await self.client.get(url, headers=headers)
            res.raise_for_status()
            folders = res.json()
            if folders:
                return folders[0]["path"]
        except Exception as e:
            logger.error(f"Error getting Sonarr root folders: {e}")
        return None

    async def _get_sonarr_language_profile(self) -> int | None:
        url = f"{self.sonarr_url}/api/v3/languageprofile"
        headers = {"X-Api-Key": self.sonarr_api_key}
        try:
            res = await self.client.get(url, headers=headers)
            res.raise_for_status()
            profiles = res.json()
            if profiles:
                return profiles[0]["id"]
        except Exception as e:
            logger.debug(f"Error getting Sonarr language profiles: {e}")
        return None

    async def add_series(self, series_data: dict, quality_profile_id: int) -> tuple[bool, int | None, str]:
        """Add a TV show/series to Sonarr library."""
        root_folder = await self._get_sonarr_root_folder()
        if not root_folder:
            return (
                False,
                None,
                "Could not resolve Sonarr root folder. Check your settings.",
            )

        language_profile_id = await self._get_sonarr_language_profile()
        if not language_profile_id:
            language_profile_id = 1

        url = f"{self.sonarr_url}/api/v3/series"
        headers = {"X-Api-Key": self.sonarr_api_key}

        # Check if series already exists
        existing_series = await self.find_existing_series(series_data.get("tvdbId"))
        if existing_series:
            return (
                True,
                existing_series.get("id"),
                f"Series is already in Sonarr: '{series_data.get('title')}'.",
            )

        payload = {
            "title": series_data.get("title"),
            "tvdbId": series_data.get("tvdbId"),
            "year": series_data.get("year"),
            "images": series_data.get("images", []),
            "titleSlug": series_data.get("titleSlug"),
            "rootFolderPath": root_folder,
            "qualityProfileId": quality_profile_id,
            "languageProfileId": language_profile_id,
            "monitored": True,
            "seasonFolder": True,
            "addOptions": {"searchForMissingEpisodes": False},
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                return True, data.get("id"), f"Added '{series_data.get('title')}'!"
            else:
                return (
                    False,
                    None,
                    f"Sonarr returned status {response.status_code}: {response.text}",
                )
        except Exception as e:
            logger.error(f"Failed to add series to Sonarr: {e}")
            return False, None, f"Failed to add series: {str(e)}"

    async def find_existing_series(self, tvdb_id: int) -> dict | None:
        """Find a series in the existing library by TVDB ID."""
        url = f"{self.sonarr_url}/api/v3/series"
        headers = {"X-Api-Key": self.sonarr_api_key}
        try:
            response = await self.client.get(url, headers=headers)
            if response.status_code == 200:
                for series in response.json():
                    if series.get("tvdbId") == tvdb_id:
                        return series
        except Exception as e:
            logger.error(f"Error checking existing series: {e}")
        return None

    async def get_series_releases(self, series_id: int) -> list[dict]:
        """Fetch releases for a TV series from indexers."""
        url = f"{self.sonarr_url}/api/v3/release"
        headers = {"X-Api-Key": self.sonarr_api_key}
        params = {"seriesId": series_id}
        try:
            logger.info(f"Getting series releases for Sonarr ID: {series_id}")
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting series releases: {e}")
            return []

    # --- GENERAL RELEASE OPERATIONS & QUEUE ---

    async def download_release(self, app_type: str, release_payload: dict) -> tuple[bool, str]:
        """Send the chosen release resource to Radarr or Sonarr to start the download."""
        if app_type == "movie":
            url = f"{self.radarr_url}/api/v3/release"
            api_key = self.radarr_api_key
        elif app_type == "series":
            url = f"{self.sonarr_url}/api/v3/release"
            api_key = self.sonarr_api_key
        else:
            return False, "Unknown application type."

        headers = {"X-Api-Key": api_key}
        try:
            logger.info(f"Pushing download release to {app_type}: {release_payload.get('title')}")
            response = await self.client.post(url, headers=headers, json=release_payload)
            if response.status_code in (200, 201, 202):
                return True, f"Triggered download for '{release_payload.get('title')}'!"
            else:
                logger.error(f"Push release failed: status {response.status_code}, {response.text}")
                return (
                    False,
                    f"Server responded with status {response.status_code}: {response.text}",
                )
        except Exception as e:
            logger.error(f"Error pushing download release: {e}")
            return False, f"Failed to start download: {str(e)}"

    async def get_download_queue(self) -> list[dict]:
        """Get the active download queue from both Radarr and Sonarr, with de-duplication."""
        unique_downloads = {}

        # 1. Fetch Radarr queue (large page size to get all items)
        try:
            res = await self.client.get(
                f"{self.radarr_url}/api/v3/queue",
                headers={"X-Api-Key": self.radarr_api_key},
                params={"pageSize": 1000},
            )
            if res.status_code == 200:
                data = res.json()
                items = data if isinstance(data, list) else data.get("records", [])
                for item in items:
                    download_id = item.get("downloadId") or item.get("title")
                    if not download_id:
                        continue
                    # Keep one entry per download task
                    if download_id not in unique_downloads:
                        unique_downloads[download_id] = {
                            "app": "Radarr (Movie)",
                            "title": item.get("title", "Unknown"),
                            "status": item.get("status", "unknown"),
                            "size": item.get("size", 0),
                            "sizeleft": item.get("sizeleft", 0),
                            "timeleft": item.get("timeleft", "unknown"),
                        }
        except Exception as e:
            logger.error(f"Error fetching Radarr queue: {e}")

        # 2. Fetch Sonarr queue (large page size to get all items)
        try:
            res = await self.client.get(
                f"{self.sonarr_url}/api/v3/queue",
                headers={"X-Api-Key": self.sonarr_api_key},
                params={"pageSize": 1000},
            )
            if res.status_code == 200:
                data = res.json()
                items = data if isinstance(data, list) else data.get("records", [])
                for item in items:
                    download_id = item.get("downloadId") or item.get("title")
                    if not download_id:
                        continue
                    if download_id not in unique_downloads:
                        unique_downloads[download_id] = {
                            "app": "Sonarr (TV Show)",
                            "title": item.get("title", "Unknown"),
                            "status": item.get("status", "unknown"),
                            "size": item.get("size", 0),
                            "sizeleft": item.get("sizeleft", 0),
                            "timeleft": item.get("timeleft", "unknown"),
                        }
        except Exception as e:
            logger.error(f"Error fetching Sonarr queue: {e}")

        return list(unique_downloads.values())
