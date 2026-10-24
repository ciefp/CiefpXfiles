# -*- coding: utf-8 -*-
#
# xtream_api.py - Xtream Codes API klijent
#
# Koristi /player_api.php i /get.php endpointe.
# Sve metode vraćaju (success: bool, data: dict/list/None, error: str|None)
#
from __future__ import absolute_import, print_function

import json
import ssl
import urllib.request
import urllib.parse


# SSL context koji ne verifikuje sertifikate (mnogi IPTV serveri imaju self-signed)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

DEFAULT_TIMEOUT = 15


def _http_get_json(url, timeout=DEFAULT_TIMEOUT):
    """GET URL -> JSON dict/list, ili None uz ispis greške."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "CiefpXfiles/1.0 (Enigma2)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            raw = resp.read()
            # Neki serveri vraćaju BOM ili leading whitespace
            text = raw.decode("utf-8", errors="ignore").lstrip("\ufeff").strip()
            if not text:
                return None
            return json.loads(text)
    except urllib.error.HTTPError as e:
        print(f"[CiefpXfiles] HTTP {e.code} for {url}")
        return None
    except urllib.error.URLError as e:
        print(f"[CiefpXfiles] URL error for {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"[CiefpXfiles] JSON error for {url}: {e}")
        return None


class XtreamAPI(object):
    """Klijent za jedan Xtream portal."""

    def __init__(self, host, username, password, timeout=DEFAULT_TIMEOUT):
        self.host = (host or "").rstrip("/")
        self.username = username or ""
        self.password = password or ""
        self.timeout = timeout
        self._user_info = None
        self._server_info = None

    # ---------- HELPER ----------
    def _api_url(self, action=None, **extra_params):
        params = {
            "username": self.username,
            "password": self.password,
        }
        if action:
            params["action"] = action
        params.update(extra_params)
        return f"{self.host}/player_api.php?" + urllib.parse.urlencode(params)

    def build_live_url(self, stream_id, ext="ts"):
        """http://host/live/user/pass/ID.ext"""
        return f"{self.host}/live/{self.username}/{self.password}/{stream_id}.{ext}"

    def build_movie_url(self, stream_id, ext="mp4"):
        """http://host/movie/user/pass/ID.ext"""
        return f"{self.host}/movie/{self.username}/{self.password}/{stream_id}.{ext}"

    def build_series_url(self, episode_id, ext="mp4"):
        """http://host/series/user/pass/ID.ext"""
        return f"{self.host}/series/{self.username}/{self.password}/{episode_id}.{ext}"

    # ---------- AUTH / STATUS ----------
    def get_player_api(self):
        """
        Poziva /player_api.php bez action.
        Vraća (success, data, error) gde data sadrži 'user_info' i 'server_info'.
        """
        url = self._api_url()
        data = _http_get_json(url, timeout=self.timeout)
        if not data or not isinstance(data, dict):
            return False, None, "No response from server"

        user_info = data.get("user_info") or {}
        # Neki serveri vraćaju {"user_info": {"auth": 0, ...}}
        if not user_info:
            return False, None, "Invalid player_api response"

        auth = user_info.get("auth")
        status = (user_info.get("status") or "").lower()
        if auth in (0, "0", False) or status in ("banned", "disabled", "expired"):
            msg = user_info.get("message") or status or "Auth failed"
            return False, data, msg

        self._user_info = user_info
        self._server_info = data.get("server_info") or {}
        return True, data, None

    @property
    def user_info(self):
        return self._user_info or {}

    @property
    def server_info(self):
        return self._server_info or {}

    def is_active(self):
        """Da li je nalog aktivan (na osnovu keširanog user_info)."""
        st = (self.user_info.get("status") or "").lower()
        return st == "active"

    def expires_str(self):
        """Vraća lepo formatiran datum isteka ili '-'"""
        exp = self.user_info.get("exp_date")
        if not exp:
            return "-"
        try:
            import time
            return time.strftime("%d.%m.%Y", time.localtime(int(exp)))
        except Exception:
            return str(exp)

    def max_connections(self):
        return self.user_info.get("max_connections", "-")

    def active_connections(self):
        return self.user_info.get("active_cons", "-")

    # ---------- LIVE ----------
    def get_live_categories(self):
        url = self._api_url(action="get_live_categories")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid live categories"
        return True, data, None

    def get_live_streams(self, category_id=None):
        if category_id:
            url = self._api_url(action="get_live_streams", category_id=category_id)
        else:
            url = self._api_url(action="get_live_streams")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid live streams"
        return True, data, None

    # ---------- VOD ----------
    def get_vod_categories(self):
        url = self._api_url(action="get_vod_categories")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid vod categories"
        return True, data, None

    def get_vod_streams(self, category_id=None):
        if category_id:
            url = self._api_url(action="get_vod_streams", category_id=category_id)
        else:
            url = self._api_url(action="get_vod_streams")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid vod streams"
        return True, data, None

    def get_vod_info(self, vod_id):
        url = self._api_url(action="get_vod_info", vod_id=vod_id)
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, dict):
            return False, None, "Invalid vod info"
        return True, data, None

    # ---------- SERIES ----------
    def get_series_categories(self):
        url = self._api_url(action="get_series_categories")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid series categories"
        return True, data, None

    def get_series(self, category_id=None):
        if category_id:
            url = self._api_url(action="get_series", category_id=category_id)
        else:
            url = self._api_url(action="get_series")
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, list):
            return False, [], "Invalid series list"
        return True, data, None

    def get_series_info(self, series_id):
        url = self._api_url(action="get_series_info", series_id=series_id)
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, dict):
            return False, None, "Invalid series info"
        return True, data, None

    # ---------- SHORT EPG ----------
    def get_short_epg(self, stream_id, limit=2):
        """Dohvata EPG preko get_simple_data_table (kao XKlass)."""
        url = self._api_url(action="get_simple_data_table", stream_id=stream_id)
        data = _http_get_json(url, timeout=self.timeout)
        if not isinstance(data, dict):
            return False, None, "Invalid simple data table"
        return True, data, None

    def build_live_hls_url(self, stream_id):
        return f"{self.host}/live/{self.username}/{self.password}/{stream_id}.m3u8"