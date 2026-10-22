# -*- coding: utf-8 -*-
#
# main_screen.py - Glavni ekran sa 3 panela (Kategorije, Info, Poster)
#
from __future__ import absolute_import, print_function

import os
import threading
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER

from ..core.xtream_api import XtreamAPI
from ..core.player import play_stream
from ..core.metadata import fetch_metadata_async
from .settings_screen import SettingsScreen
from ..core.epg_parser import download_epg_async, load_epg_from_cache, get_current_epg
from ..core.metadata import fetch_metadata_async, fetch_omdb_rating_async, translate_text_async
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

class MainScreen(Screen):
    skin = """
        <screen name="CiefpXfilesMain" position="0,0" size="1920,1080"
                backgroundColor="#011a2e" title="..:: CiefpXfiles ::..">

            <!-- NASLOV NA VRHU -->
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- LEVI PANEL: Kategorije i Streamovi -->
            <widget name="left_list" position="40,110" size="650,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- SREDNJI PANEL: Odvojeni podaci -->
            <widget name="movie_title" position="720,110" size="550,40" font="Bold;34"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="epg_title" position="720,150" size="550,30" font="Regular;20"
                    foregroundColor="#A0A0A0" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="duration" position="720,190" size="550,30" font="Regular;24"
                    foregroundColor="#D3D3D3" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="rating" position="720,230" size="550,30" font="Regular;24"
                    foregroundColor="#03a81f" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="imdb_rating" position="720,270" size="550,30" font="Regular;24"
                    foregroundColor="#F5C518" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="genres" position="720,310" size="550,30" font="Regular;24"
                    foregroundColor="#f702db" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="director" position="720,350" size="550,30" font="Regular;24"
                    foregroundColor="#f79102" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="plot" position="720,390" size="550,400" font="Regular;24"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>
            
            <widget name="cast_header" position="720,800" size="550,30" font="Bold;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="cast" position="720,840" size="550,120" font="Regular;20"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- DESNI PANEL: Poster -->
            <widget name="poster" position="1320,110" size="500,750"
                    alphatest="blend" zPosition="2"/>

            <!-- STATUS -->
            <widget name="status" position="1250,1005" size="700,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/green.png" position="240,1005" size="35,35" alphatest="blend"/>
            <eLabel text="LIVE" position="290,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/yellow.png" position="480,1005" size="35,35" alphatest="blend"/>
            <eLabel text="MOVIES" position="530,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#808000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/blue.png" position="720,1005" size="35,35" alphatest="blend"/>
            <eLabel text="SERIES" position="770,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#000080" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/red.png" position="960,1005" size="35,35" alphatest="blend"/>
            <eLabel text="SETTINGS" position="1010,1000" size="200,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#400080" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal, api_data):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        
        # Inicijalizacija API klijenta
        self.api = XtreamAPI(portal["host"], portal["username"], portal["password"])
        
        self.current_view = "HOME" # HOME, LIVE, VOD, SERIES
        self.categories = []
        self.streams = []
        self.current_category = None
        self.current_series = None
        self.current_season = None
        self.streams_series_data = None
        self._fetch_timer = None  
        self._last_tmdb_title = None 
        self._tmdb_timer = None
        self._epg_loaded = False

        # Tip plejera (učitava se iz config-a)
        self.player_type_live = config.plugins.ciefpxfiles.player_type_live.value
        self.player_type_vod = config.plugins.ciefpxfiles.player_type_vod.value

        # Widgets
        self["title"] = Label(f"..:: CiefpXfiles - {portal.get('name', '')} ::..")
        
        # Koristimo MenuList sa podrškom za sličice
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        
        # Srednji panel
        self["movie_title"] = Label("")
        self["epg_title"] = Label("")
        self["duration"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["plot"] = Label("")
        self["cast_header"] = Label("")
        self["cast"] = Label("")
        
        self["poster"] = Pixmap()
        self["status"] = Label("")

        # Actions
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.show_live,
                "yellow": self.show_movies,
                "blue": self.show_series,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
                "menu": self.open_settings,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        self._set_poster(None)
        self.show_home()

    def _set_poster(self, image_path):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if image_path and os.path.exists(image_path):
            path = image_path
        else:
            path = os.path.join(plugin_dir, "icons", "placeholder.png")

        px = _load_pixmap_safe(path)
        if px and self["poster"].instance:
            self["poster"].instance.setPixmap(px)

    def _clear_info_panel(self):
        self["movie_title"].setText("")
        self["epg_title"].setText("")
        self["duration"].setText("")
        self["rating"].setText("")
        self["imdb_rating"].setText("")
        self["genres"].setText("")
        self["director"].setText("")
        self["plot"].setText("")
        self["cast_header"].setText("")
        self["cast"].setText("")

    # ---------- VIEWS ----------
    def show_home(self):
        self.current_view = "HOME"
        self.current_category = None
        self._clear_info_panel()
        self._set_poster(None)
        
        # Pravimo listu sa sličicama
        items = []
        # Placeholder za prvi red (Please select a category)
        items.append([
            ("", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="Please select a category:")
        ])
        
        icon_live = _get_icon_path("icon_live.png")
        if os.path.exists(icon_live):
            items.append([
                ("LIVE", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_live)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Live")
            ])
        else:
            items.append([("LIVE", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="> Live")])

        icon_film = _get_icon_path("icon_film.png")
        if os.path.exists(icon_film):
            items.append([
                ("MOVIES", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_film)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Movies")
            ])
        else:
            items.append([("MOVIES", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="> Movies")])

        icon_tv = _get_icon_path("icon_tv.png")
        if os.path.exists(icon_tv):
            items.append([
                ("SERIES", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_tv)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Series")
            ])
        else:
            items.append([("SERIES", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="> Series")])

        items.append([("", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="")])
        items.append([("", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="or make settings on the settings button:")])
        items.append([("", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="TMDB, OMDB, Clear Cache ...")])
        
        self["left_list"].setList(items)
        self["plot"].setText("Welcome to CiefpXfiles.\n\nUse Green, Yellow, or Blue buttons to browse content.")

    def show_live(self):
        self.current_view = "LIVE"
        self.current_category = None
        self["status"].setText("Loading Live categories...")
        ok, data, err = self.api.get_live_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def show_movies(self):
        self.current_view = "VOD"
        self.current_category = None
        self["status"].setText("Loading Movies categories...")
        ok, data, err = self.api.get_vod_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def show_series(self):
        self.current_view = "SERIES"
        self.current_category = None
        self["status"].setText("Loading Series categories...")
        ok, data, err = self.api.get_series_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def _render_categories(self):
        items = []
        # BACK dugme
        items.append([
            ("BACK", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO HOME ]")
        ])
        
        icon_folder = _get_icon_path("icon_folder.png")
        for cat in self.categories:
            name = cat.get('category_name', 'Unknown')
            if os.path.exists(icon_folder):
                items.append([
                    (name, cat.get("category_id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_folder)),
                    MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
            else:
                items.append([
                    (name, cat.get("category_id")),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
                
        self["left_list"].setList(items)
        self["left_list"].moveToIndex(1)
        self["status"].setText(f"Loaded {len(self.categories)} categories. Press OK to open.")
        self._update_info()

    # ---------- NAVIGATION ----------
    def on_up(self):
        try:
            self["left_list"].up()
            self._update_info()
        except Exception:
            pass

    def on_down(self):
        try:
            self["left_list"].down()
            self._update_info()
        except Exception:
            pass
    def _update_info(self):
        idx = self["left_list"].getSelectedIndex()

        if self.current_view == "HOME":
            self._clear_info_panel()
            self._set_poster(None)
            return

        # Provera za BACK dugme
        if idx == 0:
            self._clear_info_panel()
            self["movie_title"].setText("Go back to previous menu.")
            self._set_poster(None)
            return

        # 1. KATEGORIJE
        if self.current_category is None and (0 < idx <= len(self.categories)):
            cat = self.categories[idx - 1]
            self._clear_info_panel()
            self["movie_title"].setText(f"Category: {cat.get('category_name', '')}")
            self["plot"].setText("Press OK to open.")
            self._set_poster(None)
            return

        # 2. LIVE ILI VOD ILI SERIJE (lista)
        if self.current_category is not None and not self.current_series:
            if 0 < idx <= len(self.streams):
                s = self.streams[idx - 1]
                name = s.get("name", "Unknown")
                rating = s.get("rating", "")

                self._clear_info_panel()
                self["movie_title"].setText(f"Name: {name}")

                if rating and str(rating) != "0":
                    self["rating"].setText(f"Server Rating: {rating}")

                if self.current_view == "VOD":
                    ext = s.get("container_extension", "")
                    if ext:
                        self["duration"].setText(f"Format: {ext.upper()}")

                self["plot"].setText("Loading metadata...")

                if self.current_view in ("VOD", "SERIES"):
                    self._trigger_tmdb_fetch(name, "movie" if self.current_view == "VOD" else "tv")
                else:
                    self["plot"].setText("Press OK to play.")
                    self._set_poster(None)
            return

        # 3. SERIJE (Sezone)
        if self.current_series is not None and self.current_season is None:
            series_info = self.current_series.get("info", {})
            base_name = series_info.get("name", "Unknown Series")
            # Pošto smo u listi sezona, a idx > 0, uzimamo ime sezone iz self.streams
            if 0 < idx <= len(self.streams):
                season_num = self.streams[idx - 1]
                self._clear_info_panel()
                self["movie_title"].setText(f"Series: {base_name}")
                self["plot"].setText(f"Season {season_num}\nSelect an episode to play.")
            return

        # 4. SERIJE (Epizode)
        if self.current_series is not None and self.current_season is not None:
            series_info = self.current_series.get("info", {})
            base_name = series_info.get("name", "Unknown Series")
            if 0 < idx <= len(self.streams):
                ep = self.streams[idx - 1]
                ep_num = ep.get("episode_num")
                title = ep.get("title", "Unknown")
                self._clear_info_panel()
                self["movie_title"].setText(f"Series: {base_name}")
                self["plot"].setText(f"S{self.current_season}E{ep_num} - {title}\n\nPress OK to play.")
            return

    def _trigger_tmdb_fetch(self, title, media_type):
        if title == self._last_tmdb_title:
            return

        self._last_tmdb_title = title

        from enigma import eTimer
        def _do_fetch():
            fetch_metadata_async(title, media_type, self._on_tmdb_data)

        if self._tmdb_timer:
            self._tmdb_timer.stop()

        self._tmdb_timer = eTimer()
        self._tmdb_timer.callback.append(_do_fetch)
        self._tmdb_timer.start(500, True)

    def _on_tmdb_data(self, success, data):
        from enigma import eTimer
        def _update_ui():
            if not success:
                self["plot"].setText(f"TMDB Error: {data}")
                return

            plot = data.get("plot", "-")
            if len(plot) > 450:
                plot = plot[:450] + "..."

            self["plot"].setText(f"Plot:\n{plot}")
            
            if config.plugins.ciefpxfiles.groq_plot_translation.value:
                self["plot"].setText(f"Plot:\n{plot}\n\n(Translating...)")
                translate_text_async(plot, self._on_translated_plot)
            else:
                self["plot"].setText(f"Plot:\n{plot}")

            self["movie_title"].setText(f"{data.get('title')} ({data.get('year')})")
            self["epg_title"].setText("")
            self["rating"].setText(f"TMDB: {data.get('rating')}/10 ★")
            self["genres"].setText(f"Genres: {data.get('genres')}")
            self["director"].setText(f"Director: {data.get('director')}")
            
            cast = data.get('cast', '-')
            if cast != '-':
                self["cast_header"].setText("Cast:")
                self["cast"].setText(cast)
            else:
                self["cast_header"].setText("")
                self["cast"].setText("")

            self["duration"].setText("")
            self["imdb_rating"].setText("IMDB: Loading...")

            fetch_omdb_rating_async(data.get('title'), data.get('year'), self._on_omdb_data)
            self._set_poster(data.get("poster_path"))

        self._tmdb_ui_timer = eTimer()
        self._tmdb_ui_timer.callback.append(_update_ui)
        self._tmdb_ui_timer.start(10, True)

    def _on_omdb_data(self, success, rating):
        from enigma import eTimer
        def _update_ui():
            if success:
                self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
            else:
                self["imdb_rating"].setText("IMDB: N/A")

        self._omdb_ui_timer = eTimer()
        self._omdb_ui_timer.callback.append(_update_ui)
        self._omdb_ui_timer.start(10, True)

    def _on_translated_plot(self, success, translated_text):
        from enigma import eTimer
        def _update_ui():
            if success:
                self["plot"].setText(f"Plot (SR):\n{translated_text}")
            else:
                current_text = self["plot"].getText()
                if "(Translating...)" in current_text:
                    self["plot"].setText(current_text.replace("(Translating...)", f"(Prevod nije uspeo: {translated_text})"))
                else:
                    self["plot"].setText(current_text + f"\n\n(Prevod nije uspeo: {translated_text})")

        self._trans_timer = eTimer()
        self._trans_timer.callback.append(_update_ui)
        self._trans_timer.start(10, True)

    # ---------- ACTIONS ----------
    def on_ok(self):
        idx = self["left_list"].getSelectedIndex()

        if self.current_view == "HOME":
            if idx == 1:
                self.show_live()
            elif idx == 2:
                self.show_movies()
            elif idx == 3:
                self.show_series()
            return

        if self.current_category is None:
            if idx == 0:
                self.show_home()
                return
            if idx > 0 and (idx - 1) < len(self.categories):
                cat = self.categories[idx - 1]
                self.current_category = cat.get("category_id")
                self._load_streams_for_category()
            return

        if self.current_category is not None:
            if idx == 0:
                if self.current_season is not None:
                    self._open_series(self.streams_series_data)
                    return
                elif self.current_series is not None:
                    self.current_series = None
                    self._load_streams_for_category()
                    return
                else:
                    self.current_category = None
                    self._render_categories()
                    return

            if self.current_view == "SERIES" and not self.current_series:
                if idx > 0 and (idx - 1) < len(self.streams):
                    self._open_series(self.streams[idx - 1])
            elif self.current_view == "SERIES" and self.current_series and not self.current_season:
                if idx > 0 and (idx - 1) < len(self.streams):
                    season_num = self.streams[idx - 1]
                    self._open_season(season_num)
            else:
                self._play_selected_stream()

    def _load_streams_for_category(self):
        self["status"].setText("Loading streams...")
        if self.current_view == "LIVE":
            ok, data, err = self.api.get_live_streams(self.current_category)
        elif self.current_view == "VOD":
            ok, data, err = self.api.get_vod_streams(self.current_category)
        elif self.current_view == "SERIES":
            ok, data, err = self.api.get_series(self.current_category)
        else:
            return

        if ok:
            self.streams = data
            items = []
            
            # BACK dugme
            items.append([
                ("BACK", ""),
                MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="[ BACK TO CATEGORIES ]")
            ])

            if self.current_view == "LIVE":
                icon_live = _get_icon_path("icon_live.png")
                if not self._epg_loaded:
                    epg_url = self.portal.get("epg")
                    if epg_url:
                        self["status"].setText("Downloading EPG...")
                        download_epg_async(epg_url, self._on_epg_downloaded)
                    else:
                        self._epg_loaded = True

                for s in self.streams:
                    name = s.get("name", "Unknown")
                    epg_info = get_current_epg(name)
                    epg_str = ""
                    if epg_info and epg_info.get("current"):
                        epg_str = f" | {epg_info['current']['title']}"
                    
                    if os.path.exists(icon_live):
                        items.append([
                            (name, s.get("stream_id")),
                            MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_live)),
                            MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text=f"{name}{epg_str}")
                        ])
                    else:
                        items.append([
                            (name, s.get("stream_id")),
                            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text=f"{name}{epg_str}")
                        ])
            else:
                if self.current_view == "SERIES":
                    icon = _get_icon_path("icon_tv.png")
                else:
                    icon = _get_icon_path("icon_film.png")
                    
                for s in self.streams:
                    name = s.get("name", "Unknown")
                    if os.path.exists(icon):
                        items.append([
                            (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                            MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon)),
                            MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text=name)
                        ])
                    else:
                        items.append([
                            (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text=name)
                        ])

            self["left_list"].setList(items)
            self["left_list"].moveToIndex(0)
            self["status"].setText(f"Loaded {len(self.streams)} items.")
            self._update_info()
        else:
            self["status"].setText(f"Error: {err}")

    def _on_epg_downloaded(self, success, msg):
        from enigma import eTimer
        def _update():
            if success:
                load_epg_from_cache()
                self._epg_loaded = True
                self["status"].setText("EPG Updated. Reloading list...")
                self._load_streams_for_category()
            else:
                self._epg_loaded = True
                self["status"].setText(f"EPG Error: {msg}")

        t = eTimer()
        t.callback.append(_update)
        t.start(10, True)

    def _play_selected_stream(self):
        idx = self["left_list"].getSelectedIndex()
        if idx == 0:
            return

        stream = self.streams[idx - 1]

        if self.current_view == "SERIES" and self.current_season is not None:
            ep_id = stream.get("id")
            ext = stream.get("container_extension", "mp4")
            url = self.api.build_series_url(ep_id, ext)
            title = stream.get("title", "Unknown")
        else:
            stream_id = stream.get("stream_id")
            title = stream.get("name", "Unknown")
            if self.current_view == "LIVE":
                url = self.api.build_live_url(stream_id, "ts")
            elif self.current_view == "VOD":
                container_ext = stream.get("container_extension", "mp4")
                url = self.api.build_movie_url(stream_id, container_ext)
            else:
                return

        # Odabir plejera
        if self.current_view == "LIVE":
            p_type = self.player_type_live
        else:
            p_type = self.player_type_vod

        self["status"].setText(f"Playing: {title}...")

        # 1. Puštamo strim
        success, err = play_stream(self.session, url, p_type, title=title)

        if success:
            # 2. Sakrijemo prozor (ne zatvaramo ga odmah)
            self.hide()

            # 3. Zatvorimo prozor nakon 500ms (kada plejer već preuzme fokus)
            from enigma import eTimer
            def _close_later():
                self.close(True)

            self._close_timer = eTimer()
            self._close_timer.callback.append(_close_later)
            self._close_timer.start(500, True)
        else:
            self["status"].setText(f"Play failed: {err}")

    def _open_series(self, series_data):
        series_id = series_data.get("series_id")
        series_name = series_data.get("name", "Unknown")
        self["status"].setText(f"Loading seasons for {series_name}...")

        def fetch_worker():
            ok, data, err = self.api.get_series_info(series_id)
            from enigma import eTimer
            def _update_ui():
                self._fetch_timer = None
                if not ok or not data:
                    self["status"].setText(f"Error loading series: {err}")
                    return
                self.current_series = data
                self.streams_series_data = series_data
                self.current_season = None
                self.streams = []

                items = []
                # BACK dugme
                items.append([
                    ("BACK", ""),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text="[ BACK TO SERIES ]")
                ])
                
                icon_season = _get_icon_path("icon_season.png")
                episodes = data.get("episodes", {})

                if not episodes:
                    items.append([("NONE", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="No episodes found.")])
                else:
                    for season_num in sorted(episodes.keys(), key=int):
                        season_text = f"Season {season_num}"
                        if os.path.exists(icon_season):
                            items.append([
                                (season_text, str(season_num)),
                                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_season)),
                                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                      text=season_text)
                            ])
                        else:
                            items.append([
                                (season_text, str(season_num)),
                                MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                      text=season_text)
                            ])
                        self.streams.append(season_num)

                self["left_list"].setList(items)
                if len(items) > 1:
                    self["left_list"].moveToIndex(1)
                else:
                    self["left_list"].moveToIndex(0)
                self["status"].setText(f"Loaded {len(episodes)} seasons.")
                self._update_info()

            self._fetch_timer = eTimer()
            self._fetch_timer.callback.append(_update_ui)
            self._fetch_timer.start(10, True)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _open_season(self, season_num):
        self.current_season = str(season_num)
        episodes = self.current_series.get("episodes", {}).get(self.current_season, [])

        items = []
        # BACK dugme
        items.append([
            ("BACK", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO SEASONS ]")
        ])
        
        self.streams = []
        icon_play = _get_icon_path("icon_play.png")

        for ep in episodes:
            ep_num = ep.get("episode_num")
            title = ep.get("title", "Unknown")
            ep_text = f"S{season_num}E{ep_num} - {title}"
            
            if os.path.exists(icon_play):
                items.append([
                    (ep_text, ep.get("id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_play)),
                    MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=ep_text)
                ])
            else:
                items.append([
                    (ep_text, ep.get("id")),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=ep_text)
                ])
            self.streams.append(ep)

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Loaded {len(episodes)} episodes for Season {season_num}.")
        self._update_info()

    def open_settings(self):
        self.session.open(SettingsScreen)