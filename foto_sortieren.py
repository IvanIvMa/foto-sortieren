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
  3. Fuer Videos und Fotos ohne EXIF: Datum aus Dateiname oder Aenderungsdatum
  4. Erkennt Duplikate (gleicher Dateiname + Dateigroesse)
  5. Kopiert alles in DEST nach Struktur: Jahr/Fotos/ und Jahr/Videos/
  6. Duplikate -> DEST/_Duplikate/ (zur manuellen Pruefung)

WICHTIG:
  - Originalordner wird NICHT veraendert (nur kopieren, nie loeschen)
  - Du kannst das Skript mehrfach ausfuehren - bereits kopierte Dateien werden uebersprungen
  - Nach Pruefung des Ergebnisses kannst du den Originalordner selbst aufraeumen
"""

import os
import shutil
import datetime
import re
import sys
from collections import defaultdict

# --- KONFIGURATION ---
SOURCE = '/Volumes/Verbatim/Pics'
DEST   = '/Volumes/SSD_IM/Verbatim Media'
SKIP_DIRS = {'Pics_Sortiert', '_Sortiert', '_Duplikate'}

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
            y, mo, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1990 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, mo, d), 'filename'
        except Exception:
            pass
    return None, None


def get_best_date(filepath, ext):
    if ext in PHOTO_EXT:
        dt, source = get_exif_date(filepath)
        if dt:
            return dt, source
    dt, source = get_filename_date(filepath)
    if dt:
        return dt, source
    mtime = os.path.getmtime(filepath)
    return datetime.datetime.fromtimestamp(mtime), 'mtime'


def safe_copy(src, dst_dir, filename):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, filename)
    if os.path.exists(dst):
        try:
            if os.path.getsize(src) == os.path.getsize(dst):
                return 'skipped'
        except Exception:
            pass
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dst):
            dst = os.path.join(dst_dir, f"{base}_{counter}{ext}")
            counter += 1
    shutil.copy2(src, dst)
    return 'copied'


def collect_media_files(source, skip_dirs):
    files = []
    for root, dirs, filenames in os.walk(source):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in MEDIA_EXT:
                files.append(os.path.join(root, f))
    return files


def find_duplicates(files):
    key_map = defaultdict(list)
    for fp in files:
        try:
            sz = os.path.getsize(fp)
            key = (os.path.basename(fp).lower(), sz)
            key_map[key].append(fp)
        except Exception:
            pass
    duplicates = set()
    for key, paths in key_map.items():
        if len(paths) > 1:
            paths_sorted = sorted(paths, key=lambda p: len(p))
            for dp in paths_sorted[1:]:
                duplicates.add(dp)
    return duplicates


def main():
    print("=" * 60)
    print("  FOTO/VIDEO SORTIERER")
    print("=" * 60)
    print(f"  Quelle: {SOURCE}")
    print(f"  Ziel:   {DEST}")
    print()

    try:
        from PIL import Image
    except ImportError:
        print("FEHLER: Pillow nicht installiert. Bitte: pip3 install Pillow")
        sys.exit(1)

    if not os.path.exists(SOURCE):
        print(f"FEHLER: Quellordner nicht gefunden: {SOURCE}")
        sys.exit(1)

    print("Schritt 1/3: Sammle alle Mediendateien...")
    files = collect_media_files(SOURCE, SKIP_DIRS)
    print(f"  -> {len(files):,} Mediendateien gefunden")

    print("Schritt 2/3: Erkenne Duplikate...")
    duplicates = find_duplicates(files)
    print(f"  -> {len(duplicates):,} ueberfluessige Kopien erkannt")

    total = len(files)
    print(f"Schritt 3/3: Sortiere {total:,} Dateien...")

    stats = {'copied': 0, 'skipped': 0, 'errors': 0,
             'photos': 0, 'videos': 0, 'dupes': 0,
             'exif': 0, 'filename': 0, 'mtime': 0}
    error_log = []

    for i, fp in enumerate(files):
        if i > 0 and i % 1000 == 0:
            print(f"  {i:,}/{total:,} ({i/total*100:.0f}%)  kopiert: {stats['copied']:,}")

        ext = os.path.splitext(fp)[1].lower()
        filename = os.path.basename(fp)

        try:
            if fp in duplicates:
                result = safe_copy(fp, os.path.join(DEST, '_Duplikate'), filename)
                if result == 'copied':
                    stats['dupes'] += 1
                stats[result] += 1
                continue

            dt, source = get_best_date(fp, ext)
            stats[source] = stats.get(source, 0) + 1
            year = str(dt.year)
            subdir = 'Fotos' if ext in PHOTO_EXT else 'Videos'
            if ext in PHOTO_EXT:
                stats['photos'] += 1
            else:
                stats['videos'] += 1

            result = safe_copy(fp, os.path.join(DEST, year, subdir), filename)
            stats[result] += 1

        except Exception as e:
            stats['errors'] += 1
            error_log.append(f"{fp}: {e}")

    print(f"\nFERTIG! Kopiert: {stats['copied']:,} | Uebersprungen: {stats['skipped']:,} | Fehler: {stats['errors']:,}")
    print(f"Fotos: {stats['photos']:,} | Videos: {stats['videos']:,} | Duplikate: {stats['dupes']:,}")
    print(f"Datum-Quellen: EXIF={stats['exif']:,} Dateiname={stats['filename']:,} mtime={stats['mtime']:,}")
    print(f"Ergebnis in: {DEST}")

    if error_log:
        os.makedirs(DEST, exist_ok=True)
        with open(os.path.join(DEST, '_fehler.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(error_log))


if __name__ == '__main__':
    main()
