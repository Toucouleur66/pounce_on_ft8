# builder.py

import subprocess
import platform
import sys
import os
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets

print(PyQt6.QtCore.QT_VERSION_STR)
print(PyQt6.QtWidgets.QStyleFactory.keys())

from constants import CURRENT_VERSION_NUMBER
from termcolor import colored 

# app_name = f"Wait & Pounce v{CURRENT_VERSION_NUMBER}"
app_name = f"WaitAndPounce"

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
        "--add-data=cq-zones.geojson:.",
        f'--add-binary={qt_plugins_path};PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=Foundation',
        '--hidden-import=numpy._globals',
        '--hidden-import=shapely',        
        '--hidden-import=objc',
        '--noconfirm',
    ]
elif platform.system() == 'Darwin':
    pyinstaller_cmd = common_options + [
        "--windowed",
        "--icon=pounce.icns",
        "--add-data=pounce.png:.",
        "--add-data=sounds:sounds",
        "--add-data=cty.xml:.",
        "--add-data=cq-zones.geojson:.",
        f'--add-binary={qt_plugins_path}:PyQt6/Qt6/plugins/multimedia',
        '--hidden-import=Foundation',
        '--hidden-import=objc',
        '--noconfirm',
    ]    

# Run the PyInstaller command
subprocess.run(pyinstaller_cmd)

if platform.system() == 'Darwin':
    def generate_info_plist(version_number):
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>CFBundleName</key>
            <string>WaitAndPounce</string>

            <key>CFBundleIdentifier</key>
            <string>com.f5ukw.waitandpounce</string>

            <key>CFBundleExecutable</key>
            <string>WaitAndPounce</string>

            <key>CFBundlePackageType</key>
            <string>APPL</string>
            
            <key>CFBundleShortVersionString</key>
            <string>{version_number}</string>
            
            <key>CFBundleVersion</key>
            <string>{version_number}</string>
            
            <key>CFBundleIconFile</key>
            <string>pounce.icns</string>
        </dict>
        </plist>
        """
        plist_path = os.path.join("dist", "Info.plist")
        os.makedirs("dist", exist_ok=True) 
        with open(plist_path, "w") as plist_file:
            plist_file.write(plist_content)
        return plist_path
   
    plist_path = generate_info_plist(CURRENT_VERSION_NUMBER)

    def post_process(plist_path):
        app_path = f"dist/{app_name}.app"
        plist_dest = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.exists(app_path):
            print(f"Copying {plist_path} to {plist_dest}")
            os.makedirs(os.path.dirname(plist_dest), exist_ok=True)
            subprocess.run(["cp", plist_path, plist_dest], check=True)
        else:
            print("Error: Application bundle not found. Skipping Info.plist copy.")

    post_process(plist_path)

    print(colored(f"[INFO] Build READY", "yellow"))