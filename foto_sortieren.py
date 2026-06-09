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
SOURCE = '/Volumes/Verbatim/Pics'

# Zielordner (wo die sortierte Struktur erstellt wird)
# Tipp: Auf derselben Festplatte lassen, damit kein Kopieren über USB nötig ist
DEST = '/Volumes/SSD_IM/Verbatim Media'

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
        print("FEHLER: Pillow nicht installiert.")
        print("Bitte ausführen: pip3 install Pillow")
        sys.exit(1)

    if not os.path.exists(SOURCE):
        print(f"FEHLER: Quellordner nicht gefunden: {SOURCE}")
        print("Bitte SOURCE-Variable oben im Skript anpassen.")
        sys.exit(1)

    print("Schritt 1/3: Sammle alle Mediendateien...")
    files = collect_media_files(SOURCE, SKIP_DIRS)
    print(f"  → {len(files):,} Mediendateien gefunden")

    print("\nSchritt 2/3: Erkenne Duplikate...")
    duplicates = find_duplicates(files)
    print(f"  → {len(duplicates):,} überflüssige Kopien erkannt")

    total = len(files)
    print(f"\nSchritt 3/3: Sortiere {total:,} Dateien...")
    print("  (Das kann eine Weile dauern – bitte warten)\n")

    stats = {
        'copied': 0, 'skipped': 0, 'errors': 0,
        'photos': 0, 'videos': 0, 'dupes': 0,
        'exif': 0, 'filename': 0, 'mtime': 0
    }
    error_log = []

    for i, fp in enumerate(files):
        if i > 0 and i % 1000 == 0:
            pct = i / total * 100
            print(f"  {i:,}/{total:,} ({pct:.0f}%)  "
                  f"kopiert: {stats['copied']:,}  "
                  f"übersprungen: {stats['skipped']:,}")

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

    print(f"\n{'=' * 60}")
    print("  FERTIG!")
    print(f"{'=' * 60}")
    print(f"  Kopiert:              {stats['copied']:,}")
    print(f"  Übersprungen:         {stats['skipped']:,}")
    print(f"  Fehler:               {stats['errors']:,}")
    print()
    print(f"  davon Fotos:          {stats['photos']:,}")
    print(f"  davon Videos:         {stats['videos']:,}")
    print(f"  davon Duplikate:      {stats['dupes']:,}")
    print()
    print("  Datum-Quellen:")
    print(f"    EXIF (genau):       {stats['exif']:,}")
    print(f"    Dateiname:          {stats['filename']:,}")
    print(f"    Änderungsdatum:     {stats['mtime']:,}")
    print()
    print(f"  Ergebnis in: {DEST}")

    if error_log:
        log_path = os.path.join(DEST, '_fehler.txt')
        os.makedirs(DEST, exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(error_log))
        print(f"\n  Fehlerprotokoll: {log_path}")

    print()
    print("NÄCHSTE SCHRITTE:")
    print(f"  1. Prüfe den sortierten Ordner: {DEST}")
    print(f"  2. Schau dir _Duplikate/ an und lösche was du nicht brauchst")
    print(f"  3. Wenn alles gut aussieht: lösche den alten Ordner {SOURCE}")


if __name__ == '__main__':
    main()
