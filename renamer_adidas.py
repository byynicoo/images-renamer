import os
from pathlib import Path
from PIL import Image

# cartella dove si trovano le immagini
FOLDER = "/Users/nicolo.morando/Downloads/nb"

# estensioni immagini da convertire
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def convert_all_to_jpg(folder: Path):
    """Converte tutte le immagini della cartella in JPG.
       I file non-JPG vengono convertiti in JPG e poi eliminati."""
    files = [f for f in folder.iterdir() if f.is_file()]

    for f in files:
        ext = f.suffix.lower()
        if ext not in IMAGE_EXTS:
            continue

        # se è già jpg, non facciamo nulla
        if ext == ".jpg":
            continue

        new_path = f.with_suffix(".jpg")

        # se esiste già un jpg con quel nome, salta per sicurezza
        if new_path.exists():
            print(f"⚠️ Esiste già {new_path.name}, salto conversione di {f.name}")
            continue

        try:
            with Image.open(f) as img:
                # gestiamo trasparenza con sfondo bianco
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    img = img.convert("RGBA")
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    alpha = img.split()[3]
                    background.paste(img, mask=alpha)
                    background.save(new_path, "JPEG", quality=95)
                else:
                    rgb = img.convert("RGB")
                    rgb.save(new_path, "JPEG", quality=95)
            print(f"🔄 Convertito {f.name} → {new_path.name}")
            # elimina l'originale dopo conversione
            f.unlink()
        except Exception as e:
            print(f"❌ Errore convertendo {f.name}: {e}")


def rename_images(folder):
    folder = Path(folder)

    # 1) converte tutto in JPG prima di qualsiasi cosa
    convert_all_to_jpg(folder)

    # 2) prendi solo file .jpg
    files = sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() == ".jpg"
    ])

    # ---- CONTEGGIO PREFISSI ----
    prefixes = set()

    for f in files:
        name = f.stem
        prefix = name[:6]
        prefixes.add(prefix)

    print(f"📦 Trovati {len(prefixes)} codici diversi")
    print(f"Prefissi identificati: {sorted(prefixes)}\n")

    # ---- PROCESSO DI RINOMINA ----
    current_prefix = None
    counter = 0

    for f in files:
        name = f.stem
        ext = ".jpg"

        prefix = name[:6]

        # reset contatore se cambia prefisso
        if prefix != current_prefix:
            current_prefix = prefix
            counter = 0

        new_name = f"{prefix}-{counter:02d}{ext}"
        counter += 1

        new_path = folder / new_name

        if new_path.exists():
            print(f"⚠️ WARNING: {new_name} esiste già, salto.")
            continue

        f.rename(new_path)
        print(f"Renamed: {f.name} → {new_name}")


if __name__ == "__main__":
    rename_images(FOLDER)
