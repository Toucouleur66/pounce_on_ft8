import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import pickle
import os
import threading
import datetime
import sys
import wait_and_pounce
import re

PARAMS_FILE = "params.pkl"
WANTED_CALLSIGNS_FILE = "wanted_callsigns.pkl"  
MAX_HISTORY = 10  

class DebugRedirector:
    def __init__(self, widget, log_filename):
        self.widget = widget
        self.log_filename = log_filename
        self.buffer = '' 

    def write(self, string):
        self.buffer += string
        if '\n' in self.buffer:
            lines = self.buffer.splitlines(keepends=True)
            for line in lines:
                if line.endswith('\n'):
                    clean_string = self.remove_tag_codes(line)
                    self.write_to_log(clean_string)
                    self.widget.after(0, self.apply_tags, line)
            self.buffer = lines[-1] if not lines[-1].endswith('\n') else ''

    def write_to_log(self, clean_string):
        with open(self.log_filename, "a") as log_file:
            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
            log_file.write(f"{timestamp} {clean_string}")

    def remove_tag_codes(self, string):
        tag_escape = re.compile(r'\[/?[a-zA-Z_]+\]')
        return tag_escape.sub('', string)

    def apply_tags(self, string):
        tag_pattern = re.compile(r'\[(.*?)\](.*?)\[/.*?\]')
        
        last_pos = 0
        for match in tag_pattern.finditer(string):
            tag = match.group(1)  
            text = match.group(2) 

            if last_pos < match.start():
                self.widget.insert(tk.END, string[last_pos:match.start()])

            self.widget.insert(tk.END, text, tag)

            last_pos = match.end()

        if last_pos < len(string):
            self.widget.insert(tk.END, string[last_pos:])
        
        self.widget.see(tk.END)

    def flush(self):
        pass

def force_uppercase(*args):
    your_callsign_var.set(your_callsign_var.get().upper())
    wanted_callsigns_var.set(wanted_callsigns_var.get().upper())

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

def get_log_filename():
    today = datetime.datetime.now().strftime("%y%m%d") 
    return f"{today}_pounce.log"

def log_exception_to_file(filename, message):
    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S") 
    with open(filename, "a") as log_file:
        log_file.write(f"{timestamp} {message}\n")

def run_script():
    instance_type = instance_var.get()
    frequencies = frequency_var.get()
    time_hopping = time_hopping_var.get()
    wanted_callsigns = wanted_callsigns_var.get()
    your_callsign = your_callsign_var.get()
    mode = mode_var.get()

    update_wanted_callsigns_history(wanted_callsigns)

    params = {
        "instance": instance_type,
        "frequencies": frequencies,
        "time_hopping": time_hopping,
        "wanted_callsigns": wanted_callsigns,
        "your_callsign": your_callsign,
        "mode": mode 
    }
    save_params(params)

    def target():
        try:
            run_button.config(state="disabled", background="red", text="Running...")
            
            # Appel direct à la fonction monitor_file avec les paramètres et la fonction callback
            wait_and_pounce.main(
                instance_type,
                frequencies,
                time_hopping,        
                your_callsign,
                wanted_callsigns,
                mode,
                update_log_count
            )

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exécution du script : {e}")
            log_exception_to_file(log_filename, f"Exception: {str(e)}")
        finally:
            run_button.config(state="normal", background="SystemButtonFace", text="Run Script")

    # Lancer l'exécution du script dans un thread séparé pour ne pas bloquer l'interface
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
        wanted_callsigns_var.set(selected_callsign) 

def update_log_count(value):
    log_been_analyzed_counter_var.set(f"Log Analysis Count: {value}")

# Charger les paramètres précédemment sauvegardés
params = load_params()

# Charger l'historique des wanted_callsigns
wanted_callsigns_history = load_wanted_callsigns()

# Création de la fenêtre principale
root = tk.Tk()
root.geometry("900x600")
root.grid_columnconfigure(2, weight=1) 
root.grid_columnconfigure(3, weight=1) 
root.grid_columnconfigure(4, weight=1) 
root.title("Wait and Pounce (by F5UKW under GNU GPL Licence)")

# Variables
your_callsign_var = tk.StringVar(value=params.get("your_callsign", ""))
instance_var = tk.StringVar(value=params.get("instance", "JTDX"))
frequency_var = tk.StringVar(value=params.get("frequencies", ""))
time_hopping_var = tk.StringVar(value=params.get("time_hopping", ""))
wanted_callsigns_var = tk.StringVar(value=params.get("callsign", ""))
mode_var = tk.StringVar(value=params.get("mode", "Normal"))

your_callsign_var.trace_add("write", force_uppercase)
wanted_callsigns_var.trace_add("write", force_uppercase)

# Création des widgets
courier_font = ("Courier", 10, "normal")
courier_bold_font = ("Courier", 12, "bold")

log_been_analyzed_counter_var = tk.StringVar()
log_been_analyzed_counter_var.set("Log Analysis Count: 0")

log_been_analyzed_counter_label = ttk.Label(root, textvariable= log_been_analyzed_counter_var, font=courier_font)
log_been_analyzed_counter_label.grid(column=0, row=6, padx=10, pady=5)

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
wanted_callsigns_entry = ttk.Entry(root, textvariable=wanted_callsigns_var, font=courier_font)
wanted_callsigns_entry.grid(column=1, row=4, padx=10, pady=5)

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

output_text = tk.Text(root, height=20, width=100, bg="#D3D3D3", font=("Courier", 10, "normal"))

output_text.tag_config('black_on_green', foreground='black', background='green')
output_text.tag_config('black_on_white', foreground='black', background='white')
output_text.tag_config('black_on_yellow', foreground='black', background='yellow')
output_text.tag_config('white_on_red', foreground='white', background='red')
output_text.tag_config('white_on_blue', foreground='white', background='blue')
output_text.tag_config('bright_green', foreground='green', font=('Courier', 10, 'bold'))

output_text.grid(column=0, row=7, columnspan=5, padx=10, pady=10, sticky="ew")

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

log_filename = get_log_filename()
sys.stdout = DebugRedirector(output_text, log_filename)

# Exécution de la boucle principale
root.mainloop()
