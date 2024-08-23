import os
import glob
import time
import datetime
import pyautogui
import pyperclip
import pygetwindow as gw
import argparse
import sys
import signal
import pytz
import win32gui
import win32con
import threading
import queue
import re
import math
import inspect

def caller_function_name():
    return inspect.stack()[1][3]

def grandcaller_function_name():
    return inspect.stack()[2][3]

from colorama import init, Fore, Back, Style

# Temps d'attente pour les différentes fréquences 
wait_time = 0.3

# Temps d'attente pour le basculement de fréquence
default_time_hopping = 10
hop_index = 0

# Gestion du compteur de log 
check_call_count = 0

# Instance par défaut
default_instance_type = 'JTDX'

# Définir les couleurs
color_even = (162, 229, 235)
color_odd = (241, 249, 216)

color_tx_enabled = (255, 60, 60)
color_tx_disabled = (220, 220, 220)

# Définir les arguments de la ligne de commande
parser = argparse.ArgumentParser(description='Surveillance des fichiers de logs pour une séquence spécifique.')
parser.add_argument('-yc', '--your_call', type=str, required=True, help='Votre indicatif d\'appel')
parser.add_argument('-c', '--call', type=str, required=True, help='Le call à rechercher')
parser.add_argument('-f', '--frequency', type=int, default=None, help="(optionnel) La fréquence à utiliser (en Khz, par exemple 28091, en cas d'absence de fréquence spécifiée, l'instance conserve sa fréquence actuelle)")
parser.add_argument('-i', '--instance', type=str, default=default_instance_type, help=f'Le type d\'instance à lancer (valeurs autorisées "JTDX" ou "WSJT", par défaut "{default_instance_type}")')
parser.add_argument('-fh', '--frequency_hopping', type=str, default=None, help="(optionnel) Les fréquences à utiliser (en Khz, par exemple 28091,18095,24911) le basculement des fréquences s'effectuera dans l'ordre indiqué")
parser.add_argument('-th', '--time_hopping', type=int, default=default_time_hopping, help=f'(optionnel) Le temps entre chaque saut de fréquence si --frequency_hopping a été précisé (fixé par défaut à {default_time_hopping} minutes)')

args = parser.parse_args()

print(f"Your Call: {args.your_call}")
print(f"Call: {args.call}")
print(f"Frequency: {args.frequency}")
print(f"Instance: {args.instance}")
print(f"Frequency Hopping: {args.frequency_hopping}")
print(f"Time Hopping: {args.time_hopping}")

your_call, call_selected, frequency, instance, frequency_hopping, time_hopping = args.your_call, args.call, args.frequency, args.instance, args.frequency_hopping, args.time_hopping

# Prise en charge des fréquences à gérer
if frequency_hopping:
    frequency_hopping = list(map(int, args.frequency_hopping.split(',')))

# Initialisation de colorama
init()

# Event global pour signaler l'arrêt des threads
stop_event = threading.Event()

def find_latest_file(dir_path, pattern="*ALL.TXT"):
    files = glob.glob(os.path.join(dir_path, pattern))
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)    
    return latest_file

# Fonction de décoration de texte
def black_on_green(text):
    return f"{Fore.BLACK}{Back.GREEN}{text}{Style.RESET_ALL}"

def black_on_white(text):
    return f"{Fore.BLACK}{Back.WHITE}{text}{Style.RESET_ALL}"

def black_on_yellow(text):
    return f"{Fore.BLACK}{Back.YELLOW}{text}{Style.RESET_ALL}"

def white_on_red(text):
    return f"{Fore.WHITE}{Back.RED}{text}{Style.RESET_ALL}"

def white_on_blue(text):
    return f"{Fore.WHITE}{Back.BLUE}{text}{Style.RESET_ALL}"

def bright_green(text):
    return f"{Fore.GREEN}{Style.BRIGHT}{text}{Style.RESET_ALL}"

def truncate_title(title, max_length=22):
    return (title[:max_length] + '[...]') if len(title) > max_length else title

def format_with_comma(number):
    if isinstance(number, int):
        return f"{number:,}"
    return None

def signal_handler(sig, frame):
    print(f"\n{white_on_red("Arrêt manuel du script.")}")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Queue de travail
work_queue = queue.Queue()
          
