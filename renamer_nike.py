import os
import queue
import threading
import urllib.request
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from PIL import Image, ImageTk, ImageDraw

# ---------- CONFIG ----------

BACKGROUND_IMAGE_PATH = "nike_bg.jpg"   # metti qui una foto dell'HQ Nike
NIKE_LOGO_FILE = "nike_logo.png"
NIKE_LOGO_URL = "https://static.nike.com/a/images/f_auto/w_200/jo8m1sx7dxvdmwfefk6x/nike-logo.png"

VIEW_ORDER = {
    "PHCFH": 0,  # FRONT
    "PHSLH": 1,  # LEFT
    "PHSRH": 2,  # RIGHT
    "PHCBH": 3,  # BACK
    "PHSTH": 4,  # TOP
    "PHSUH": 5,  # SOLE
    "PHSYD": 6,  # DETAILS / ZOOM
}

# ---------- LOGICA FILE ----------

def parse_filename(path: Path):
    """
    AURORA_415445-101_PHCFH001-2000.png
             ^^^^^^^^ articolo
                       ^^^^^ view_code
    """
    name = path.stem
    parts = name.split("_")
    if len(parts) < 3:
        return None

    article_code = parts[1]
    ph_part = parts[2]

    if not article_code or not ph_part.startswith("PH"):
        return None

    view_code = ph_part[:5]
    rest = ph_part[5:]

    seq_digits = ""
    for ch in rest:
        if ch.isdigit():
            seq_digits += ch
        elif ch == "-":
            break

    seq_num = int(seq_digits) if seq_digits.isdigit() else 0
    return article_code, view_code, seq_num


def convert_png_to_jpg(img_path: Path, log_callback=None) -> Path:
    """Converte PNG in JPG con sfondo bianco e ritorna il nuovo path."""
    new_path = img_path.with_suffix(".jpg")

    if log_callback:
        log_callback(f"PNG → JPG: {img_path.name}")

    with Image.open(img_path) as img:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[3]
            background.paste(img, mask=alpha)
            background.save(new_path, "JPEG", quality=95)
        else:
            rgb = img.convert("RGB")
            rgb.save(new_path, "JPEG", quality=95)

    img_path.unlink()
    return new_path


def rename_nike_images(folder, log_callback=None, progress_callback=None, article_callback=None):
    """
    progress_callback(done, total)
    article_callback(article_code)
    """
    folder = Path(folder)

    if log_callback:
        log_callback(f"[INFO] Cartella: {folder}")

    files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]

    if log_callback:
        log_callback(f"[INFO] Immagini trovate: {len(files)} (JPG + PNG)")

    if not files:
        if log_callback:
            log_callback("[WARN] Nessuna immagine trovata.")
        if progress_callback:
            progress_callback(0, 0)
        return

    converted_files = []
    for f in files:
        if f.suffix.lower() == ".png":
            f = convert_png_to_jpg(f, log_callback=log_callback)
        converted_files.append(f)

    files = converted_files

    images_by_article = {}
    for f in files:
        parsed = parse_filename(f)
        if not parsed:
            if log_callback:
                log_callback(f"[SKIP] Nome non riconosciuto: {f.name}")
            continue

        article_code, view_code, seq_num = parsed
        images_by_article.setdefault(article_code, []).append(
            (f, view_code, seq_num)
        )

    if log_callback:
        log_callback(f"[INFO] Codici articolo: {len(images_by_article)}")

    total_to_process = sum(len(v) for v in images_by_article.values())
    done = 0
    if progress_callback:
        progress_callback(done, total_to_process)

    for article_code, entries in images_by_article.items():
        if log_callback:
            log_callback(f"[ARTICLE] {article_code} – immagini: {len(entries)}")

        if article_callback:
            article_callback(article_code)

        def sort_key(item):
            _, view_code, seq_num = item
            return (VIEW_ORDER.get(view_code, 99), seq_num)

        entries.sort(key=sort_key)

        for idx, (f, view_code, seq_num) in enumerate(entries):
            new_name = f"{article_code}-{idx:02d}.jpg"
            new_path = folder / new_name

            if new_path.exists():
                if log_callback:
                    log_callback(f"[WARN] Esiste già {new_name}, salto.")
            else:
                old_name = f.name
                f.rename(new_path)
                if log_callback:
                    log_callback(f"   {old_name}  →  {new_name}")

            done += 1
            if progress_callback:
                progress_callback(done, total_to_process)

    if article_callback:
        article_callback("")  # reset

    if log_callback:
        log_callback("[OK] Rinomina completata.")


