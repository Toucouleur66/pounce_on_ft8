import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import pickle
import os
import threading

PARAMS_FILE = "params.pkl"
WANTED_CALLSIGNS_FILE = "wanted_callsigns.pkl"  
MAX_HISTORY = 10  

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

def load_wanted_callsigns():
    if os.path.exists(WANTED_CALLSIGNS_FILE):
        with open(WANTED_CALLSIGNS_FILE, "rb") as f:
            return pickle.load(f)
    return []

def save_wanted_callsigns(wanted_callsigns_history):
    with open(WANTED_CALLSIGNS_FILE, "wb") as f:
        pickle.dump(wanted_callsigns_history, f)

def update_wanted_callsigns_history(new_callsign):
    if new_callsign:
        if new_callsign not in wanted_callsigns_history:
            wanted_callsigns_history.append(new_callsign)
            # Limiter à 10 entrées
            if len(wanted_callsigns_history) > MAX_HISTORY:
                wanted_callsigns_history.pop(0)
            save_wanted_callsigns(wanted_callsigns_history)
            # Met à jour la Listbox
            update_listbox()

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

    # Mettre à jour et sauvegarder l'historique des wanted_callsigns
    update_wanted_callsigns_history(callsign)

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

def update_listbox():
    listbox.delete(0, tk.END) 
    for callsign in wanted_callsigns_history:
        listbox.insert(tk.END, callsign)  

def on_listbox_select(event):
    selection = listbox.curselection()
    if selection:
        selected_callsign = listbox.get(selection[0])
        callsign_var.set(selected_callsign) 

# Charger les paramètres précédemment sauvegardés
params = load_params()

# Charger l'historique des wanted_callsigns
wanted_callsigns_history = load_wanted_callsigns()

# Création de la fenêtre principale
root = tk.Tk()
root.geometry("900x270")
root.grid_columnconfigure(2, weight=1) 
root.grid_columnconfigure(3, weight=1) 
root.grid_columnconfigure(4, weight=1) 
root.title("Wait and Pounce (by F5UKW under GNU GPL Licence)")

# Variables
your_callsign_var = tk.StringVar(value=params.get("your_callsign", ""))
instance_var = tk.StringVar(value=params.get("instance", "JTDX"))
frequency_var = tk.StringVar(value=params.get("frequencies", ""))
time_hopping_var = tk.StringVar(value=params.get("time_hopping", ""))
callsign_var = tk.StringVar(value=params.get("callsign", ""))
mode_var = tk.StringVar(value=params.get("mode", "Normal"))

your_callsign_var.trace_add("write", force_uppercase)
callsign_var.trace_add("write", force_uppercase)

courier_font = ("Courier", 10, "normal")
courier_bold_font = ("Courier", 12, "bold")

# Création des widgets
ttk.Label(root, text="Instance to monitor:").grid(column=0, row=0, padx=10, pady=5, sticky=tk.W)
instance_combo = ttk.Combobox(root, textvariable=instance_var, values=["JTDX", "WSJT"], font=courier_font)
instance_combo.grid(column=1, row=0, padx=10, pady=5)

ttk.Label(root, text="Your Call:").grid(column=0, row=1, padx=10, pady=5, sticky=tk.W)
your_callsign_entry = ttk.Entry(root, textvariable=your_callsign_var, font=courier_font)
your_callsign_entry.grid(column=1, row=1, padx=10, pady=5)

ttk.Label(root, text="Frequencies (comma-separated):").grid(column=0, row=2, padx=10, pady=5, sticky=tk.W)
frequency_entry = ttk.Entry(root, textvariable=frequency_var, font=courier_font)
frequency_entry.grid(column=1, row=2, padx=10, pady=5)

ttk.Label(root, text="Time Hopping (minutes):").grid(column=0, row=3, padx=10, pady=5, sticky=tk.W)
time_hopping_entry = ttk.Entry(root, textvariable=time_hopping_var, font=courier_font)
time_hopping_entry.grid(column=1, row=3, padx=10, pady=5)

ttk.Label(root, text="Wanted Callsign(s) (comma-separated):").grid(column=0, row=4, padx=10, pady=5, sticky=tk.W)
callsign_entry = ttk.Entry(root, textvariable=callsign_var, font=courier_font)
callsign_entry.grid(column=1, row=4, padx=10, pady=5)

ttk.Label(root, text="Mode:").grid(column=0, row=5, padx=10, pady=5, sticky=tk.W)

radio_frame = ttk.Frame(root)
radio_frame.grid(column=1, row=5, padx=10, pady=5)

radio_normal = tk.Radiobutton(radio_frame, text="Normal", variable=mode_var, value="Normal", font=courier_font)
radio_normal.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)

radio_foxhound = tk.Radiobutton(radio_frame, text="Fox/Hound", variable=mode_var, value="Fox/Hound", font=courier_font)
radio_foxhound.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)

radio_superfox = tk.Radiobutton(radio_frame, text="SuperFox", variable=mode_var, value="SuperFox", font=courier_font)
radio_superfox.grid(column=2, row=0, padx=5, pady=5, sticky=tk.W)

# Listbox pour afficher l'historique des wanted_callsigns
ttk.Label(root, text="Wanted Callsigns History:").grid(column=2, row=0, padx=10, pady=0, sticky=tk.W)

listbox = tk.Listbox(root, height=6, bg="#d080d0", fg="black", font=courier_bold_font)
listbox.grid(column=2, row=0, rowspan=6, columnspan=3, padx=10, pady=0, sticky=tk.W+tk.E)
listbox.bind("<<ListboxSelect>>", on_listbox_select) 

button_frame = tk.Frame(root)
button_frame.grid(column=1, row=6, padx=10, pady=10)

# Bouton pour exécuter le script
run_button = tk.Button(button_frame, text="Click to Wait & Pounce", command=run_script)
run_button.pack(side="left", padx=5)

# Bouton pour arrêter le script
stop_button = tk.Button(button_frame, text="Stop all", command=stop_script)
stop_button.pack(side="left", padx=5)

# Met à jour la Listbox avec l'historique
update_listbox()

# Exécution de la boucle principale
root.mainloop()
