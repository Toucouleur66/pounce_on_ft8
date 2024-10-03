import tkinter as tk
from tkinter import ttk, messagebox, Menu
import subprocess
import pyperclip
import pickle
import os
import queue
import threading
import datetime
import sys
import wait_and_pounce
import re

stop_event = threading.Event()
version_number = 1.0

PARAMS_FILE = "params.pkl"
POSITION_FILE = "window_position.pkl"
WANTED_CALLSIGNS_FILE = "wanted_callsigns.pkl"  
WANTED_CALLSIGNS_HISTORY_SIZE = 50 

GUI_LABEL_VERSION = f"Wait and Pounce v{version_number} (by F5UKW under GNU GPL Licence)"
RUNNING_TEXT_BUTTON = "Running..."
WAIT_POUNCE_LABEL = "Click to Wait & Pounce"
WAITING_DATA_ANALYSIS_LABEL= "Nothing yet"
WANTED_CALLSIGNS_HISTORY_LABEL = "Wanted Callsigns History (%d):" 

START_COLOR = (255, 255, 0)
END_COLOR = (240, 240, 240)

EVEN_COLOR = "#9dfffe"
ODD_COLOR = "#fffe9f"

gui_queue = queue.Queue()
inputs_enabled = True

def process_gui_queue():
    try:
        while not gui_queue.empty():
            task = gui_queue.get_nowait()
            task()  
    except queue.Empty:
        pass

    root.after(100, process_gui_queue)

class ToolTip:
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        self.text = self.widget.get()

        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, 
            text=self.text,
            relief="solid",
            bg="#D080d0",
            fg="black",
            font=consolas_bold_font,
            justify="left",
            borderwidth=1,
            wraplength=250
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

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
                    gui_queue.put(lambda l=line: self.widget.after(0, self.apply_tags, l))
            self.buffer = lines[-1] if not lines[-1].endswith('\n') else ''

        self.update_clear_button_state()

    def update_clear_button_state(self):
        if self.widget.get(1.0, tk.END).strip():  
            clear_button.config(state=tk.NORMAL) 
        else:
            clear_button.config(state=tk.DISABLED) 

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

def copy_to_clipboard(event):
    text = focus_value_label.cget("text")
    pyperclip.copy(text)
    print(f"Copied to clipboard: {text}")

def interpolate_color(start_color, end_color, factor):
    return tuple(int(start + (end - start) * factor) for start, end in zip(start_color, end_color))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def save_window_position():
    x = root.winfo_x()
    y = root.winfo_y()
    position = {'x': x, 'y': y}
    
    with open(POSITION_FILE, "wb") as f:
        pickle.dump(position, f)

def load_window_position():
    if os.path.exists(POSITION_FILE):
        with open(POSITION_FILE, "rb") as f:
            position = pickle.load(f)
        root.geometry(f"+{position['x']}+{position['y']}")  

def check_fields():
    if your_callsign_var.get() and wanted_callsigns_var.get():
        run_button.config(state="normal")
    else:
        run_button.config(state="disabled")

def disable_inputs():
    global inputs_enabled

    inputs_enabled = False

    instance_combo_entry.config(state="disabled")
    your_callsign_entry.config(state="disabled")
    frequency_entry.config(state="disabled")
    time_hopping_entry.config(state="disabled")
    wanted_callsigns_entry.config(state="disabled")

    for child in radio_frame.winfo_children():
        child.config(state="disabled")

def enable_inputs():
    global inputs_enabled
    
    inputs_enabled = True

    instance_combo_entry.config(state="normal")
    your_callsign_entry.config(state="normal")
    frequency_entry.config(state="normal")
    time_hopping_entry.config(state="normal")
    wanted_callsigns_entry.config(state="normal")

    for child in radio_frame.winfo_children():
        child.config(state="normal")

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
            if len(wanted_callsigns_history) > WANTED_CALLSIGNS_HISTORY_SIZE:
                wanted_callsigns_history.pop(0)
            save_wanted_callsigns(wanted_callsigns_history)
            update_listbox()

def update_wanted_callsigns_history_counter():
    wanted_callsigns_label.config(text=WANTED_CALLSIGNS_HISTORY_LABEL % len(wanted_callsigns_history))        

def on_right_click(event):
    try:
        index = listbox.nearest(event.y)  
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index) 
        listbox.activate(index)
        
        wanted_callsigns_menu.post(event.x_root, event.y_root)
    except Exception as e:
        print(f"Erreur : {e}")

