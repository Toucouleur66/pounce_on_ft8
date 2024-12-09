# builder.py

import subprocess
import platform
import sys
import os
import PyQt6.QtCore

from constants import CURRENT_VERSION_NUMBER

# app_name = f"Wait & Pounce v{CURRENT_VERSION_NUMBER}"
app_name = f"WaitAndPounce"

def generate_info_plist(version_number):
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.citronpresse.waitandpounce</string>
    <key>CFBundleShortVersionString</key>
    <string>{version_number}</string>
    <key>CFBundleVersion</key>
    <string>{version_number}</string>
</dict>
</plist>
"""
    plist_path = os.path.join("dist", "Info.plist")
    os.makedirs("dist", exist_ok=True) 
    with open(plist_path, "w") as plist_file:
        plist_file.write(plist_content)
    return plist_path

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
        "--add-data=pounce.png:.",
        "--add-data=sounds;sounds",
        "--add-data=cty.xml;.",
        f'--add-binary={qt_plugins_path};PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=Foundation',
        '--hidden-import=objc',
        '--noconfirm',
    ]
elif platform.system() == 'Darwin':
    plist_path = generate_info_plist(CURRENT_VERSION_NUMBER)
    
    pyinstaller_cmd = common_options + [
        "--windowed",
        "--icon=pounce.icns",
        "--add-data=pounce.png:.",
        "--add-data=sounds:sounds",
        "--add-data=cty.xml:.",
        f'--add-binary={qt_plugins_path}:PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=Foundation',
        '--hidden-import=objc',
        '--noconfirm',
    ]

    def post_process():
        app_path = f"dist/{app_name}.app"
        plist_dest = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.exists(app_path):
            print(f"Copying {plist_path} to {plist_dest}")
            os.makedirs(os.path.dirname(plist_dest), exist_ok=True)
            subprocess.run(["cp", plist_path, plist_dest], check=True)
        else:
            print("Error: Application bundle not found. Skipping Info.plist copy.")

# Run the PyInstaller command
subprocess.run(pyinstaller_cmd)
