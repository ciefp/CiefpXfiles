# -*- coding: utf-8 -*-
#
# playlist_parser.py - tolerantni parser za playlist.txt
#
# Podržava dva formata:
#
# FORMAT A (strukturirani):
#   Hᴏsᴛ:http://vpn.koszalek.xyz:80
#   Usᴇʀɴᴀᴍᴇ:a52d6eabea
#   Pᴀssᴡᴏʀᴅ:f406c939163c
#   m3u:http://vpn.koszalek.xyz:80/get.php?username=...&password=...&type=m3u_plus&output=ts
#   EPG:http://vpn.koszalek.xyz:80/xmltv.php?username=...&password=...
#
# FORMAT B (samo M3U linkovi):
#   http://rjcf.ofztvxv.top:8080/get.php?username=...&password=...&type=m3u_plus&output=ts
#   http://vpn.koszalek.xyz:80/get.php?username=...&password=...&type=m3u_plus&output=ts
#
from __future__ import absolute_import, print_function

import os
import re
from urllib.parse import urlparse, parse_qs


# Small Caps Unicode -> normalna ASCII slova
_SMALL_CAPS_MAP = {
    "\u1d00": "a", "\u0299": "b", "\u1d04": "c", "\u1d05": "d",
    "\u1d07": "e", "\ua730": "f", "\u0262": "g", "\u029c": "h",
    "\u026a": "i", "\u1d0a": "j", "\u1d0b": "k", "\u029f": "l",
    "\u1d0d": "m", "\u0274": "n", "\u1d0f": "o", "\u1d18": "p",
    "\u0280": "r", "\ua731": "s", "\u1d1b": "t", "\u1d1c": "u",
    "\u1d20": "v", "\u1d21": "w", "\u028f": "y", "\u1d22": "z",
}


def _normalize_key(s):
    """Pretvara 'Hᴏsᴛ' -> 'HOST', 'Usᴇʀɴᴀᴍᴇ' -> 'USERNAME'"""
    if not s:
        return ""
    for k, v in _SMALL_CAPS_MAP.items():
        s = s.replace(k, v)
    return s.strip().upper()

from .paths import PLAYLIST_FILE

def parse_playlist_file(path=None):
    if path is None:
        path = PLAYLIST_FILE

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[CiefpXfiles] cannot read playlist: {e}")
        return []

    portals = []
    current = {}

    def _finalize(cur):
        if not cur:
            return
        # Ako imamo m3u link ali ne host/user/pass - izvuci iz m3u URL-a
        if cur.get("m3u") and not cur.get("host"):
            m3u_url = cur["m3u"]
            try:
                p = urlparse(m3u_url)
                cur["host"] = f"{p.scheme}://{p.netloc}"
                qs = parse_qs(p.query)
                if "username" in qs:
                    cur["username"] = qs["username"][0]
                if "password" in qs:
                    cur["password"] = qs["password"][0]
            except Exception:
                pass
        # Ako imamo host/user/pass ali ne m3u - generiši
        if cur.get("host") and cur.get("username") and cur.get("password") and not cur.get("m3u"):
            h = cur["host"].rstrip("/")
            cur["m3u"] = (f"{h}/get.php?username={cur['username']}"
                          f"&password={cur['password']}&type=m3u_plus&output=ts")
        # Ako imamo host/user/pass ali ne epg - generiši
        if cur.get("host") and cur.get("username") and cur.get("password") and not cur.get("epg"):
            h = cur["host"].rstrip("/")
            cur["epg"] = (f"{h}/xmltv.php?username={cur['username']}"
                          f"&password={cur['password']}")

        # Validacija: mora imati host + user + pass
        if cur.get("host") and cur.get("username") and cur.get("password"):
            portals.append(cur)
        else:
            print(f"[CiefpXfiles] skipping incomplete portal: {cur}")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # FORMAT B - samostalni http linkovi
        if line.lower().startswith("http"):
            # Ako je M3U link (get.php)
            if "get.php" in line.lower():
                # Ako već imamo započet portal, sačuvaj ga
                if current:
                    _finalize(current)
                    current = {}
                current["m3u"] = line
                try:
                    p = urlparse(line)
                    current["host"] = f"{p.scheme}://{p.netloc}"
                    qs = parse_qs(p.query)
                    if "username" in qs:
                        current["username"] = qs["username"][0]
                    if "password" in qs:
                        current["password"] = qs["password"][0]
                except Exception:
                    pass

            # Ako je EPG link (xmltv.php)
            elif "xmltv.php" in line.lower():
                # Pokušavamo da ga prikačimo na trenutni portal
                try:
                    p = urlparse(line)
                    h = f"{p.scheme}://{p.netloc}"
                    qs = parse_qs(p.query)
                    u = qs.get("username", [""])[0]

                    # Ako se poklapa host i user sa trenutnim portalom
                    if current.get("host") == h and current.get("username") == u:
                        current["epg"] = line
                    else:
                        # Ako ne postoji portal, a imamo samo epg, ignorišemo ga
                        pass
                except Exception:
                    pass
            continue

        # FORMAT A - ključ:vrednost
        if ":" in line:
            key_raw, _, value = line.partition(":")
            key = _normalize_key(key_raw)
            value = value.strip()
            if key == "HOST":
                # Novi portal počinje sa HOST:
                if current and current.get("host"):
                    _finalize(current)
                    current = {}
                current["host"] = value.rstrip("/")
            elif key == "USERNAME":
                current["username"] = value
            elif key == "PASSWORD":
                current["password"] = value
            elif key == "M3U":
                current["m3u"] = value
            elif key == "EPG":
                current["epg"] = value

    if current:
        _finalize(current)

    # Dodeli imena
    for idx, p in enumerate(portals):
        host = p.get("host", "")
        try:
            netloc = urlparse(host).netloc
        except Exception:
            netloc = host
        p["name"] = netloc or f"Portal {idx + 1}"
        p["id"] = idx

    print(f"[CiefpXfiles] parsed {len(portals)} portals from {path}")
    return portals


