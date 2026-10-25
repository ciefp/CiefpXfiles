# -*- coding: utf-8 -*-
from Components.config import config, ConfigSubsection, ConfigText, ConfigSelection, ConfigYesNo, ConfigDirectory

# Inicijalizacija sekcije za naš plugin
config.plugins.ciefpxfiles = ConfigSubsection()

# API Ključevi
config.plugins.ciefpxfiles.tmdb_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpxfiles.omdb_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpxfiles.groq_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpxfiles.subdl_api_key = ConfigText(default="", fixed_size=False)

# Jezici
LANG_CHOICES = [
    ("en", "English"), ("sr", "Srpski"), ("hr", "Hrvatski"), 
    ("bs", "Bosanski"), ("de", "Deutsch"), ("fr", "Français"), 
    ("es", "Español"), ("it", "Italiano"), ("ru", "Русский")
]
config.plugins.ciefpxfiles.tmdb_language = ConfigSelection(default="en", choices=LANG_CHOICES)
config.plugins.ciefpxfiles.subtitle_language = ConfigSelection(default="sr", choices=LANG_CHOICES)

# Putanje
config.plugins.ciefpxfiles.subtitle_location = ConfigText(default="/media/hdd/subtitles/", fixed_size=False)
config.plugins.ciefpxfiles.playlist_location = ConfigText(default="/etc/enigma2/CiefpXfiles/playlist.txt", fixed_size=False)

# GROQ
config.plugins.ciefpxfiles.groq_plot_translation = ConfigYesNo(default=True)
config.plugins.ciefpxfiles.groq_model = ConfigSelection(default="openai/gpt-oss-20b", choices=[
    ("openai/gpt-oss-20b", "GPT-OSS 20B (Preporučeno)"),
    ("openai/gpt-oss-120b", "GPT-OSS 120B (Snažniji)"),
    ("qwen/qwen3.8-27b", "Qwen 3.8 27B"),
])
# Plejeri
PLAYER_CHOICES = [
    ("5002", "Exteplayer3 (5002)"),
    ("5001", "GStreamer (5001)"),
    ("4097", "GStreamer (4097)")
]
config.plugins.ciefpxfiles.player_type_live = ConfigSelection(default="5002", choices=PLAYER_CHOICES)
config.plugins.ciefpxfiles.player_type_vod = ConfigSelection(default="5002", choices=PLAYER_CHOICES)

# EPG i Ostalo
config.plugins.ciefpxfiles.epg_auto_update = ConfigYesNo(default=True)
config.plugins.ciefpxfiles.epg_interval_hours = ConfigSelection(default="12", choices=[
    ("6", "6 sati"), ("12", "12 sati"), ("24", "24 sata"), ("48", "48 sati")
])
config.plugins.ciefpxfiles.adult_content = ConfigYesNo(default=False)
config.plugins.ciefpxfiles.use_subssupport = ConfigYesNo(default=True)
config.plugins.ciefpxfiles.subtitle_language = ConfigSelection(default="sr", choices=[
    ("sr", "Srpski"), ("hr", "Hrvatski"), ("en", "English"),
    ("de", "Deutsch"), ("fr", "Français"), ("es", "Español"),
    ("it", "Italiano"), ("ru", "Русский")
])
config.plugins.ciefpxfiles.subtitle_location = ConfigText(default="/media/hdd/subtitles/", fixed_size=False)
config.plugins.ciefpxfiles.epg_auto_update = ConfigYesNo(default=True)
config.plugins.ciefpxfiles.adult_content = ConfigYesNo(default=False)
config.plugins.ciefpxfiles.use_subssupport = ConfigYesNo(default=True)
# Tip skina (Classic / Modern)
config.plugins.ciefpxfiles.skin_type = ConfigSelection(default="classic", choices=[
    ("classic", "Classic"),
    ("modern", "Modern"),
])