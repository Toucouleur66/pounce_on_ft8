# Building from Source

Wait and Pounce is a Python application packaged with **PyInstaller**. This page covers running it
from source and producing distributables.

## Prerequisites

- **Python 3** (the project pins **PyQt6 6.8** — use a matching CPython, 3.11/3.12 recommended).
- Platform build tools for PyInstaller (standard on Windows/macOS).

## Install dependencies

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Key dependencies (`requirements.txt`): `PyQt6`, `PyQt6-SwitchControl`, `numpy`, `shapely`,
`maidenhead`, `requests`, `pyperclip`, `Pillow`, `Pympler`, `termcolor`, and `pyinstaller`.

## Run from source

The entry point is **`pounce_gui.pyw`**:

```bash
python pounce_gui.pyw
```

## Build a distributable

The project includes a build helper, `builder.py`, which invokes PyInstaller with the right
options per platform:

```bash
python builder.py
```

It builds an app named **`WaitAndPounce`**:

- **Windows** — `--onefile`, with `--additional-hooks-dir=.` and a custom `hook-pywinauto.py` so
  the JTDX auto-click dependency (`pywinauto`) is bundled. May collect `PIL` / `win32com`
  submodules and the QtMultimedia plugins.
- **macOS** — produces a `.app` bundle; a companion **StatusMenuAgent** (`StatusMenuAgent.spec`)
  provides the menu-bar icon, and `window_titles_monitor` is a small helper.

Spec files present: `WaitAndPounce.spec`, `StatusMenuAgent.spec`, `window_titles_monitor.spec`.

::: tip Bundled data
The build must include the reference data and assets (`cty.xml`, `CTY_WT_MOD.DAT`, `cq-zones.go`,
`GRD_WP.txt`, `sounds/`, `translations/`, icons). These are referenced relative to the program
directory at runtime.
:::

## Translations

UI strings live in `translatable_strings.py`. Helper scripts compile them into Qt `.qm` files:

- `generate_translations.py` — generate/update `.ts` sources.
- `compile_translations.py` — compile `.ts` → `.qm` (committed so Windows builds find them).

After changing strings, regenerate and recompile so all five languages stay current.

## Project conventions

- Logging goes through `logger.py` (`iLog`) — a rotating file handler; never use ad-hoc prints for
  persistent logs.
- Code and identifiers are written in **English** regardless of UI language.