# ---------- FUNZIONI GRAFICHE ----------

def ensure_nike_logo():
    """Scarica il logo Nike dal web se non esiste già."""
    logo_path = Path(NIKE_LOGO_FILE)
    if logo_path.exists():
        return logo_path
    try:
        urllib.request.urlretrieve(NIKE_LOGO_URL, NIKE_LOGO_FILE)
    except Exception:
        return None
    return logo_path


def create_round_rect_image(width, height, radius, fill_color, border_color=None, border_width=0):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [border_width, border_width, width - border_width, height - border_width],
        radius=radius,
        fill=fill_color,
        outline=border_color,
        width=border_width
    )
    return img


# ---------- APP ----------

class NikeRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nike.Net – Media Tool")
        self.root.geometry("1100x650")
        self.root.minsize(950, 550)

        self._set_icon()

        self.bg_color = "#000000"
        self.text_main = "#ffffff"
        self.text_muted = "#e6e6e6"

        self.folder_path = tk.StringVar()

        self.log_queue = queue.Queue()
        self.is_animating = False

        self.bg_image_raw = None
        self.bg_image_tk = None
        self.bg_label = None
        self._load_background()

        self.logo_img_tk = None
        self._load_logo()

        self.round_button_images = {}

        # progress state
        self.progress_var = tk.DoubleVar(value=0.0)
        self.current_article_var = tk.StringVar(value="–")

        self.build_ui()

        self.root.bind("<Configure>", self._on_resize)

    # ---------- ICONA & BACKGROUND ----------

    def _set_icon(self):
        try:
            base = Path(__file__).resolve().parent
        except NameError:
            base = Path(".").resolve()

        ico = base / "nike.ico"
        png = base / "nike.png"
        try:
            if ico.exists():
                self.root.iconbitmap(default=str(ico))
            elif png.exists():
                img = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, img)
                self._icon_keep = img
        except Exception:
            pass

    def _load_background(self):
        try:
            img_path = Path(BACKGROUND_IMAGE_PATH)
            if not img_path.exists():
                self.root.configure(bg=self.bg_color)
                return

            self.bg_image_raw = Image.open(img_path).convert("RGB")
            w, h = self.root.winfo_width() or 1100, self.root.winfo_height() or 650
            resized = self.bg_image_raw.resize((w, h), Image.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(resized)

            self.bg_label = tk.Label(self.root, image=self.bg_image_tk, bd=0, bg=self.bg_color)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()
        except Exception:
            self.root.configure(bg=self.bg_color)

    def _load_logo(self):
        logo_path = ensure_nike_logo()
        if not logo_path or not logo_path.exists():
            return
        try:
            img = Image.open(logo_path).convert("RGBA")
            base_h = 50
            w, h = img.size
            ratio = base_h / h
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            self.logo_img_tk = ImageTk.PhotoImage(img)
        except Exception:
            self.logo_img_tk = None

    def _on_resize(self, event):
        if not self.bg_image_raw or not self.bg_label:
            return
        try:
            resized = self.bg_image_raw.resize((max(event.width, 1), max(event.height, 1)), Image.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(resized)
            self.bg_label.configure(image=self.bg_image_tk)
        except Exception:
            pass

    def _create_button_image(self, key, width, height, radius, fill_color, border_color, border_width):
        img = create_round_rect_image(width, height, radius, fill_color, border_color, border_width)
        tk_img = ImageTk.PhotoImage(img)
        self.round_button_images[key] = tk_img
        return tk_img

    # ---------- UI ----------

    def build_ui(self):
        # card centrale con angoli arrotondati
        canvas = tk.Canvas(self.root, bg=self.bg_color, highlightthickness=0, bd=0)
        canvas.place(relx=0.5, rely=0.55, anchor="center", width=900, height=440)

        card_img = create_round_rect_image(
            900, 440, radius=25, fill_color=(0, 0, 0, 210)
        )
        self.card_img_tk = ImageTk.PhotoImage(card_img)
        canvas.create_image(0, 0, image=self.card_img_tk, anchor="nw")

        content = tk.Frame(canvas, bg="#000000")
        canvas.create_window(450, 220, window=content)

        # logo top-center
        if self.logo_img_tk:
            logo_lbl = tk.Label(self.root, image=self.logo_img_tk, bg=self.bg_color, bd=0)
            logo_lbl.place(relx=0.5, rely=0.12, anchor="center")

        # header
        header = tk.Frame(content, bg="#000000")
        header.pack(fill="x", padx=40, pady=(25, 10))

        title = tk.Label(
            header,
            text="NIKE IMAGE RENAMER",
            fg=self.text_main,
            bg="#000000",
            font=("Helvetica Neue", 18, "bold")
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="Standardizza i media di prodotto per Nike.Net – PNG → JPG, viste ordinate, naming pulito.",
            fg=self.text_muted,
            bg="#000000",
            font=("Helvetica Neue", 10)
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        # selezione cartella
        top = tk.Frame(content, bg="#000000")
        top.pack(fill="x", padx=40, pady=(8, 4))

        lbl = tk.Label(
            top,
            text="ASSET FOLDER",
            fg=self.text_main,
            bg="#000000",
            font=("Helvetica Neue", 9, "bold")
        )
        lbl.pack(anchor="w")

        path_frame = tk.Frame(top, bg="#000000")
        path_frame.pack(fill="x", pady=(6, 0))

        self.entry_folder = tk.Entry(
            path_frame,
            textvariable=self.folder_path,
            bg="#111111",
            fg=self.text_main,
            insertbackground=self.text_main,
            relief="flat",
            font=("Helvetica Neue", 9)
        )
        self.entry_folder.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))

        browse_img = self._create_button_image(
            "browse", 120, 32, radius=16,
            fill_color=(255, 255, 255, 255),
            border_color=(255, 255, 255, 255),
            border_width=0
        )
        self.btn_browse = tk.Button(
            path_frame,
            text="BROWSE",
            image=browse_img,
            compound="center",
            command=self.browse_folder,
            bd=0,
            font=("Helvetica Neue", 9, "bold"),
            fg="#000000",
            bg="#000000",
            activebackground="#000000",
            cursor="hand2"
        )
        self.btn_browse.pack(side="left")

        run_img = self._create_button_image(
            "run", 150, 38, radius=19,
            fill_color=(0, 0, 0, 0),
            border_color=(255, 255, 255, 255),
            border_width=2
        )
        self.btn_start = tk.Button(
            top,
            text="RUN RENAME",
            image=run_img,
            compound="center",
            command=self.start_rename,
            bd=0,
            font=("Helvetica Neue", 10, "bold"),
            fg="#ffffff",
            bg="#000000",
            activebackground="#000000",
            cursor="hand2"
        )
        self.btn_start.pack(anchor="e", pady=(10, 0))

        # progress bar + articolo corrente
        prog_frame = tk.Frame(content, bg="#000000")
        prog_frame.pack(fill="x", padx=40, pady=(8, 4))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Nike.Horizontal.TProgressbar",
            troughcolor="#111111",
            bordercolor="#111111",
            background="#ffffff",
            lightcolor="#ffffff",
            darkcolor="#ffffff"
        )

        self.progress = ttk.Progressbar(
            prog_frame,
            style="Nike.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
            length=400
        )
        self.progress.pack(side="left", fill="x", expand=True, pady=(0, 2))

        article_container = tk.Frame(prog_frame, bg="#000000")
        article_container.pack(side="left", padx=(15, 0))

        lbl_art_title = tk.Label(
            article_container,
            text="ARTICLE:",
            fg=self.text_muted,
            bg="#000000",
            font=("Helvetica Neue", 9, "bold")
        )
        lbl_art_title.pack(side="left")

        self.lbl_article_value = tk.Label(
            article_container,
            textvariable=self.current_article_var,
            fg=self.text_main,
            bg="#000000",
            font=("Helvetica Neue", 10, "bold")
        )
        self.lbl_article_value.pack(side="left", padx=(4, 0))

        # divider
        divider = tk.Frame(content, bg="#333333", height=1)
        divider.pack(fill="x", padx=30, pady=(10, 6))

        lbl_log = tk.Label(
            content,
            text="PROCESS LOG",
            fg=self.text_muted,
            bg="#000000",
            font=("Helvetica Neue", 9, "bold")
        )
        lbl_log.pack(anchor="w", padx=40, pady=(0, 4))

        self.text_log = scrolledtext.ScrolledText(
            content,
            wrap="word",
            height=11,
            bg="#050505",
            fg=self.text_main,
            insertbackground=self.text_main,
            relief="flat",
            font=("Consolas", 9)
        )
        self.text_log.pack(fill="both", expand=True, padx=40, pady=(0, 25))

    # ---------- LOG ANIMATO ----------

    def log(self, message: str):
        self.log_queue.put(message)
        if not self.is_animating:
            self.is_animating = True
            self.root.after(5, self._process_log_queue)

    def _process_log_queue(self):
        if self.log_queue.empty():
            self.is_animating = False
            return
        msg = self.log_queue.get()
        self._animate_message(msg, 0)

    def _animate_message(self, message: str, index: int):
        if index == 0:
            self.text_log.insert("end", "\n")
        if index < len(message):
            self.text_log.insert("end", message[index])
            self.text_log.see("end")
            self.root.update_idletasks()
            self.root.after(10, self._animate_message, message, index + 1)
        else:
            self.root.after(25, self._process_log_queue)

    # ---------- UPDATE PROGRESS / ARTICLE (THREAD-SAFE) ----------

    def progress_update_from_thread(self, done, total):
        self.root.after(0, self._update_progress_ui, done, total)

    def _update_progress_ui(self, done, total):
        if total <= 0:
            self.progress_var.set(0)
            return
        value = (done / total) * 100.0
        self.progress_var.set(value)

    def article_update_from_thread(self, article_code):
        self.root.after(0, self._update_article_ui, article_code)

    def _update_article_ui(self, article_code):
        if article_code:
            self.current_article_var.set(article_code)
        else:
            self.current_article_var.set("–")

    # ---------- EVENTI GUI ----------

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Nike asset folder")
        if folder:
            self.folder_path.set(folder)
            self.log(f"[UI] Folder selected: {folder}")

    def start_rename(self):
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showerror("Error", "Seleziona una cartella con gli asset.")
            return

        path_obj = Path(folder)
        if not path_obj.exists():
            messagebox.showerror("Error", f"La cartella non esiste:\n{folder}")
            return
        if not path_obj.is_dir():
            messagebox.showerror("Error", f"Il percorso non è una cartella:\n{folder}")
            return

        # reset progress & articolo
        self.progress_var.set(0)
        self.current_article_var.set("–")

        self.btn_start.config(state="disabled")
        self.log("====== RUN ======")
        self.log("[UI] Avvio processo di rinomina...")

        threading.Thread(
            target=self._run_thread,
            args=(path_obj,),
            daemon=True
        ).start()

    def _run_thread(self, folder: Path):
        try:
            rename_nike_images(
                folder,
                log_callback=self.log,
                progress_callback=self.progress_update_from_thread,
                article_callback=self.article_update_from_thread
            )
        except Exception as e:
            self.log(f"[ERROR] {e}")
            messagebox.showerror("Error", f"Si è verificato un errore:\n{e}")
        finally:
            self.btn_start.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = NikeRenamerApp(root)
    root.mainloop()
