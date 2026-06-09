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
    shutil.copy2(src, dst)
    return "copied"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Foto Sortierer")
        self.geometry("680x820")
        self.resizable(True, True)
        self._stop = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        pad = {"padx": 20, "pady": (10, 0)}

        # ── Titel ──
        ctk.CTkLabel(self, text="Foto Sortierer", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(self, text="Sortiert Fotos & Videos nach Aufnahmedatum", text_color="gray", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        # ── Ordner ──
        f_folders = ctk.CTkFrame(self)
        f_folders.grid(row=2, column=0, sticky="ew", **pad)
        f_folders.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f_folders, text="Ordner", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(f_folders, text="Quelle:", anchor="w").grid(row=1, column=0, padx=(14,6), pady=4, sticky="w")
        self.src_var = ctk.StringVar(value="/Volumes/Verbatim/Pics")
        ctk.CTkEntry(f_folders, textvariable=self.src_var, width=380).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(f_folders, text="Wählen", width=80, command=lambda: self.browse("src")).grid(row=1, column=2, padx=(4,14), pady=4)

        ctk.CTkLabel(f_folders, text="Ziel:", anchor="w").grid(row=2, column=0, padx=(14,6), pady=4, sticky="w")
        self.dst_var = ctk.StringVar(value="/Volumes/SSD_IM/Verbatim Media")
        ctk.CTkEntry(f_folders, textvariable=self.dst_var, width=380).grid(row=2, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(f_folders, text="Wählen", width=80, command=lambda: self.browse("dst")).grid(row=2, column=2, padx=(4,14), pady=4)
        ctk.CTkLabel(f_folders, text="  Tipp: Das Ziel muss beschreibbar sein (nicht NTFS/schreibgeschützt)", text_color="gray", font=ctk.CTkFont(size=11)).grid(row=3, column=0, columnspan=3, sticky="w", padx=14, pady=(0,10))

        # ── Dateitypen ──
        f_types = ctk.CTkFrame(self)
        f_types.grid(row=3, column=0, sticky="ew", **pad)
        f_types.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f_types, text="Dateitypen", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12,6))

        self.photo_vars = {}
        self.video_vars = {}

        photo_frame = ctk.CTkFrame(f_types, fg_color="transparent")
        photo_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(0,4))
        ctk.CTkLabel(photo_frame, text="Fotos:", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=(0,8))
        for ext in PHOTO_EXTS_ALL:
            v = ctk.BooleanVar(value=True)
            self.photo_vars[ext] = v
            ctk.CTkCheckBox(photo_frame, text=ext, variable=v, width=60, checkbox_width=16, checkbox_height=16, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        video_frame = ctk.CTkFrame(f_types, fg_color="transparent")
        video_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0,12))
        ctk.CTkLabel(video_frame, text="Videos:", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=(0,8))
        for ext in VIDEO_EXTS_ALL:
            v = ctk.BooleanVar(value=True)
            self.video_vars[ext] = v
            ctk.CTkCheckBox(video_frame, text=ext, variable=v, width=60, checkbox_width=16, checkbox_height=16, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)

        # Alle an/aus Buttons
        btn_row = ctk.CTkFrame(f_types, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="w", padx=14, pady=(0,10))
        ctk.CTkButton(btn_row, text="Alle Fotos an", width=120, height=26, font=ctk.CTkFont(size=12),
                      command=lambda: [v.set(True) for v in self.photo_vars.values()]).pack(side="left", padx=(0,6))
        ctk.CTkButton(btn_row, text="Alle Fotos aus", width=120, height=26, font=ctk.CTkFont(size=12),
                      command=lambda: [v.set(False) for v in self.photo_vars.values()]).pack(side="left", padx=(0,12))
        ctk.CTkButton(btn_row, text="Alle Videos an", width=120, height=26, font=ctk.CTkFont(size=12),
                      command=lambda: [v.set(True) for v in self.video_vars.values()]).pack(side="left", padx=(0,6))
        ctk.CTkButton(btn_row, text="Alle Videos aus", width=120, height=26, font=ctk.CTkFont(size=12),
                      command=lambda: [v.set(False) for v in self.video_vars.values()]).pack(side="left")

        # ── Optionen ──
        f_opts = ctk.CTkFrame(self)
        f_opts.grid(row=4, column=0, sticky="ew", **pad)
        ctk.CTkLabel(f_opts, text="Optionen", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12,6))

        self.opt_dupes = ctk.BooleanVar(value=True)
        self.opt_type = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(f_opts, text="Duplikate in _Duplikate/ verschieben (gleicher Name + Größe)", variable=self.opt_dupes).grid(row=1, column=0, padx=14, pady=3, sticky="w")
        ctk.CTkCheckBox(f_opts, text="Nach Typ trennen: Jahr/Fotos/ und Jahr/Videos/", variable=self.opt_type).grid(row=2, column=0, padx=14, pady=(3,12), sticky="w")

        # ── Start/Stop ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=12)
        btn_frame.grid_columnconfigure(0, weight=1)

        self.start_btn = ctk.CTkButton(btn_frame, text="▶  Sortierung starten", height=44,
                                        font=ctk.CTkFont(size=15, weight="bold"), command=self.start)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0,8))

        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹  Stopp", height=44, width=100,
                                       fg_color="gray", hover_color="#555", command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=1)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=6, column=0, sticky="ew", padx=20, pady=(0,6))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self, text="Bereit", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=7, column=0, sticky="w", padx=20)

        # ── Log ──
        self.log = ctk.CTkTextbox(self, height=180, font=ctk.CTkFont(family="Menlo", size=12))
        self.log.grid(row=8, column=0, sticky="nsew", padx=20, pady=(6,20))
        self.grid_rowconfigure(8, weight=1)

    def browse(self, which):
        path = filedialog.askdirectory(title="Ordner auswählen")
        if path:
            if which == "src": self.src_var.set(path)
            else: self.dst_var.set(path)

    def log_msg(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def start(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("Fehler", f"Quellordner nicht gefunden:\n{src}"); return
        if not dst:
            messagebox.showerror("Fehler", "Bitte Zielordner angeben."); return

        photo_exts = {ext for ext, v in self.photo_vars.items() if v.get()}
        video_exts = {ext for ext, v in self.video_vars.items() if v.get()}
        if not photo_exts and not video_exts:
            messagebox.showerror("Fehler", "Bitte mindestens einen Dateityp auswählen."); return

        self._stop = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log.delete("1.0", "end")
        self.progress.set(0)

        t = threading.Thread(target=self.run_sort, args=(src, dst, photo_exts, video_exts), daemon=True)
        t.start()

    def stop(self):
        self._stop = True
        self.status_label.configure(text="Wird gestoppt...")

    def run_sort(self, src, dst, photo_exts, video_exts):
        media_exts = photo_exts | video_exts
        skip_dirs = {"_Duplikate", "_Sortiert"}
        handle_dupes = self.opt_dupes.get()
        by_type = self.opt_type.get()

        self.log_msg(f"Sammle Dateien in {src} ...")
        files = []
        for root, dirs, fnames in os.walk(src):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not os.path.join(root, d).startswith(dst)]
            for f in fnames:
                if os.path.splitext(f)[1].lower() in media_exts:
                    files.append(os.path.join(root, f))

        self.log_msg(f"  → {len(files):,} Mediendateien gefunden")

        duplicates = set()
        if handle_dupes:
            km = defaultdict(list)
            for fp in files:
                try: km[(os.path.basename(fp).lower(), os.path.getsize(fp))].append(fp)
                except: pass
            for paths in km.values():
                if len(paths) > 1:
                    for dp in sorted(paths, key=lambda p: len(p))[1:]:
                        duplicates.add(dp)
            self.log_msg(f"  → {len(duplicates):,} Duplikate erkannt")

        stats = {"copied": 0, "skipped": 0, "errors": 0, "dupes": 0}
        total = len(files)

        self.log_msg(f"\nStarte Sortierung → {dst}\n")

        for i, fp in enumerate(files):
            if self._stop:
                self.log_msg("\n⏹  Gestoppt.")
                break

            pct = (i + 1) / total
            self.progress.set(pct)
            self.status_label.configure(text=f"{i+1:,}/{total:,} ({pct*100:.0f}%)  Kopiert: {stats['copied']:,}  Übersprungen: {stats['skipped']:,}")

            ext = os.path.splitext(fp)[1].lower()
            fname = os.path.basename(fp)

            try:
                file_dt, _ = get_date(fp, ext, photo_exts)

                if fp in duplicates:
                    r = safe_copy(fp, os.path.join(dst, "_Duplikate"), fname, file_dt)
                    if r == "copied": stats["dupes"] += 1
                    stats[r] += 1
                    continue

                year = str(file_dt.year)

                if by_type:
                    subdir = "Fotos" if ext in photo_exts else "Videos"
                    dst_dir = os.path.join(dst, year, subdir)
                else:
                    dst_dir = os.path.join(dst, year)

                r = safe_copy(fp, dst_dir, fname, file_dt)
                stats[r] += 1

            except Exception as e:
                stats["errors"] += 1

            if i > 0 and i % 500 == 0:
                self.log_msg(f"  {i:,}/{total:,}  Kopiert: {stats['copied']:,}  Übersprungen: {stats['skipped']:,}")

        self.log_msg(f"\n{'='*45}")
        self.log_msg(f"  FERTIG!")
        self.log_msg(f"  Kopiert:       {stats['copied']:,}")
        self.log_msg(f"  Übersprungen:  {stats['skipped']:,}")
        self.log_msg(f"  Duplikate:     {stats['dupes']:,}")
        self.log_msg(f"  Fehler:        {stats['errors']:,}")
        self.log_msg(f"  Ergebnis:      {dst}")
        self.log_msg(f"{'='*45}")

        self.progress.set(1)
        self.status_label.configure(text="Fertig!")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
