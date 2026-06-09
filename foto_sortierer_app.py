#!/usr/bin/env python3
"""
Foto Sortierer – macOS App
Benötigt: pip3 install customtkinter pillow
Als App packen: pip3 install pyinstaller && pyinstaller --windowed --onefile --name "Foto Sortierer" foto_sortierer_app.py
"""


import os, shutil, datetime, re, threading
from collections import defaultdict
import customtkinter as ctk
from tkinter import filedialog, messagebox


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


PHOTO_EXTS_ALL = [".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".tif",
                  ".raw", ".cr2", ".nef", ".arw", ".dng", ".gif", ".webp", ".bmp"]
VIDEO_EXTS_ALL = [".mp4", ".mov", ".avi", ".mkv", ".mts", ".m2ts",
                  ".wmv", ".flv", ".3gp", ".m4v", ".mpg", ".mpeg"]




def get_exif_date(fp):
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(fp)
        exif = img._getexif()
        if exif:
            for tid, val in exif.items():
                if TAGS.get(tid) == "DateTimeOriginal":
                    return datetime.datetime.strptime(val, "%Y:%m:%d %H:%M:%S"), "exif"
    except: pass
    return None, None




def get_filename_date(fp):
    m = re.search(r"(\d{4})[_\-.]?(\d{2})[_\-.]?(\d{2})", os.path.basename(fp))
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1990 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, mo, d), "filename"
        except: pass
    return None, None




def get_date(fp, ext, photo_exts):
    if ext in photo_exts:
        dt, src = get_exif_date(fp)
        if dt: return dt, src
    dt, src = get_filename_date(fp)
    if dt: return dt, src
    return datetime.datetime.fromtimestamp(os.path.getmtime(fp)), "mtime"




def safe_copy(src, dst_dir, name, dt=None):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
        return "skipped"
    if os.path.exists(dst):
        base, ext = os.path.splitext(name)
        # Rename with creation date instead of _1, _2 ...
        if dt is None:
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(src))
        date_str = dt.strftime("%Y-%m-%d_%H%M%S")
        dst = os.path.join(dst_dir, f"{base}_{date_str}{ext}")
        # Fallback counter if date-renamed file also exists
        c = 1
        while os.path.exists(dst):
            dst = os.path.join(dst_dir, f"{base}_{date_str}_{c}{ext}")
            c += 1
