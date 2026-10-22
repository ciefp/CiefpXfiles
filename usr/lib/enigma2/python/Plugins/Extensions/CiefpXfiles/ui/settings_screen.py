# -*- coding: utf-8 -*-
import os
import shutil
import threading
import requests
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from ..core.config import config

from ..core.paths import (
    TMDB_KEY_FILE, OMDB_KEY_FILE, GROQ_KEY_FILE, SUBDL_KEY_FILE,
    PLAYLIST_FILE, POSTERS_CACHE_DIR, get_plugin_dir
)
from ..core.paths import get_plugin_dir
BACKGROUND_SETTINGS = os.path.join(get_plugin_dir(), "icons", "settings.png")

class SettingsScreen(Screen):
    skin = """
        <screen name="CiefpXfilesSettings" position="center,center" size="1400,950"
                title="..:: CiefpXfiles Settings ::.." backgroundColor="#011a2e">
            <widget name="menu" position="50,50" size="700,800" scrollbarMode="showOnDemand"
                    itemHeight="45" font="Regular;26" backgroundColor="#011a2e"/>
            <widget name="status" position="50,800" size="1300,40" font="Regular;26"
                    foregroundColor="#00FF00" backgroundColor="#011a2e"/>
            <widget name="background" position="800,0" size="500,750" pixmap="%s" alphatest="on" />        
            <ePixmap pixmap="buttons/red.png" position="50,880" size="35,35" alphatest="blend"/>
            <eLabel text="Cancel" position="100,870" size="200,50" font="Regular;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
            <ePixmap pixmap="buttons/green.png" position="320,880" size="35,35" alphatest="blend"/>
            <eLabel text="Save" position="370,870" size="200,50" font="Regular;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """% BACKGROUND_SETTINGS

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["menu"] = MenuList([])
        self["status"] = Label("Settings")
        self["background"] = Pixmap()
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.save_settings,
                "ok": self.on_ok,
                "left": self.on_left,
                "right": self.on_right,
            }, -1)
            
        self.onLayoutFinish.append(self.build_menu)

    def _get_plugin_dir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read_key(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def _write_key(self, path, value):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(value.strip())
            return True
        except Exception as e:
            print(f"[CiefpXfiles] Error saving key: {e}")
            return False

    def _get_cache_size(self):
        total_size = 0
        if os.path.exists(POSTERS_CACHE_DIR):
            for dirpath, _, filenames in os.walk(POSTERS_CACHE_DIR):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # U MB

    def _clear_cache(self):
        if os.path.exists(POSTERS_CACHE_DIR):
            try:
                shutil.rmtree(POSTERS_CACHE_DIR)
                os.makedirs(POSTERS_CACHE_DIR)
                self["status"].setText("Cache cleared successfully!")
            except Exception as e:
                self["status"].setText(f"Error clearing cache: {e}")
        else:
            self["status"].setText("Cache is already empty.")

    def build_menu(self):
        # Provera ključeva
        tmdb = "[SET]" if self._read_key(TMDB_KEY_FILE) else "[EMPTY]"
        omdb = "[SET]" if self._read_key(OMDB_KEY_FILE) else "[EMPTY]"
        groq = "[SET]" if self._read_key(GROQ_KEY_FILE) else "[EMPTY]"
        subdl = "[SET]" if self._read_key(SUBDL_KEY_FILE) else "[EMPTY]"

        # Uzimamo vrednosti iz config-a
        t_lang = config.plugins.ciefpxfiles.tmdb_language.value
        g_trans = "YES" if config.plugins.ciefpxfiles.groq_plot_translation.value else "NO"
        p_live = config.plugins.ciefpxfiles.player_type_live.value
        p_vod = config.plugins.ciefpxfiles.player_type_vod.value

        # Ostale opcije
        sub_lang = getattr(config.plugins.ciefpxfiles, 'subtitle_language',
                           type('obj', (object,), {'value': 'sr'})).value
        epg_auto = "YES" if getattr(config.plugins.ciefpxfiles, 'epg_auto_update',
                                    type('obj', (object,), {'value': True})).value else "NO"
        adult = "YES" if getattr(config.plugins.ciefpxfiles, 'adult_content',
                                 type('obj', (object,), {'value': False})).value else "NO"

        cache_mb = self._get_cache_size()

        items = [
            f"TMDB API Key:         {tmdb}",
            f"OMDB API Key:         {omdb}",
            f"GROQ API Key:         {groq}",
            f"SUBDL API Key:        {subdl}",
            "----------------------------------------",
            f"TMDB Language:        {t_lang}",
            f"GROQ Translate Plot:  {g_trans}",
            f"GROQ Translate Lang:  {sub_lang}",
            f"Live Player Type:     {p_live}",
            f"VOD Player Type:      {p_vod}",
            f"Subtitle Language:    {sub_lang}",
            f"EPG Auto Update:      {epg_auto}",
            f"Adult Content:        {adult}",
            "----------------------------------------",
            f"Clear Cache:          {cache_mb:.1f} MB",
            ">>> TEST TMDB CONNECTION <<<"
        ]

        self["menu"].setList(items)

    def on_ok(self):
        idx = self["menu"].getSelectedIndex()
        if idx == 0:
            self.edit_key("TMDB API Key", TMDB_KEY_FILE)
        elif idx == 1:
            self.edit_key("OMDB API Key", OMDB_KEY_FILE)
        elif idx == 2:
            self.edit_key("GROQ API Key", GROQ_KEY_FILE)
        elif idx == 3:
            self.edit_key("SUBDL API Key", SUBDL_KEY_FILE)
        elif idx == 14:
            self._clear_cache()
        elif idx == 15:
            self.test_tmdb()

    def _change_option(self, idx, direction):
        if idx == 5:  # TMDB Language
            choices = ["en", "sr", "hr", "bs", "de", "fr", "es", "it", "ru"]
            current = config.plugins.ciefpxfiles.tmdb_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpxfiles.tmdb_language.value = choices[new_idx]
        elif idx == 6:  # GROQ Translate Plot
            config.plugins.ciefpxfiles.groq_plot_translation.value = not config.plugins.ciefpxfiles.groq_plot_translation.value
        elif idx == 7:  # GROQ Translate Lang
            choices = ["sr", "hr", "en", "de", "fr", "es", "it", "ru"]
            current = config.plugins.ciefpxfiles.subtitle_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpxfiles.subtitle_language.value = choices[new_idx]
        elif idx == 8:  # Live Player
            choices = ["5002", "5001", "4097"]
            current = config.plugins.ciefpxfiles.player_type_live.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpxfiles.player_type_live.value = choices[new_idx]
        elif idx == 9:  # VOD Player
            choices = ["5002", "5001", "4097"]
            current = config.plugins.ciefpxfiles.player_type_vod.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpxfiles.player_type_vod.value = choices[new_idx]
        elif idx == 10:  # Subtitle Language
            choices = ["sr", "hr", "en", "de", "fr", "es", "it", "ru"]
            current = config.plugins.ciefpxfiles.subtitle_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpxfiles.subtitle_language.value = choices[new_idx]
        elif idx == 11:  # EPG Auto Update
            config.plugins.ciefpxfiles.epg_auto_update.value = not config.plugins.ciefpxfiles.epg_auto_update.value
        elif idx == 12:  # Adult Content
            config.plugins.ciefpxfiles.adult_content.value = not config.plugins.ciefpxfiles.adult_content.value

        self.build_menu()

    def on_left(self):
        idx = self["menu"].getSelectedIndex()
        self._change_option(idx, -1)

    def on_right(self):
        idx = self["menu"].getSelectedIndex()
        self._change_option(idx, 1)

    def edit_key(self, title, filename_or_config, is_file=True):
        if is_file:
            current = self._read_key(filename_or_config)
        else:
            current = filename_or_config.value

        def cb(res):
            if res is not None:
                if is_file:
                    if self._write_key(filename_or_config, res):
                        self["status"].setText(f"{title} saved.")
                else:
                    filename_or_config.value = res
                    self["status"].setText(f"{title} saved.")
                self.build_menu()
        self.session.openWithCallback(cb, VirtualKeyBoard, title=title, text=current)

    def save_settings(self):
        config.plugins.ciefpxfiles.save()
        self["status"].setText("Settings saved!")
        self.close()

    def test_tmdb(self):
        api_key = self._read_key(TMDB_KEY_FILE)
        if not api_key:
            self["status"].setText("TMDB Key is empty! Please set it first.")
            return

        self["status"].setText("Testing TMDB connection...")

        def worker():
            try:
                url = f"https://api.themoviedb.org/3/movie/550?api_key={api_key}&language=en-US"
                response = requests.get(url, timeout=10, verify=False)
                if response.status_code == 200:
                    msg = f"Success! TMDB returned: {response.json().get('title', 'Unknown')}"
                else:
                    msg = f"HTTP Error: {response.status_code}"
            except Exception as e:
                msg = f"Connection Error: {str(e)}"

            from enigma import eTimer
            self._test_timer = eTimer()
            self._test_timer.callback.append(lambda: self["status"].setText(msg))
            self._test_timer.start(10, True)

        threading.Thread(target=worker, daemon=True).start()