def remove_callsign_from_history():
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        listbox.delete(index)
        del wanted_callsigns_history[index]
    
    save_wanted_callsigns(wanted_callsigns_history)
    update_wanted_callsigns_history_counter()   

def update_listbox():
    listbox.delete(0, tk.END) 
    for callsign in wanted_callsigns_history:
        listbox.insert(tk.END, callsign)  

    if wanted_callsigns_history:
        listbox.see(tk.END)         
    
    update_wanted_callsigns_history_counter()

def on_listbox_select(event):
    if inputs_enabled == False:
        return 
    
    selection = listbox.curselection()
    if selection:
        selected_callsign = listbox.get(selection[0])
        wanted_callsigns_var.set(selected_callsign) 

def get_log_filename():
    today = datetime.datetime.now().strftime("%y%m%d") 
    return f"{today}_pounce.log"

def log_exception_to_file(filename, message):
    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S") 
    with open(filename, "a") as log_file:
        log_file.write(f"{timestamp} {message}\n")

def clear_output_text():
    output_text.delete(1.0, tk.END)
    clear_button.config(state=tk.DISABLED)

def start_monitoring():
    run_button.config(state="disabled", background="red", text=RUNNING_TEXT_BUTTON)
    disable_inputs()
    stop_event.clear() 

    instance_type = instance_var.get()
    frequency = frequency_var.get()
    time_hopping = time_hopping_var.get()
    wanted_callsigns = wanted_callsigns_var.get()
    your_callsign = your_callsign_var.get()
    mode = mode_var.get()

    update_wanted_callsigns_history(wanted_callsigns)

    params = {
        "instance": instance_type,
        "frequency": frequency,
        "time_hopping": time_hopping,
        "wanted_callsigns": wanted_callsigns,
        "your_callsign": your_callsign,
        "mode": mode 
    }
    save_params(params)

    def target():
        try:
            wait_and_pounce.main(
                instance_type,
                frequency,
                time_hopping,        
                your_callsign,
                wanted_callsigns,
                mode,
                control_log_analysis_tracking,
                stop_event
            )
            stop_monitoring()

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exécution du script : {e}")
            log_exception_to_file(log_filename, f"Exception: {str(e)}")

    # Lancer l'exécution du script dans un thread séparé pour ne pas bloquer l'interface
    thread = threading.Thread(target=target)
    thread.start()

def stop_monitoring():
    stop_event.set()
    run_button.config(state="normal", background="SystemButtonFace", text=WAIT_POUNCE_LABEL)
    enable_inputs()

def control_log_analysis_tracking(log_analysis_tracking):
    if log_analysis_tracking is None:
        gui_queue.put(lambda: counter_value_label.config(text=WAITING_DATA_ANALYSIS_LABEL, bg="yellow"))
        gui_queue.put(lambda: focus_frame.grid_remove())  
    else:
        current_time = datetime.datetime.now().timestamp()
        time_difference = current_time - log_analysis_tracking['last_analysis_time']
        
        min_time = 60 
        max_time = 300 

        # Calculer le facteur pour le dégradé (0 pour 2 minutes, 1 pour 5 minutes)
        if time_difference <= min_time:
            # set to START_COLOR 
            factor = 0  
        elif time_difference >= max_time:
            # Set to END_COLOR
            factor = 1
        else:
            # Get factor
            factor = (time_difference - min_time) / (max_time - min_time)

        # Update counter value
        counter_value_text = f"{datetime.datetime.fromtimestamp(log_analysis_tracking['last_analysis_time'], tz=datetime.timezone.utc).strftime('%H:%M:%S')} ----- #{str(log_analysis_tracking['total_analysis'])} ----"

        gui_queue.put(lambda: counter_value_label.config(
            text=counter_value_text,
            bg=rgb_to_hex(interpolate_color(START_COLOR, END_COLOR, factor))
        ))

        active_callsign = log_analysis_tracking['active_callsign']

        if active_callsign is not None and isinstance(active_callsign, (str, list)):
            if your_callsign_var.get() in (active_callsign if isinstance(active_callsign, list) else [active_callsign]):          
                bg_color_hex ="#80d0d0"
                fg_color_hex ="#ff6452"
            else:
                bg_color_hex ="#000000"
                fg_color_hex ="#01ffff"

            gui_queue.put(lambda: (
                focus_value_label.config(
                    text=active_callsign,
                    bg= bg_color_hex,
                    fg= fg_color_hex
                ),
                focus_frame.grid() 
            ))
        else:
            gui_queue.put(lambda: focus_frame.grid_remove())  

