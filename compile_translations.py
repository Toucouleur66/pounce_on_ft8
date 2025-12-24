#!/usr/bin/env python3
"""
.ts to .qm compiler for translations

This script compiles .ts XML files to .qm binary files that Qt can use.
Uses the official lrelease tool for proper Qt translation format.
"""

import os
import sys
import subprocess
import shutil

def find_lrelease():
    """Find lrelease executable"""
    # Try common names for lrelease
    for cmd in ['lrelease', 'lrelease-qt6', 'pyside6-lrelease', 'lrelease-qt5']:
        if shutil.which(cmd):
            return cmd
    return None

def compile_ts_to_qm(ts_file, qm_file):
    """
    Compile .ts XML file to .qm binary format using lrelease

    Args:
        ts_file: Path to source .ts file
        qm_file: Path to output .qm file

    Returns:
        True if compilation succeeded, False otherwise
    """
    lrelease_cmd = find_lrelease()

    if not lrelease_cmd:
        print(f"✗ lrelease not found. Please install Qt tools.")
        print(f"  On macOS: brew install qt")
        print(f"  On Ubuntu/Debian: sudo apt install qttools5-dev-tools")
        return False

    try:
        # Run lrelease to compile .ts to .qm
        result = subprocess.run(
            [lrelease_cmd, ts_file, '-qm', qm_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Count translations
            translation_count = 0
            if "Generated" in result.stdout:
                import re
                match = re.search(r'Generated (\d+) translation', result.stdout)
                if match:
                    translation_count = int(match.group(1))

            print(f"✓ Compiled {os.path.basename(ts_file)} → {os.path.basename(qm_file)}")
            if translation_count > 0:
                print(f"  {translation_count} translations")
            return True
        else:
            print(f"✗ Failed to compile {ts_file}")
            if result.stderr:
                print(f"  Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ Failed to compile {ts_file}: {e}")
        return False

def main():
    translations_dir = 'translations'

    if not os.path.exists(translations_dir):
        print(f"Error: {translations_dir} directory not found")
        return 1

    print("=" * 70)
    print("Compiling Translation Files (.ts → .qm)")
    print("=" * 70)
    print()

    # Find all .ts files
    ts_files = [f for f in os.listdir(translations_dir) if f.endswith('.ts')]

    if not ts_files:
        print(f"No .ts files found in {translations_dir}/")
        return 1

    success_count = 0
    for ts_filename in ts_files:
        ts_path = os.path.join(translations_dir, ts_filename)
        qm_filename = ts_filename.replace('.ts', '.qm')
        qm_path = os.path.join(translations_dir, qm_filename)

        if compile_ts_to_qm(ts_path, qm_path):
            success_count += 1

    print()
    print("=" * 70)
    print(f"Compiled {success_count}/{len(ts_files)} translation files")
    print("=" * 70)

    if success_count > 0:
        print("\n✓ Translations ready to use!")
        print(f"\nCompiled files in {translations_dir}/:")
        for f in os.listdir(translations_dir):
            if f.endswith('.qm'):
                print(f"  - {f}")

    return 0 if success_count == len(ts_files) else 1

if __name__ == '__main__':
    sys.exit(main())