def distance(c1, c2):
    return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2)

def is_closer_to_odd_or_even(color):
    if distance(color, color_even) < distance(color, color_odd):
        return 'EVEN'
    else:
        return 'ODD'

def replace_input_field_content(x_offset, y_offset, check_file_for_sequences, press_enter_key=None):
    # Déplacer la souris vers le champ input et cliquer
    pyautogui.click(x_offset, y_offset)
    time.sleep(wait_time)  
    
    # Sélectionner tout le texte (Ctrl+A)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(wait_time)
    
    # Copier le contenu actuel dans le presse-papiers (Ctrl+C)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(wait_time)
    
    # Lire le contenu du presse-papiers
    current_content = pyperclip.paste()
    
    # Si le contenu actuel est identique à check_file_for_sequences, sortir de la fonction
    if current_content == check_file_for_sequences:
        return
    
    # Effacer le texte sélectionné (Delete)
    pyautogui.press('delete')
    time.sleep(wait_time)
    
    pyautogui.typewrite(check_file_for_sequences, interval=0.05)  # Vous pouvez ajuster l'intervalle entre chaque caractère si nécessaire

    if press_enter_key:
        pyautogui.press('enter')

    time.sleep(wait_time)
    
def check_and_enable_tx_wsjt(window_title, x_offset, y_offset, disable_tx = False):
    window = restore_and_or_move_window(window_title)

    if disable_tx:
        print(f"{white_on_blue('DX Call')} à désactiver. Clic droit sur le bouton.")
    
    if window:
        pyautogui.moveTo(x_offset, y_offset)  
        time.sleep(wait_time)
        try:
            # Obtenir la couleur du pixel à la position actuelle de la souris
            pixel_color = pyautogui.pixel(x_offset, y_offset)
            if disable_tx:                
                pyautogui.click(x_offset, y_offset, button='right')
            # Vérifier si la couleur du pixel est (255, 255, 0)
            elif pixel_color == (255, 255, 0):                
                pyautogui.click(x_offset, y_offset)
                print(f"{black_on_yellow('DX Call')} jaune, à activer. Clic pour le passage de {white_on_red('DX Call')} en rouge.")
            elif pixel_color == (255, 0, 0):
                print(f"{white_on_red('DX Call')} rouge. Aucun clic. Le monitoring se poursuit.")
            else:
                print(f"{white_on_red('Erreur ou arrêt volontaire de l\'instance')} {str(pixel_color)}")
                sys.exit()
        except pyautogui.PyAutoGUIException as e:
            print(f"Erreur lors de l'obtention de la couleur du pixel : {e}")
            sys.exit()
        return None
    
def check_and_enable_tx_jtdx(window_title, x_offset, y_offset):
    window = restore_and_or_move_window(window_title)
    
    if window:
        pyautogui.moveTo(x_offset, y_offset)  
        time.sleep(wait_time)
        try:
            # Obtenir la couleur du pixel à la position actuelle de la souris
            pixel_color = pyautogui.pixel(x_offset, y_offset)
            if distance(pixel_color, color_tx_disabled) < distance(pixel_color, color_tx_enabled):            
                print(f"{black_on_yellow('Enable TX')} inactif. Clic pour passage à l'état {white_on_red('Enable TX')} actif.")
                pyautogui.click(x_offset, y_offset)
            else:
                print(f"{white_on_red('Enable TX')} actif. Aucun clic. Le monitoring se poursuit.")
        except pyautogui.PyAutoGUIException as e:
            print(f"Erreur lors de l'obtention de la couleur du pixel : {e}")
            sys.exit()
        return None

def clear_console():
    # Windows
    if os.name == 'nt':
        os.system('cls')
    # Mac and Linux
    else:
        os.system('clear')
        
