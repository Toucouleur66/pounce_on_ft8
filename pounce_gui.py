import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import pickle
import os
import threading

PARAMS_FILE = "params.pkl"

def force_uppercase(*args):
    value = your_callsign_var.get()
    your_callsign_var.set(value.upper())

    value = callsign_var.get()
    callsign_var.set(value.upper())

def load_params():
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_params(params):
    with open(PARAMS_FILE, "wb") as f:
        pickle.dump(params, f)

def run_script():
    instance_type = instance_var.get()
    frequencies = frequency_var.get()
    time_hopping = time_hopping_var.get()
    callsign = callsign_var.get()
    your_callsign = your_callsign_var.get()
    mode = mode_var.get() 
    
    if not callsign:
        messagebox.showerror("Erreur", "Le champ Call Sign est obligatoire")
        return

    params = {
        "instance": instance_type,
        "frequencies": frequencies,
        "time_hopping": time_hopping,
        "callsign": callsign,
        "your_callsign": your_callsign,
        "mode": mode 
    }
    save_params(params)
    
    cmd = f"python wait_and_pounce.py -wc {callsign} -yc {your_callsign_var.get()}"
    if instance_type:
        cmd += f" -i {instance_type}"
    if frequencies:
        cmd += f" -fh {frequencies}"
    if time_hopping:
        cmd += f" -th {time_hopping}"
    if mode:
        cmd += f" -m {mode}"
    
    def target():
        try:
            run_button.config(state="disabled", background="red", text="Running...")
            subprocess.run(cmd, shell=True, check=True)
            messagebox.showinfo("Succès", "Script exécuté avec succès")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exécution du script : {e}")
        finally:
            run_button.config(state="normal", background="SystemButtonFace", text="Run Script")
    
    thread = threading.Thread(target=target)
    thread.start()

def stop_script():
    for thread in threading.enumerate():
        if thread.name == "ProcessQueue":
            stop_event.set()
            run_button.config(state="normal", background="SystemButtonFace", text="Run Script")
            messagebox.showinfo("Interruption", "Script interrompu")

# Charger les paramètres précédemment sauvegardés
params = load_params()

# Création de la fenêtre principale
root = tk.Tk()
root.title("Wait and Pounce")

# Variables
your_callsign_var = tk.StringVar(value=params.get("your_callsign", ""))
instance_var = tk.StringVar(value=params.get("instance", "JTDX"))
frequency_var = tk.StringVar(value=params.get("frequencies", ""))
time_hopping_var = tk.StringVar(value=params.get("time_hopping", ""))
callsign_var = tk.StringVar(value=params.get("callsign", ""))
mode_var = tk.StringVar(value=params.get("mode", "Normal"))

your_callsign_var.trace_add("write", force_uppercase)
callsign_var.trace_add("write", force_uppercase)

# Création des widgets
ttk.Label(root, text="Instance to monitor:").grid(column=0, row=0, padx=10, pady=5, sticky=tk.W)
instance_combo = ttk.Combobox(root, textvariable=instance_var, values=["JTDX", "WSJT"])
instance_combo.grid(column=1, row=0, padx=10, pady=5)

ttk.Label(root, text="Your Call:").grid(column=0, row=1, padx=10, pady=5, sticky=tk.W)
your_callsign_entry = ttk.Entry(root, textvariable=your_callsign_var)
your_callsign_entry.grid(column=1, row=1, padx=10, pady=5)

ttk.Label(root, text="Frequencies (comma-separated):").grid(column=0, row=2, padx=10, pady=5, sticky=tk.W)
frequency_entry = ttk.Entry(root, textvariable=frequency_var)
frequency_entry.grid(column=1, row=2, padx=10, pady=5)

ttk.Label(root, text="Time Hopping (minutes):").grid(column=0, row=3, padx=10, pady=5, sticky=tk.W)
time_hopping_entry = ttk.Entry(root, textvariable=time_hopping_var)
time_hopping_entry.grid(column=1, row=3, padx=10, pady=5)

ttk.Label(root, text="Call Sign:").grid(column=0, row=4, padx=10, pady=5, sticky=tk.W)
callsign_entry = ttk.Entry(root, textvariable=callsign_var)
callsign_entry.grid(column=1, row=4, padx=10, pady=5)

ttk.Label(root, text="Mode:").grid(column=0, row=5, padx=10, pady=5, sticky=tk.W)
mode_combo = ttk.Combobox(root, textvariable=mode_var, values=["Normal", "Fox/Hound", "SuperFox"])
mode_combo.grid(column=1, row=5, padx=10, pady=5)

run_button = tk.Button(root, text="Click to Wait & Pounce", command=run_script)
run_button.grid(column=0, row=5, padx=10, pady=10)

stop_button = tk.Button(root, text="Stop all", command=stop_script)
stop_button.grid(column=1, row=5, padx=10, pady=10)

# Exécution de la boucle principale
root.mainloop()