def update_timer_with_ft8_sequence():
    current_time = datetime.datetime.now(datetime.timezone.utc)
    utc_time = current_time.strftime("%H:%M:%S")

    if (current_time.second // 15) % 2 == 0:
        background_color = EVEN_COLOR
    else:
        background_color = ODD_COLOR

    gui_queue.put(lambda: timer_value_label.config(
        text=utc_time,
        bg=background_color,
        fg="#3d25fb" 
    ))

    root.after(200, update_timer_with_ft8_sequence)

# Charger les paramètres précédemment sauvegardés
params = load_params()

# Charger l'historique des wanted_callsigns
wanted_callsigns_history = load_wanted_callsigns()

# Création de la fenêtre principale
root = tk.Tk()
root.geometry("900x800")
root.grid_columnconfigure(2, weight=1) 
root.grid_columnconfigure(3, weight=2) 
root.title(GUI_LABEL_VERSION)
root.after(100, process_gui_queue)

load_window_position()
update_timer_with_ft8_sequence()

# Sauvegarde de la position à la fermeture
root.protocol("WM_DELETE_WINDOW", lambda: [save_window_position(), root.destroy()])

# Variables
your_callsign_var = tk.StringVar(value=params.get("your_callsign", ""))
instance_var = tk.StringVar(value=params.get("instance", "JTDX"))
frequency_var = tk.StringVar(value=params.get("frequencies", ""))
time_hopping_var = tk.StringVar(value=params.get("time_hopping", ""))
wanted_callsigns_var = tk.StringVar(value=params.get("callsign", ""))
mode_var = tk.StringVar(value=params.get("mode", "Normal"))

your_callsign_var.trace_add("write", force_uppercase)
wanted_callsigns_var.trace_add("write", force_uppercase)

your_callsign_var.trace_add("write", lambda *args: check_fields())
wanted_callsigns_var.trace_add("write", lambda *args: check_fields())

# Création des widgets
courier_font = ("Courier", 10, "normal")
courier_bold_font = ("Courier", 12, "bold")

consolas_font = ("Consolas", 12, "normal")
consolas_font_lg = ("Consolas", 18, "normal")
consolas_bold_font = ("Consolas", 12, "bold")
segoe_ui_semi_bold_font = ("Segoe UI Semibold", 16)

ttk.Label(root, text="Instance to monitor:").grid(column=0, row=1, padx=10, pady=5, sticky=tk.W)
instance_combo_entry = ttk.Combobox(root, textvariable=instance_var, values=["JTDX", "WSJT"], font=consolas_font, width=23) 
instance_combo_entry.grid(column=1, row=1, padx=10, pady=5, sticky=tk.W)

ttk.Label(root, text="Your Call:").grid(column=0, row=2, padx=10, pady=5, sticky=tk.W)
your_callsign_entry = ttk.Entry(root, textvariable=your_callsign_var, font=consolas_font, width=25) 
your_callsign_entry.grid(column=1, row=2, padx=10, pady=5, sticky=tk.W)

ttk.Label(root, text="Frequencies (comma-separated):").grid(column=0, row=3, padx=10, pady=5, sticky=tk.W)
frequency_entry = ttk.Entry(root, textvariable=frequency_var, font=consolas_font, width=25) 
frequency_entry.grid(column=1, row=3, padx=10, pady=5, sticky=tk.W)

ttk.Label(root, text="Time Hopping (minutes):").grid(column=0, row=4, padx=10, pady=5, sticky=tk.W)
time_hopping_entry = ttk.Entry(root, textvariable=time_hopping_var, font=consolas_font, width=25) 
time_hopping_entry.grid(column=1, row=4, padx=10, pady=5, sticky=tk.W)

ttk.Label(root, text="Wanted Callsign(s) (comma-separated):").grid(column=0, row=5, padx=10, pady=5, sticky=tk.W)
wanted_callsigns_entry = ttk.Entry(root, textvariable=wanted_callsigns_var, font=consolas_font, width=25) 
wanted_callsigns_entry.grid(column=1, row=5, padx=10, pady=5, sticky=tk.W)

tooltip = ToolTip(wanted_callsigns_entry)

ttk.Label(root, text="Mode:").grid(column=0, row=6, padx=10, pady=5, sticky=tk.W)

radio_frame = ttk.Frame(root)
radio_frame.grid(column=1, columnspan=2, row=6, padx=10, pady=5)

radio_normal = tk.Radiobutton(radio_frame, text="Normal", variable=mode_var, value="Normal", font=consolas_font)
radio_normal.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)

