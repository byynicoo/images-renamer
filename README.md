# images-renamer

Python scripts to **rename `.jpg` images in a consistent and structured way**, designed for product catalogs, photoshoots, and e-commerce workflows.

> The repository includes brand-specific scripts (`Nike`, `adidas`, `New Balance`).

---

## What it does

- Scans a folder containing `.jpg` images  
- Renames files according to a **standard naming convention**  
- (Optional, depending on the script) handles:
  - progressive numbering
  - filename normalization (spaces, special characters, etc.)

> ⚠️ The actual naming rules depend on the logic implemented in each brand script.

---

## Requirements

- **Python 3.10+** (recommended)  
- No external dependencies (only Python standard library)

Check your Python version:
```bash
python --version
```

---

## Installation

Clone the repository:
```bash
git clone https://github.com/byynicoo/images-renamer.git
cd images-renamer
```

---

## Usage

### 1) Prepare your images

Place all `.jpg` images inside a folder (e.g. `./images/`) and **create a backup** before running any script.

Example structure:
```text
images-renamer/
  renamer_nike.py
  renamer_adidas.py
  renamer_newbalance.py
  images/
    IMG_0001.jpg
    IMG_0002.jpg
```

---

### 2) Run the brand-specific script

**Nike**
```bash
python renamer_nike.py
```

**adidas**
```bash
python renamer_adidas.py
```

**New Balance**
```bash
python renamer_newbalance.py
```

> If the script requires parameters (input/output folder, SKU, prefix, etc.), check the configuration section at the top of the `.py` file or any runtime `input()` prompts.

---

## Configuration (recommended)

Scripts can be customized using variables such as:

- `INPUT_DIR`: source images folder  
- `OUTPUT_DIR`: destination folder (recommended to avoid overwriting)  
- `START_INDEX`: starting progressive number  
- `SKU` / `MODEL_CODE`: product identifier  
- `COLOR_CODE` / `COLOR_NAME`: if required  
- `VIEW` / `ANGLE`: image view (e.g. `01_front`, `02_back`)

Example:
```py
INPUT_DIR = "./images"
OUTPUT_DIR = "./renamed"
SKU = "DV1234-001"
START_INDEX = 1
```

---

## Naming Convention Example

> ⚠️ Replace this with the real convention used in your scripts.

Simple example:
```text
<SKU>_<index>.jpg
DV1234-001_01.jpg
DV1234-001_02.jpg
```

Detailed example:
```text
<brand>_<sku>_<color>_<view>.jpg
nike_DV1234-001_black_01.jpg
```

---

## Important Notes

- **Always back up your files** before renaming  
- Prefer using a separate output folder  
- Avoid running the script multiple times on already renamed images  
- Consider adding a `dry-run` mode before batch renaming  

---

## Roadmap

- [ ] `--dry-run` preview mode  
- [ ] CLI arguments (`--input`, `--output`, `--sku`, `--start`)  
- [ ] CSV log file (old name → new name)  
- [ ] Single entrypoint (`main.py`) with brand selection  

---
