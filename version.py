# version.py

import json
import os

from constants import (
    SAVED_VERSION_FILE
)

def is_first_launch_or_new_version(current_version):  
    if not os.path.exists(SAVED_VERSION_FILE):
        return True

    with open(SAVED_VERSION_FILE, "r") as f:
        state = json.load(f)
    
    saved_version = state.get("version")
    return saved_version != current_version

def save_current_version(current_version):
    with open(SAVED_VERSION_FILE, "w") as f:
        json.dump({"version": current_version}, f)