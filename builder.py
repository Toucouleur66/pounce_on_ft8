# builder.py

import subprocess
import platform
import sys
import os
import PyQt6.QtCore

from constants import version_number

app_name = f"Wait & Pounce v{version_number}"

# Common options for PyInstaller
common_options = [
    sys.executable,
    "-m", "PyInstaller",
    "--clean",
    f"--name={app_name}",
    "pounce_gui.pyw"
]

# Get the path to the QtMultimedia plugins
qt_plugins_path = os.path.join(
    PyQt6.QtCore.QLibraryInfo.path(PyQt6.QtCore.QLibraryInfo.LibraryPath.PluginsPath),
    'multimedia'
)

if platform.system() == 'Windows':
    pyinstaller_cmd = common_options + [
        "--onefile",
        "--collect-submodules", "PIL",
        "--icon=pounce.ico",
        "--add-data=pounce.ico;.",
        "--add-data=sounds;sounds",
        "--add-data=cty.xml;.",
        f'--add-binary={qt_plugins_path};PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=Foundation',
        '--hidden-import=objc',
    ]
elif platform.system() == 'Darwin':
    pyinstaller_cmd = common_options + [
        "--windowed",
        "--icon=pounce.icns",
        "--add-data=sounds:sounds",
        "--add-data=cty.xml:.",
        f'--add-binary={qt_plugins_path}:PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=Foundation',
        '--hidden-import=objc',
    ]

# Run the PyInstaller command
subprocess.run(pyinstaller_cmd)
