#!/usr/bin/env python3
"""
Generate translation files (.ts) for Qt Linguist

This script extracts translatable strings from Python files and generates
.ts files that can be edited with Qt Linguist.

Usage:
    python generate_translations.py

This will generate:
    - translations/pounce_en.ts (English baseline)
    - translations/pounce_fr.ts (French template)
    - ... (add more languages as needed)
"""

import os
import subprocess
import sys

# Files to scan for translatable strings
SOURCE_FILES = [
    'pounce_gui.pyw',
    'setting_dialog.py',
    'grid_map_viewer.py',
    'adif_summary_dialog.py',
    'active_users_window.py',
    'translatable_strings.py',
    'context_menu_handler.py',
]

# Languages to generate translation files for
LANGUAGES = [
    'en',  # English (baseline)
    'fr',  # French
    'zh',  # Chinese (Simplified)
]

# Translation directory
TRANSLATIONS_DIR = 'translations'

def ensure_translations_dir():
    """Create translations directory if it doesn't exist"""
    if not os.path.exists(TRANSLATIONS_DIR):
        os.makedirs(TRANSLATIONS_DIR)
        print(f"Created directory: {TRANSLATIONS_DIR}")

def check_pylupdate():
    """Check if pylupdate6 is available"""
    try:
        result = subprocess.run(['pylupdate6', '-version'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            print(f"Found pylupdate6: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("ERROR: pylupdate6 not found!")
    print("Please install PyQt6 development tools:")
    print("  pip install PyQt6")
    print("\nOr on macOS with Homebrew:")
    print("  brew install qt6")
    return False

def generate_ts_file(language):
    """Generate .ts translation file for specified language"""
    ts_file = os.path.join(TRANSLATIONS_DIR, f'pounce_{language}.ts')

    # Build command
    cmd = ['pylupdate6']

    # Add all source files
    for source_file in SOURCE_FILES:
        if os.path.exists(source_file):
            cmd.append(source_file)
        else:
            print(f"Warning: Source file not found: {source_file}")

    # Add output file
    cmd.extend(['-ts', ts_file])

    print(f"\nGenerating {ts_file}...")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ Successfully generated {ts_file}")
            if result.stdout:
                print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ Failed to generate {ts_file}")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout generating {ts_file}")
        return False
    except Exception as e:
        print(f"✗ Exception generating {ts_file}: {e}")
        return False

def compile_ts_file(language):
    """Compile .ts file to .qm binary format"""
    ts_file = os.path.join(TRANSLATIONS_DIR, f'pounce_{language}.ts')
    qm_file = os.path.join(TRANSLATIONS_DIR, f'pounce_{language}.qm')

    if not os.path.exists(ts_file):
        print(f"Warning: {ts_file} not found, skipping compilation")
        return False

    print(f"\nCompiling {ts_file} to {qm_file}...")

    try:
        cmd = ['lrelease', ts_file, '-qm', qm_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ Successfully compiled {qm_file}")
            return True
        else:
            print(f"✗ Failed to compile {qm_file}")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            return False

    except FileNotFoundError:
        print("Warning: lrelease not found. .qm file not generated.")
        print("Install Qt6 tools to compile translations.")
        return False
    except Exception as e:
        print(f"✗ Exception compiling {qm_file}: {e}")
        return False

def create_readme():
    """Create README for translations directory"""
    readme_path = os.path.join(TRANSLATIONS_DIR, 'README.md')

    content = """# Translations

This directory contains translation files for Wait and Pounce.

## File Types

- `.ts` files: Translation source files (XML format)
  - Edit these with Qt Linguist
  - Human-readable
  - Version controlled

- `.qm` files: Compiled translation files (binary format)
  - Used by the application at runtime
  - Generated from .ts files
  - Not version controlled

## Workflow

### 1. Generate/Update Translation Files

Run the generation script to extract all translatable strings:

```bash
python generate_translations.py
```

This creates/updates .ts files for all configured languages.

### 2. Translate Strings

Open the .ts files in Qt Linguist:

```bash
linguist translations/pounce_fr.ts
```

Or use any text editor - .ts files are XML.

### 3. Compile Translations

Compile .ts files to .qm for use in the application:

```bash
lrelease translations/pounce_fr.ts -qm translations/pounce_fr.qm
```

Or use the generation script with compile option.

### 4. Test Translations

Run the application and select the language from settings.

## Adding a New Language

1. Edit `generate_translations.py`
2. Add language code to `LANGUAGES` list:
   ```python
   LANGUAGES = [
       'en',  # English
       'fr',  # French
       'es',  # Spanish (new)
   ]
   ```
3. Run generation script
4. Translate the new .ts file
5. Compile to .qm

## Language Codes

Use ISO 639-1 two-letter codes:
- en: English
- fr: French (Français)
- de: German (Deutsch)
- es: Spanish (Español)
- it: Italian (Italiano)
- pt: Portuguese (Português)
- ja: Japanese (日本語)
- zh: Chinese (中文)

## Qt Linguist

Qt Linguist is a visual translation tool included with Qt.

### Installation

**macOS:**
```bash
brew install qt6
```

**Windows:**
Download Qt installer from qt.io

**Linux:**
```bash
sudo apt install qttools5-dev-tools  # Qt5
sudo apt install qt6-tools-dev       # Qt6
```

### Usage

```bash
linguist translations/pounce_fr.ts
```

## Tools

- `pylupdate6`: Extract strings from Python files → .ts
- `lrelease`: Compile .ts files → .qm
- `linguist`: Visual translation editor (GUI)

## Resources

- [Qt Linguist Manual](https://doc.qt.io/qt-6/qtlinguist-index.html)
- [Internationalization with Qt](https://doc.qt.io/qt-6/internationalization.html)
"""

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\nCreated {readme_path}")

def main():
    print("=" * 70)
    print("Wait and Pounce - Translation File Generator")
    print("=" * 70)

    # Check prerequisites
    if not check_pylupdate():
        sys.exit(1)

    # Ensure translations directory exists
    ensure_translations_dir()

    # Generate .ts files for each language
    print("\n" + "=" * 70)
    print("GENERATING TRANSLATION FILES (.ts)")
    print("=" * 70)

    success_count = 0
    for language in LANGUAGES:
        if generate_ts_file(language):
            success_count += 1

    print(f"\nGenerated {success_count}/{len(LANGUAGES)} translation files")

    # Compile .ts files to .qm
    print("\n" + "=" * 70)
    print("COMPILING TRANSLATION FILES (.qm)")
    print("=" * 70)

    compile_count = 0
    for language in LANGUAGES:
        if compile_ts_file(language):
            compile_count += 1

    if compile_count > 0:
        print(f"\nCompiled {compile_count}/{len(LANGUAGES)} translation files")

    # Create README
    create_readme()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Generated {success_count} .ts files in {TRANSLATIONS_DIR}/")
    print(f"✓ Compiled {compile_count} .qm files")

    if success_count > 0:
        print("\nNext steps:")
        print("1. Edit .ts files with Qt Linguist or text editor")
        print("2. Recompile with: lrelease translations/pounce_*.ts")
        print("3. Test in application")

    print("\n" + "=" * 70)

if __name__ == '__main__':
    main()
