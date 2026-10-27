# -*- coding: utf-8 -*-
#
# modern_seasons_screen.py - Moderni ekran za sezone i epizode
#
from __future__ import absolute_import, print_function

import os
import threading
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from enigma import eTimer, eServiceReference, eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap

from ..core.metadata import fetch_metadata_async, fetch_omdb_rating_async
from ..core.xtream_api import XtreamAPI
from ..core.config import config
def _load_pixmap_safe(path):
    if path and os.path.exists(path):
        try:
            return LoadPixmap(path)
        except Exception:
            return None
    return None
def _get_icon_path(icon_name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", icon_name)

class ModernSeasonsScreen(Screen):
    skin = """
        <screen name="CiefpXfilesModernSeasons" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- LEVI PANEL: Sezone / Epizode -->
            <widget name="left_list" position="40,110" size="500,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- SREDNJI PANEL: Informacije o seriji -->
            <widget name="movie_title" position="570,110" size="550,40" font="Bold;34"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="rating" position="570,230" size="550,30" font="Regular;24"
                    foregroundColor="#03a81f" backgroundColor="#011a2e" transparent="1"/>

            <widget name="imdb_rating" position="570,270" size="550,30" font="Regular;24"
                    foregroundColor="#F5C518" backgroundColor="#011a2e" transparent="1"/>

            <widget name="genres" position="570,310" size="550,30" font="Regular;24"
                    foregroundColor="#f702db" backgroundColor="#011a2e" transparent="1"/>

            <widget name="director" position="570,350" size="550,30" font="Regular;24"
                    foregroundColor="#f79102" backgroundColor="#011a2e" transparent="1"/>

            <widget name="plot" position="570,390" size="700,400" font="Regular;24"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <widget name="cast_header" position="570,800" size="550,30" font="Bold;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="cast" position="570,840" size="550,120" font="Regular;20"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- DESNI PANEL: Poster -->
            <widget name="logo" position="1320,110" size="500,750"
                    alphatest="blend" zPosition="2"/>

            <!-- STATUS -->
            <widget name="status" position="720,950" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>

            <ePixmap pixmap="buttons/green.png" position="240,1005" size="35,35" alphatest="blend"/>
            <eLabel text="PLAY" position="290,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """
    def __init__(self, session, portal, series_id, series_title, poster_path=None):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        self.series_id = series_id
        self.series_title = series_title
        self.poster_path = poster_path  # <-- DODATO

        
        self.api = XtreamAPI(portal["host"], portal["username"], portal["password"])
        
        self.seasons = []
        self.episodes = []
        self.current_season = None
        self.is_showing_episodes = False
        
        try:
            self.player_type_vod = config.plugins.ciefpxfiles.player_type_vod.value
        except Exception:
            self.player_type_vod = "4097"
        
        self["title"] = Label(f"..:: {series_title} ::..")
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        self["logo"] = Pixmap()
        self["movie_title"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["plot"] = Label("")
        self["cast_header"] = Label("")
        self["cast"] = Label("")
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.on_back,
                "red": self.on_back,
                "green": self.on_ok,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Prvo pokušaj da učitaš poster serije
        if self.poster_path and os.path.exists(self.poster_path):
            px = _load_pixmap_safe(self.poster_path)
            if px and self["logo"].instance:
                self["logo"].instance.setPixmap(px)
                self["logo"].show()
        else:
            # Ako nema postera, koristi plugin logo
            logo_path = os.path.join(plugin_dir, "icons", "plugin_logo.png")
            if os.path.exists(logo_path):
                px = _load_pixmap_safe(logo_path)
                if px and self["logo"].instance:
                    self["logo"].instance.setPixmap(px)
                    self["logo"].show()

        self["status"].setText("Loading seasons...")
        self._fetch_metadata()
        self["status"].setText("Loading seasons...")
        self.load_seasons()
        self.load_seasons()

    def load_seasons(self):
        ok, data, err = self.api.get_series_info(self.series_id)
        if ok and data:
            episodes = data.get("episodes", {})
            self.seasons = sorted(episodes.keys(), key=int)
            self.is_showing_episodes = False
            self.render_seasons()
        else:
            self["status"].setText(f"Error: {err}")

    def render_seasons(self):
        items = []
        icon_season = _get_icon_path("icon_season.png")
        
        for idx, season_num in enumerate(self.seasons):
            text = f"Season {season_num}"
            if os.path.exists(icon_season):
                items.append([
                    (season_num, "season"),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_season)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
            else:
                items.append([
                    (season_num, "season"),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
        
        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Loaded {len(self.seasons)} seasons. Press OK to open.")

    def load_episodes(self, season_num):
        ok, data, err = self.api.get_series_info(self.series_id)
        if ok and data:
            episodes_data = data.get("episodes", {}).get(str(season_num), [])
            self.episodes = episodes_data
            self.current_season = season_num
            self.is_showing_episodes = True
            self.render_episodes()
        else:
            self["status"].setText(f"Error: {err}")

    def render_episodes(self):
        items = []
        icon_play = _get_icon_path("icon_play.png")
        
        # BACK dugme
        items.append([
            ("BACK", "back"),
            MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO SEASONS ]")
        ])
        
        for ep in self.episodes:
            ep_num = ep.get("episode_num")
            title = ep.get("title", "Unknown")
            text = f"S{self.current_season}E{ep_num} - {title}"
            
            if os.path.exists(icon_play):
                items.append([
                    (ep, "episode"),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_play)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
            else:
                items.append([
                    (ep, "episode"),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
        
        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Season {self.current_season}: {len(self.episodes)} episodes.")

    def on_up(self):
        try:
            self["left_list"].up()
        except Exception:
            pass

    def on_down(self):
        try:
            self["left_list"].down()
        except Exception:
            pass

    def on_ok(self):
        idx = self["left_list"].getSelectedIndex()
        
        if not self.is_showing_episodes:
            # Kliknuta je sezona
            if 0 <= idx < len(self.seasons):
                season_num = self.seasons[idx]
                self.load_episodes(season_num)
        else:
            # Kliknuta je epizoda ili BACK
            if idx == 0:
                # BACK
                self.is_showing_episodes = False
                self.current_season = None
                self.render_seasons()
                return
            
            if 0 < idx <= len(self.episodes):
                ep = self.episodes[idx - 1]
                self.play_episode(ep)

    def play_episode(self, ep):
        ep_id = ep.get("id")
        title = ep.get("title", "Unknown")
        ext = ep.get("container_extension", "mp4")
        
        url = self.api.build_series_url(ep_id, ext)
        
        encoded_url = url.replace(":", "%3a")
        safe_title = title.replace(":", " -").replace("\n", " ")
        ref_str = f"{self.player_type_vod}:0:1:0:0:0:0:0:0:0:{encoded_url}:{safe_title}"
        
        try:
            ref = eServiceReference(ref_str)
            if not ref.valid():
                self["status"].setText("Invalid service reference")
                return
        except Exception as e:
            self["status"].setText(f"Error: {e}")
            return
            
        try:
            self.session.openWithCallback(
                self._on_player_closed,
                MoviePlayer,
                ref
            )
        except Exception as e:
            self["status"].setText(f"Could not open player: {e}")

    def _on_player_closed(self, *args):
        self["status"].setText("Returned to series.")

    def _fetch_metadata(self):
        # Preuzimamo TMDB podatke za seriju na osnovu njenog naslova
        def _do_fetch():
            fetch_metadata_async(self.series_title, "tv", self._on_tmdb_data)

        self._tmdb_timer = eTimer()
        self._tmdb_timer.callback.append(_do_fetch)
        self._tmdb_timer.start(300, True)

    def _on_tmdb_data(self, success, data):
        def _update_ui():
            if not success or not data:
                self["plot"].setText("TMDB Metadata not found.")
                return

            self["movie_title"].setText(f"{data.get('title', 'Unknown')} ({data.get('year', '')})")
            self["rating"].setText(f"TMDB: {data.get('rating', '0.0')}/10 ★")
            self["genres"].setText(f"Genres: {data.get('genres', '-')}")
            self["director"].setText(f"Creator: {data.get('director', '-')}")
            self["cast"].setText(f"Cast: {data.get('cast', '-')}")

            cast = data.get('cast', '-')
            if cast != '-':
                self["cast_header"].setText("Cast:")
                self["cast"].setText(cast)
            else:
                self["cast_header"].setText("")
                self["cast"].setText("")

            plot = data.get("plot", "-")
            if len(plot) > 450:
                plot = plot[:450] + "..."
            self["plot"].setText(f"Plot:\n{plot}")

            self["imdb_rating"].setText("IMDB: Loading...")
            fetch_omdb_rating_async(data.get('title'), data.get('year'), self._on_imdb_data)

        self._tmdb_ui_timer = eTimer()
        self._tmdb_ui_timer.callback.append(_update_ui)
        self._tmdb_ui_timer.start(10, True)

    def _on_imdb_data(self, success, rating):
        def _update_ui():
            if success:
                self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
            else:
                self["imdb_rating"].setText("IMDB: N/A")

        self._imdb_ui_timer = eTimer()
        self._imdb_ui_timer.callback.append(_update_ui)
        self._imdb_ui_timer.start(10, True)

    def on_back(self):
        if self.is_showing_episodes:
            # Vrati se na sezone
            self.is_showing_episodes = False
            self.current_season = None
            self.render_seasons()
        else:
            # Zatvori ekran
            self.close()