radio_foxhound = tk.Radiobutton(radio_frame, text="Fox/Hound", variable=mode_var, value="Fox/Hound", font=consolas_font)
radio_foxhound.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)

radio_superfox = tk.Radiobutton(radio_frame, text="SuperFox", variable=mode_var, value="SuperFox", font=consolas_font)
radio_superfox.grid(column=2, row=0, padx=5, pady=5, sticky=tk.W)

wanted_callsigns_label = ttk.Label(root, text=WANTED_CALLSIGNS_HISTORY_LABEL % len(wanted_callsigns_history))
wanted_callsigns_label.grid(column=2, row=1, padx=10, pady=10, sticky=tk.W)

listbox_frame = tk.Frame(root)
listbox_frame.grid(column=2, row=1, rowspan=6, columnspan=2, padx=10, pady=0, sticky=tk.W+tk.E)
listbox = tk.Listbox(listbox_frame, height=6, bg="#D080d0", fg="black", font=consolas_bold_font)
listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  

scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  
listbox.config(yscrollcommand=scrollbar.set)

# Associer l'événement de sélection
listbox.bind("<<ListboxSelect>>", on_listbox_select)
listbox.bind("<Button-3>", on_right_click)

wanted_callsigns_menu = Menu(root, tearoff=0)
wanted_callsigns_menu.add_command(label="Remove", command=remove_callsign_from_history)

log_analysis_frame = ttk.Frame(root)
log_analysis_frame.grid(column=2, columnspan=2, row=7, padx=10, pady=10, sticky=tk.W)

log_analysis_label = ttk.Label(log_analysis_frame, text="Last sequence analyzed:")
log_analysis_label.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)

counter_value_label = tk.Label(log_analysis_frame, text=WAITING_DATA_ANALYSIS_LABEL, font=consolas_font, bg="yellow")
counter_value_label.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)

focus_frame = tk.Frame(root)
focus_frame.grid(column=0, columnspan=3, row=0, padx=40, pady=10, sticky=tk.W+tk.E)

focus_value_label = tk.Label(
    focus_frame,
    font=consolas_font_lg,    
    padx=10,
    pady=5,
    anchor="center"
)

focus_value_label.pack(side=tk.LEFT, fill=tk.X, expand=True) 
focus_frame.grid_remove()
focus_frame.bind("<Button-1>", copy_to_clipboard)

timer_frame = tk.Frame(root, bg="#cccccc", bd=1)
timer_frame.grid(column=3, row=0, padx=(5, 30), pady=10, sticky=tk.E)

timer_value_label = tk.Label(
    timer_frame,
    font=consolas_font_lg,
    bg="#9dfffe",
    fg="#555bc2",
    padx=10,
    pady=5,
    width=10,
    anchor="center"
)

timer_value_label.pack()

output_text = tk.Text(root, height=20, width=100, bg="#D3D3D3", font=consolas_font)

output_text.tag_config('black_on_purple', foreground='black', background='#D080d0')
output_text.tag_config('black_on_brown', foreground='black', background='#C08000')
output_text.tag_config('black_on_white', foreground='black', background='white')
output_text.tag_config('black_on_yellow', foreground='black', background='yellow')
output_text.tag_config('white_on_red', foreground='white', background='red')
output_text.tag_config('white_on_blue', foreground='white', background='blue')
output_text.tag_config('bright_green', foreground='green')

output_text.grid(column=0, row=8, columnspan=5, padx=10, pady=10, sticky="ew")

clear_button = tk.Button(root, text="Clear Log", command=clear_output_text)
clear_button.grid(column=0, columnspan="4", row=9, padx=10, pady=5, sticky=tk.E)

button_frame = tk.Frame(root)
button_frame.grid(column=1, row=7, padx=10, pady=10)

# Bouton pour exécuter le script
run_button = tk.Button(button_frame, text=WAIT_POUNCE_LABEL, width=20, command=start_monitoring)
run_button.pack(side="left", padx=5)

# Bouton pour arrêter le script
stop_button = tk.Button(button_frame, text="Stop all", command=stop_monitoring)
stop_button.pack(side="left", padx=5)

check_fields()

# Met à jour la Listbox avec l'historique
update_listbox()

log_filename = get_log_filename()
sys.stdout = DebugRedirector(output_text, log_filename)

# Exécution de la boucle principale
if __name__ == "__main__":
    root.mainloop()
