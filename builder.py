# builder.py

import subprocess
import platform

from constants import (
    version_number
)

app_name = f"Wait & Pounce v{version_number}"

if platform.system() == 'Windows':
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--collect-submodules"
        "PIL"
        "--icon=pounce.ico",
        "--add-data=pounce.ico;.",
        "--add-data=sounds:sounds",
        "--add-data=cty.xml:.",
        f"--name={app_name}",
        "pounce_gui.pyw"
    ]
elif platform.system() == 'Darwin':
    pyinstaller_cmd = [
        "pyinstaller",
        "--windowed",
        "--icon=pounce.icns",
        "--hidden-import=sip",
        "--add-data=sounds:sounds",
        "--add-data=cty.xml:.",
        f"--name={app_name}",
        "pounce_gui.pyw"
    ]

subprocess.run(pyinstaller_cmd)