def save_portal_to_file(path, portal):
    """Dodaje novi portal u playlist.txt (FORMAT A)."""
    lines = [
        "",
        f"Host:{portal.get('host', '')}",
        f"Username:{portal.get('username', '')}",
        f"Password:{portal.get('password', '')}",
    ]
    if portal.get("m3u"):
        lines.append(f"m3u:{portal['m3u']}")
    if portal.get("epg"):
        lines.append(f"EPG:{portal['epg']}")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception as e:
        print(f"[CiefpXfiles] save portal error: {e}")
        return False


def remove_portal_from_file(path, portal):
    """
    Uklanja portal iz playlist.txt.
    Pošto parser toleriše razne formate, najlakše je:
    - pročitaj sve linije
    - prepoznaj blokove po HOST: ili po http get.php linijama
    - preskoči blok koji odgovara datom portalu
    - upiši nazad
    """
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[CiefpXfiles] remove portal read error: {e}")
        return False

    target_host = (portal.get("host") or "").rstrip("/")
    target_user = portal.get("username") or ""

    out = []
    skip_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue

        # Da li je ovo početak novog bloka?
        is_host_start = _normalize_key(stripped.partition(":")[0]) == "HOST"
        is_http_start = stripped.lower().startswith("http") and "get.php" in stripped.lower()

        if is_host_start or is_http_start:
            # Proveri da li ovaj blok odgovara target portalu
            block_matches = False
            if is_host_start:
                val = stripped.partition(":")[2].strip().rstrip("/")
                if val == target_host:
                    block_matches = True
            elif is_http_start:
                # uporedi host i user iz URL-a
                try:
                    p = urlparse(stripped)
                    h = f"{p.scheme}://{p.netloc}"
                    qs = parse_qs(p.query)
                    u = qs.get("username", [""])[0]
                    if h.rstrip("/") == target_host and u == target_user:
                        block_matches = True
                except Exception:
                    pass

            skip_block = block_matches
            if skip_block:
                continue  # preskoči ovu liniju
            out.append(line)
            continue

        if skip_block:
            continue
        out.append(line)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
        return True
    except Exception as e:
        print(f"[CiefpXfiles] remove portal write error: {e}")
        return False