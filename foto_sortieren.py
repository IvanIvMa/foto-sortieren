#!/usr/bin/env python3
"""
foto_sortieren.py
=================
Sortiert Fotos und Videos nach EXIF-Aufnahmedatum.


VERWENDUNG:
    python3 foto_sortieren.py


VORAUSSETZUNGEN:
    pip3 install Pillow


WAS DAS SKRIPT TUT:
  1. Scannt den SOURCE-Ordner nach Fotos und Videos
  2. Liest das EXIF-Aufnahmedatum (DateTimeOriginal) aus Fotos
  3. Für Videos und Fotos ohne EXIF: Datum aus Dateiname oder Änderungsdatum
  4. Erkennt Duplikate (gleicher Dateiname + Dateigröße)
  5. Kopiert alles in DEST nach Struktur: Jahr/Fotos/ und Jahr/Videos/
  6. Duplikate → DEST/_Duplikate/ (zur manuellen Prüfung)


WICHTIG:
  - Originalordner wird NICHT verändert (nur kopieren, nie löschen)
  - Du kannst das Skript mehrfach ausführen – bereits kopierte Dateien werden übersprungen
  - Nach Prüfung des Ergebnisses kannst du den Originalordner selbst aufräumen
"""


import os
import shutil
import datetime
import re
import sys
from collections import defaultdict


# ─── KONFIGURATION ────────────────────────────────────────────────────────────
# Quellordner (wo deine Fotos jetzt liegen)
SOURCE = '/Volumes/MeineLaufwerk/Fotos'


# Zielordner (wo die sortierte Struktur erstellt wird)
# Tipp: Auf derselben Festplatte lassen, damit kein Kopieren über USB nötig ist
DEST = '/Volumes/Ziel/Sortierte Fotos'


# Diese Unterordner im SOURCE werden ignoriert
SKIP_DIRS = {'Pics_Sortiert', '_Sortiert', '_Duplikate'}
# ─────────────────────────────────────────────────────────────────────────────


PHOTO_EXT = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.heic', '.heif',
             '.raw', '.cr2', '.nef', '.arw', '.dng', '.gif', '.webp'}
VIDEO_EXT = {'.mp4', '.mov', '.avi', '.mkv', '.mts', '.m2ts', '.wmv', '.flv',
             '.3gp', '.m4v', '.mpg', '.mpeg'}
MEDIA_EXT = PHOTO_EXT | VIDEO_EXT




def get_exif_date(filepath):
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                if TAGS.get(tag_id) == 'DateTimeOriginal':
                    return datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S'), 'exif'
    except Exception:
        pass
    return None, None




def get_filename_date(filepath):
    name = os.path.basename(filepath)
    match = re.search(r'(\d{4})[_\-\.]?(\d{2})[_\-\.]?(\d{2})', name)
    if match:
        try:
