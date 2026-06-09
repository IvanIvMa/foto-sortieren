# Foto Sortierer

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)](https://apple.com)

Sortiert **27.000+ Fotos & Videos** nach EXIF-Aufnahmedatum in eine übersichtliche Ordnerstruktur. Erkennt Duplikate automatisch.

```
📁 Zielordner/
  📁 2013/
    📁 Fotos/    ← JPG, PNG, HEIC, RAW, ...
    📁 Videos/   ← MP4, MOV, MTS, ...
  📁 2014/
    ...
  📁 _Duplikate/ ← überflüssige Kopien zur manuellen Prüfung
```

## Features

- **EXIF-Datum** – liest `DateTimeOriginal` direkt aus den Metadaten
- **Fallback-Kette** – kein EXIF? → Datum aus Dateiname → Änderungsdatum
- **Duplikat-Erkennung** – gleicher Dateiname + Dateigröße = Duplikat
- **Sicher** – Original wird nie verändert (nur kopieren, nie löschen)
- **Wiederholbar** – bereits kopierte Dateien werden übersprungen
- **GUI-App** – `foto_sortierer_app.py` mit grafischer Oberfläche

## Unterstützte Formate

| Typ | Formate |
|-----|---------|
| Fotos | `.jpg` `.jpeg` `.png` `.heic` `.heif` `.tiff` `.raw` `.cr2` `.nef` `.arw` `.dng` `.gif` `.webp` `.bmp` |
| Videos | `.mp4` `.mov` `.avi` `.mkv` `.mts` `.m2ts` `.wmv` `.flv` `.3gp` `.m4v` `.mpg` `.mpeg` |

## Installation

```bash
pip3 install -r requirements.txt
```

## Verwendung

### CLI (Kommandozeile)

```bash
python3 foto_sortieren.py
```

Konfiguration oben im Skript anpassen:

```python
SOURCE = '/Volumes/Verbatim/Pics'          # Quellordner
DEST   = '/Volumes/SSD_IM/Verbatim Media'  # Zielordner
```

### GUI App

```bash
python3 foto_sortierer_app.py
```

Ordner per Klick auswählen, Dateitypen filtern, Fortschritt live verfolgen.

### Als macOS .app packen

```bash
pip3 install pyinstaller
pyinstaller --windowed --onefile --name "Foto Sortierer" foto_sortierer_app.py
# → dist/Foto Sortierer.app in Programme-Ordner ziehen
```

## Hinweis: Schreibrechte

macOS kann auf **NTFS-Festplatten** (Windows-Format) nicht schreiben. Als Zielordner eine Festplatte mit **exFAT**, **APFS** oder **Mac OS Extended** verwenden.

## Ausgabe

```
============================================================
  FOTO/VIDEO SORTIERER
  Quelle : /Volumes/Verbatim/Pics
  Ziel   : /Volumes/SSD_IM/Verbatim Media
============================================================
Sammle Dateien...
  -> 27,457 Mediendateien
  -> 1,058 Duplikate erkannt
Starte Sortierung...
  1,000/27,457 (4%)  kopiert: 1,000

FERTIG!
  Kopiert      : 26,399
  Übersprungen :      0
  Duplikate    :  1,058
  EXIF-Datum   : 20,234
  Dateiname    :  1,704
  Änd.datum    :  4,461
```

## Lizenz

MIT – siehe [LICENSE](LICENSE)
