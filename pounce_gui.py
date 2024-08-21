import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import pickle
import os
import threading

PARAMS_FILE = "params.pkl"

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
    call_sign = call_sign_var.get()
    your_call = your_call_var.get()
    
    if not call_sign:
        messagebox.showerror("Erreur", "Le champ Call Sign est obligatoire")
        return

    params = {
        "instance": instance_type,
        "frequencies": frequencies,
        "time_hopping": time_hopping,
        "call_sign": call_sign,
        "your_call": your_call
    }
    save_params(params)
    
    cmd = f"python wait_and_pounce.py -c {call_sign} -yc {your_call_var.get()}"
    if instance_type:
        cmd += f" -i {instance_type}"
    if frequencies:
        cmd += f" -fh {frequencies}"
    if time_hopping:
        cmd += f" -th {time_hopping}"
    
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
your_call_var = tk.StringVar(value=params.get("your_call", ""))
instance_var = tk.StringVar(value=params.get("instance", "JTDX"))
frequency_var = tk.StringVar(value=params.get("frequencies", ""))
time_hopping_var = tk.StringVar(value=params.get("time_hopping", ""))
call_sign_var = tk.StringVar(value=params.get("call_sign", ""))

# Création des widgets

ttk.Label(root, text="Instance to monitor:").grid(column=0, row=0, padx=10, pady=5, sticky=tk.W)
instance_combo = ttk.Combobox(root, textvariable=instance_var, values=["JTDX", "WSJT"])
instance_combo.grid(column=1, row=0, padx=10, pady=5)

ttk.Label(root, text="Your Call:").grid(column=0, row=1, padx=10, pady=5, sticky=tk.W)
your_call_entry = ttk.Entry(root, textvariable=your_call_var)
your_call_entry.grid(column=1, row=1, padx=10, pady=5)

ttk.Label(root, text="Frequencies (comma-separated):").grid(column=0, row=2, padx=10, pady=5, sticky=tk.W)
frequency_entry = ttk.Entry(root, textvariable=frequency_var)
frequency_entry.grid(column=1, row=2, padx=10, pady=5)

ttk.Label(root, text="Time Hopping (minutes):").grid(column=0, row=3, padx=10, pady=5, sticky=tk.W)
time_hopping_entry = ttk.Entry(root, textvariable=time_hopping_var)
time_hopping_entry.grid(column=1, row=3, padx=10, pady=5)

ttk.Label(root, text="Call Sign:").grid(column=0, row=4, padx=10, pady=5, sticky=tk.W)
call_sign_entry = ttk.Entry(root, textvariable=call_sign_var)
call_sign_entry.grid(column=1, row=4, padx=10, pady=5)

run_button = tk.Button(root, text="Click to Wait & Pounce", command=run_script)
run_button.grid(column=0, row=5, padx=10, pady=10)

stop_button = tk.Button(root, text="Stop all", command=stop_script)
stop_button.grid(column=1, row=5, padx=10, pady=10)

# Exécution de la boucle principale
root.mainloop()