def restore_and_or_move_window(window_title, x=None, y=None, width=None, height=None):
    windows = gw.getWindowsWithTitle(window_title)
    
    if not windows:
        print(white_on_red(f"Fenêtre '{window_title}' non trouvée."))
        return False

    window = windows[0]
    
    try:
        real_window = window._hWnd
        foreground_window = win32gui.GetForegroundWindow()

        if real_window != foreground_window:            
            # Restaurer la fenêtre si elle n'est pas déjà active
            window.restore()
            time.sleep(wait_time)

            # Remettre la fenêtre en place quelque soit son état
            win32gui.ShowWindow(real_window, win32con.SW_RESTORE)
            win32gui.SetWindowPos(real_window, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetWindowPos(real_window, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(real_window)
            win32gui.BringWindowToTop(real_window)
            print(f"Fenêtre '{truncate_title(window.title)}' restaurée et mise au premier plan.")

        # Repositionner et redimensionner la fenêtre si les paramètres sont fournis
        if None not in (x, y, width, height):
            window.moveTo(x, y)
            window.resizeTo(width, height)

            debug_to_print = f"Fenêtre '{black_on_yellow(truncate_title(window.title))}' identifiée et positionnée"
            debug_to_print+= f" {bright_green('[' + grandcaller_function_name() + ']')}."

            print(debug_to_print)
    except Exception as e:
        print(f"Erreur lors de la restauration et du déplacement de la fenêtre: {e}")
        return False
    
    return True

def prepare_wsjt(window_title):
    # Activer la fenêtre désirée
    restore_and_or_move_window(window_title, 480, 0, 1080, 960)
    # Lecture du champ Input 
    replace_input_field_content(690, 775, call_selected)
    # Clic sur generate_message 
    pyautogui.click(1200, 720)

    return True
    
def wait_and_log_wstj_qso(window_title):
    time.sleep(3) 
    
    # On log le QSO
    pyautogui.click(215, 380)
    # Clic droit sur le bouton DXCC Call et on désactive l'instance
    check_and_enable_tx_wsjt(window_title, 640, 750, True)

    return False

def change_qrg_jtdx(window_title, frequency):
    # Mise à jour de la fréquence
    restore_and_or_move_window(window_title)
    print(f"Mise à jours de la fréquence: {black_on_green(frequency + 'Mhz')}")
    replace_input_field_content(615, 190, frequency, True)

def prepare_jtdx(window_title):
    # Activer la fenêtre désirée
    restore_and_or_move_window(window_title, 0, 90, 1090, 960)
    # Définir 
    print(f"Configuration TX: {bright_green(jtdx_is_set_to_odd_or_even(window_title))}")
    # Lecture du champ Input 
    replace_input_field_content(625, 235, call_selected)
    # Clic sur generate_message 
    pyautogui.click(770, 840)

    return True

def disable_tx_jtdx(window_title):
    restore_and_or_move_window(window_title)
    # Halt Tx
    pyautogui.click(680, 850)

    return False

def jtdx_is_set_to_odd_or_even(window_title):
    restore_and_or_move_window(window_title, 0, 90, 1090, 960)

    try:
        pixel_color = pyautogui.pixel(1015, 150)
        time.sleep(wait_time)
        if distance(pixel_color, color_even) < distance(pixel_color, color_odd):
            return 'EVEN'
        else:
            return 'ODD'
    except pyautogui.PyAutoGUIException as e:
            print(f"Erreur lors de l'obtention de la couleur du pixel : {e}")
            sys.exit()
    return None

def toggle_jtdx_to_odd(window_title):
    if jtdx_is_set_to_odd_or_even == 'even':
        pyautogui.click(1015, 150) 

def toggle_jtdx_to_even(window_title):
    if jtdx_is_set_to_odd_or_even == 'first':
        pyautogui.click(1015, 150) 

def check_file_for_sequences(file_path, sequences, last_number_of_lines=100, time_max_expected_in_minutes=10):    
    global check_call_count
    check_call_count += 1

    # Initialiser les résultats avec les valeurs du dictionnaire sequences comme clés
    results = {sequence: False for sequence in sequences.values()}
    found_sequences = {}

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Obtenir les dernières lignes en partant de la fin
        last_lines = lines[-last_number_of_lines:]

        # Obtenir le fuseau horaire UTC
        utc = datetime.timezone.utc

        # Vérifier si les séquences sont dans les dernières lignes
        for line in reversed(last_lines):
            # Vérifier que la ligne commence par 6 chiffres
            if not re.match(r'^\d{6}', line):
                continue

            # Extraire la date et l'heure du début de la ligne
            try:
                log_time_str = line.split()[0]
                # Format JTDX
                if re.match(r'^\d{8}_\d{6}', log_time_str):
                    log_time = datetime.datetime.strptime(log_time_str, "%Y%m%d_%H%M%S")
                # Format WSJT                    
                elif re.match(r'^\d{6}_\d{6}', log_time_str):
                    log_time = datetime.datetime.strptime(log_time_str, "%y%m%d_%H%M%S")
                else:
                    continue
                
                log_time = log_time.replace(tzinfo=utc) 
            except (IndexError, ValueError):
                continue

            # Calculer la différence de temps en minutes
            time_difference_in_seconds = (datetime.datetime.now(utc) - log_time).total_seconds() 
            time_difference_in_minutes = time_difference_in_seconds / 60.0

            # Vérifier si la ligne est dans la limite de temps
            if time_difference_in_minutes <= time_max_expected_in_minutes:
                for key, sequence in sequences.items():
                    if sequence in line:
                        if time_difference_in_seconds < 120:
                            time_difference_display = f"{int(time_difference_in_seconds)}s"
                        else:
                            time_difference_display = f"{int(time_difference_in_minutes)}m"
                                                
                        found_sequences[sequence] = line.strip()

    # Parcourir les séquences dans l'ordre et mettre à jour results
    for key in sequences.values():
        if key in found_sequences:
            print(f"Il y a {white_on_blue(time_difference_display)} [{key}]: {black_on_white(found_sequences[key])}")
            results[key] = found_sequences[key]
            return results
        
    return results

def monitor_file(file_path, window_title, control_function_name):
    global check_call_count, hop_index

    wsjt_ready = False
    jtdx_ready = False
    force_next_hop = False
    last_exit_sequence = None 

    if control_function_name == 'WSJT':
        wsjt_ready = prepare_wsjt(window_title)
    elif control_function_name == 'JTDX':
        jtdx_ready = prepare_jtdx(window_title)

    print(f"\n=== Démarrage Monitoring pour {control_function_name} {black_on_yellow(cq_to_find)} ou {black_on_yellow(rr73_to_find)} ===")
    
    try:
        enable_tx = False
        last_file_time_update = None

        if time_hopping and frequency_hopping:
            change_qrg_jtdx(jtdx_window_title, format_with_comma(frequency_hopping[hop_index]))
            frequency_uptime = time.time()

        while not stop_event.is_set():
            current_mod_time = os.path.getmtime(file_path)
            
            # Vérification de la date de modification du fichier
            if last_file_time_update is None or current_mod_time != last_file_time_update:
                results = check_file_for_sequences(file_path, sequences_to_find)
                last_file_time_update = current_mod_time  

                if results[exit_sequence] and last_exit_sequence != results[exit_sequence]:
                    print(f"Séquence de sortie trouvée {white_on_red(exit_sequence)}: {black_on_white(results[exit_sequence])}")
                    # Mise à jours de la dernière séquence de sortie
                    last_exit_sequence = results[exit_sequence]
                    
                    if control_function_name == 'JTDX':
                        jtdx_ready = disable_tx_jtdx(window_title)
                    elif control_function_name == 'WSJT':
                        wsjt_ready = wait_and_log_wstj_qso(window_title)          

                    # Est ce que le programme doit continuer?
                    if frequency_hopping:
                        # Supprime la fréquence car terminé
                        del frequency_hopping[hop_index]
                        if not frequency_hopping:
                            print(white_on_red("Arrêt du script."))                            
                            break                
                        else:
                            force_next_hop = True
                            if control_function_name == 'JTDX':
                                jtdx_ready == False                            
                            elif control_function_name == 'WSJT':
                                wsjt_ready == False
                    else:
                        break
                else:
                    sequence_found = None
                    enable_tx = True

                    if results[cq_to_find]:
                        sequence_found = cq_to_find                        
                    elif results[answer_to_my_call]:
                        sequence_found = answer_to_my_call     
                    elif results[rr73_to_find]:
                        sequence_found = rr73_to_find
                    elif results[positive_report_to_find]:
                        sequence_found = positive_report_to_find       
                    elif results[negative_report_to_find]:
                        sequence_found = negative_report_to_find                               
                    else:
                        enable_tx = False

                if not force_next_hop and sequence_found:
                    print(f"Séquence trouvée {black_on_green(sequence_found)}. Activation de la fenêtre et check état.")    

                if enable_tx:        
                    frequency_uptime = time.time()
                    if control_function_name == 'JTDX':
                        if jtdx_ready == False:
                            jtdx_ready = prepare_jtdx(window_title)
                        # Check sur le bouton Enable TX
                        check_and_enable_tx_jtdx(window_title, 610, 855)
                    elif control_function_name == 'WSJT':
                        if wsjt_ready == False:
                            wsjt_ready = prepare_wsjt(window_title)
                        # Check sur le bouton DX Call
                        check_and_enable_tx_wsjt(window_title, 640, 750)
                else:
                    if jtdx_ready or wsjt_ready:
                        print(f"{black_on_yellow('Disable TX')}. Pas de séquence trouvée pour {bright_green(call_selected)}. Le monitoring se poursuit.")
                                        
                        if control_function_name == 'JTDX':
                            jtdx_ready = False
                            disable_tx_jtdx(window_title)
                        elif control_function_name == 'WSJT':
                            wsjt_ready = False

                # Afficher le compteur de vérifications
                print(f"Mise à jour du log et suivi {black_on_white(control_function_name + ' #' + str(check_call_count))}", end='\r')
            
            if time_hopping and frequency_hopping:  
                # Vérifier si time_hopping exprimé en minutes a été dépassé
                if (time.time() - frequency_uptime) > time_hopping * 60 or force_next_hop:
                    # Au prochain passage dans la boucle inutile de changer à nouveau de fréquence
                    if force_next_hop:
                        force_next_hop = False
                        debug_to_print = "Changement de fréquence demandé"
                    else:
                        debug_to_print = f"{time_hopping} minute(s) écoulée(s)"
                    
                    hop_index = (hop_index + 1) % len(frequency_hopping)
                    change_qrg_jtdx(jtdx_window_title, format_with_comma(frequency_hopping[hop_index]))
                    print(f"{white_on_blue(datetime.datetime.now(datetime.timezone.utc).strftime("%H%Mz %d %b"))} {debug_to_print}. Fréquence modifiée (frequency_hopping)")                    
                    frequency_uptime = time.time()

            time.sleep(wait_time)
    except KeyboardInterrupt:
        print("Script interrompu par l'utilisateur.")

# Définir les chemins de fichiers à analyser
wsjt_file_path = "C:\\Users\\TheBoss\\AppData\\Local\\WSJT-X\\"
jtdx_file_path = "C:\\Users\\TheBoss\\AppData\\Local\\JTDX - FT5000\\"

# Update window tile
wsjt_window_title = "WSJT-X   v2.7.1-devel   by K1JT et al."
jtdx_window_title = "JTDX - FT5000  by HF community                                         v2.2.160-rc7 , derivative work based on WSJT-X by K1JT"

# Séquences à identifier
cq_to_find = f"CQ {call_selected}"
rr73_to_find = f"{call_selected} RR73"
answer_to_my_call = f"{your_call} {call_selected}"
exit_sequence = f"{your_call} {call_selected} RR73"
positive_report_to_find = f"{call_selected} +"
negative_report_to_find = f"{call_selected} -"

# Definition des séquences à identifier:
# Attention, l'ordre doit être respecté 
# par ordre décroissant d'importance 
sequences_to_find = {
    'exit_sequence': exit_sequence,
    'answer_to_my_call': answer_to_my_call,
    'rr73_to_find': rr73_to_find,
    'cq_to_find': cq_to_find,
    'positive_report_to_find': positive_report_to_find,
    'negative_report_to_find': negative_report_to_find
}

def main():
    if frequency and frequency_hopping == None:
        restore_and_or_move_window(jtdx_window_title, 0, 90, 1090, 960)
        change_qrg_jtdx(jtdx_window_title, format_with_comma(frequency))
    
    # Ajouter les tâches à la queue de travail
    if instance == 'JTDX':
        working_file_path = find_latest_file(jtdx_file_path)
        working_window_title = jtdx_window_title
    elif instance == 'WSJT':
        working_file_path = find_latest_file(wsjt_file_path)
        working_window_title = wsjt_window_title
    
    print(f"\nMonitoring pour {white_on_blue(your_call)} du fichier: {white_on_red(working_file_path)}")

    monitor_file(working_file_path, working_window_title, instance)

    return 0

if __name__ == "__main__":
    clear_console()
    sys.exit(main())
