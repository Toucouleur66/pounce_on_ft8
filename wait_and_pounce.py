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
import traceback

def caller_function_name():
    return inspect.stack()[1][3]

def grandcaller_function_name():
    return inspect.stack()[2][3]

utc = datetime.timezone.utc

# Temps d'attente pour les différentes fréquences 
wait_time = 0.3

# Temps d'attente pour le basculement de fréquence
default_time_hopping = 10
hop_index = 0

# Instance par défaut
default_instance_type = "JTDX"

# Mode par défaut
default_instance_mode = "Normal"
# "Normal", "Fox/Hound", "SuperFox"

# Définir les couleurs
color_even = (162, 229, 235)
color_odd = (241, 249, 216)

EVEN = "EVEN"
ODD = "ODD"

color_tx_enabled = (255, 60, 60)
color_tx_disabled = (220, 220, 220)

# Définition des séquences à identifier
cq_call_selected = None
report_received_73 = None
reply_to_my_call = None
reception_report_received = None
best_regards = None
best_regards_received_for_my_call = None
best_regards_sent_to_call_selected = None
report_received_73_for_my_call = None
respond_with_positive_signal_report = None
respond_with_negative_signal_report = None
confirm_signal_and_respond_with_positive_signal_report = None
confirm_signal_and_respond_with_negative_signal_report = None

def is_valid_frequency(freq):
    # Plages de fréquences autorisées
    valid_ranges = [
        (1800, 2000),
        (3500, 4000),
        (5330, 5400),
        (7000, 7100),
        (10100, 10150),
        (14000, 14350),
        (18068, 18168),
        (21000, 21450),
        (24890, 24990),
        (28000, 29700),
        (50000, 50500)
    ]
    return any(lower <= freq <= upper for lower, upper in valid_ranges)

def find_latest_file(dir_path, pattern="*ALL.TXT"):
    files = glob.glob(os.path.join(dir_path, pattern))
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)    
    return latest_file

# Fonction d'affichage de couleur de texte
def black_on_purple(text):
    return f"[black_on_purple]{text}[/black_on_purple]"

def black_on_brown(text):
    return f"[black_on_brown]{text}[/black_on_brown]"

def black_on_white(text):
    return f"[black_on_white]{text}[/black_on_white]"

def black_on_yellow(text):
    return f"[black_on_yellow]{text}[/black_on_yellow]"

def white_on_red(text):
    return f"[white_on_red]{text}[/white_on_red]"

def white_on_blue(text):
    return f"[white_on_blue]{text}[/white_on_blue]"

def bright_green(text):
    return f"[bright_green]{text}[/bright_green]"

def truncate_title(title, max_length=22):
    return (title[:max_length] + '[...]') if len(title) > max_length else title

def format_with_comma(number):
    if isinstance(number, int):
        return f"{number:,}"
    return None

def signal_handler(sig, frame):
    print(f"\n{white_on_red('Arrêt manuel du script.')}")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Queue de travail
work_queue = queue.Queue()
          
def distance(c1, c2):
    return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2)

def is_closer_to_odd_or_even(color):
    if distance(color, color_even) < distance(color, color_odd):
        return EVEN
    else:
        return ODD

def replace_input_field_content(x_offset, y_offset, find_sequences, press_enter_key=None):
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
    
    # Si le contenu actuel est identique à find_sequences, sortir de la fonction
    if current_content == find_sequences:
        return
    
    # Effacer le texte sélectionné (Delete)
    pyautogui.press('delete')
    time.sleep(wait_time)
    
    pyautogui.typewrite(find_sequences, interval=0.05)  # Vous pouvez ajuster l'intervalle entre chaque caractère si nécessaire

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
                print(f"{white_on_red('Erreur ou arrêt volontaire')} {str(pixel_color)}")
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
            print(f"Fenêtre restaurée et mise au premier plan.")

        # Repositionner et redimensionner la fenêtre si les paramètres sont fournis
        if None not in (x, y, width, height):
            window.moveTo(x, y)
            window.resizeTo(width, height)

            debug_to_print = f"Fenêtre identifiée et correctement positionnée"
            debug_to_print+= f" {bright_green('[' + grandcaller_function_name() + ']')}."

            print(debug_to_print)
    except Exception as e:
        print(f"Erreur lors de l'identification et ou déplacement de la fenêtre: {e}")
        return False
    
    return True

def prepare_wsjt(window_title, call_selected = None):
    # Activer la fenêtre désirée
    restore_and_or_move_window(window_title, 480, 0, 1080, 960)
    if call_selected:
        # Lecture du champ Input 
        replace_input_field_content(690, 775, call_selected)
    # Clic sur generate_message 
    pyautogui.click(1200, 720)

    if call_selected:
        return True
    else:
        return False
    
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
    print(f"Mise à jours de la fréquence: {black_on_purple(frequency + 'Mhz')}")
    replace_input_field_content(615, 190, frequency, True)

def prepare_jtdx(window_title, call_selected = None):
    # Activer la fenêtre désirée
    restore_and_or_move_window(window_title, 0, 90, 1090, 960)
    # Définir 
    print(f"Configuration TX: {bright_green(jtdx_is_set_to_odd_or_even(window_title))}")
    if call_selected:
        # Lecture du champ Input 
        replace_input_field_content(625, 235, call_selected)
    # Clic sur generate_message 
    pyautogui.click(770, 840)

    if call_selected:
        return True
    else:
        return False

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
        return is_closer_to_odd_or_even(pixel_color)
    except pyautogui.PyAutoGUIException as e:
            print(f"Erreur lors de l'obtention de la couleur du pixel : {e}")
            sys.exit()
    return None

def toggle_jtdx_to_odd(window_title):
    if jtdx_is_set_to_odd_or_even(window_title) == EVEN:
        pyautogui.click(1015, 150) 

def toggle_jtdx_to_even(window_title):
    if jtdx_is_set_to_odd_or_even(window_title) == ODD:
        pyautogui.click(1015, 150) 

def ends_with_even_or_odd(log_time_str):
    if log_time_str[-1].isdigit():
        last_digit = int(log_time_str[-1])    
        if last_digit % 2 == 0:
            # Nombres paires 
            # (first)
            return EVEN
        else:
            # Nombre impaires 
            # (second)
            return ODD        
    else:
        return False

# Séquences à identifier
def generate_sequences(your_callsign, call_selected):
    global cq_call_selected
    global report_received_73
    global reply_to_my_call
    global reception_report_received
    global best_regards
    global best_regards_received_for_my_call    
    global best_regards_sent_to_call_selected
    global report_received_73_for_my_call
    global respond_with_positive_signal_report
    global respond_with_negative_signal_report
    global confirm_signal_and_respond_with_positive_signal_report
    global confirm_signal_and_respond_with_negative_signal_report

    cq_call_selected = f"CQ {call_selected}"
    report_received_73 = f"{call_selected} RR73"
    reception_report_received = f"{call_selected} RRR"
    reply_to_my_call = f"{your_callsign} {call_selected}"
    report_received_73_for_my_call = f"{your_callsign} {call_selected} RR73"
    best_regards_received_for_my_call = f"{your_callsign} {call_selected} 73"
    best_regards_sent_to_call_selected = f"{call_selected} {your_callsign} 73"
    best_regards = f"{call_selected} 73"
    respond_with_positive_signal_report = f"{call_selected} +"
    respond_with_negative_signal_report = f"{call_selected} -"
    confirm_signal_and_respond_with_positive_signal_report = f"{call_selected} R+"
    confirm_signal_and_respond_with_negative_signal_report = f"{call_selected} R-"

    # Definition des séquences à identifier:
    # Attention, l'ordre doit être respecté par ordre décroissant d'importance des messages
    return {
        'report_received_73_for_my_call': report_received_73_for_my_call,
        'best_regards_received_for_my_call': best_regards_received_for_my_call,
        'best_regards_sent_to_call_selected': best_regards_sent_to_call_selected,
        'best_regards': best_regards,
        'reply_to_my_call': reply_to_my_call,
        'reception_report_received': reception_report_received,
        'report_received_73': report_received_73,
        'cq_call_selected': cq_call_selected,
        'respond_with_positive_signal_report': respond_with_positive_signal_report,
        'respond_with_negative_signal_report': respond_with_negative_signal_report,
        'confirm_signal_and_respond_with_positive_signal_report': confirm_signal_and_respond_with_positive_signal_report,
        'confirm_signal_and_respond_with_negative_signal_report': confirm_signal_and_respond_with_negative_signal_report
    }


def get_log_time(log_time_str):
    # Format JTDX
    if re.match(r'^\d{8}_\d{6}', log_time_str):
        match = re.match(r'^\d{8}_\d{6}', log_time_str)
        log_time = datetime.datetime.strptime(match.group(0), "%Y%m%d_%H%M%S")
    # Format WSJT                    
    elif re.match(r'^\d{6}_\d{6}', log_time_str):
        log_time = datetime.datetime.strptime(log_time_str, "%y%m%d_%H%M%S")

    return log_time.replace(tzinfo=utc) 

def find_sequences(file_path, sequences, last_number_of_lines=100, time_max_expected_in_minutes=10):    
    # Initialiser les résultats avec les valeurs du dictionnaire sequences comme clés
    results = {sequence: False for sequence in sequences.values()}
    found_sequences = {}
    log_time_str = False

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Obtenir les dernières lignes en partant de la fin
        last_lines = lines[-last_number_of_lines:]
        sequence_found_flag = False 

        # Vérifier si les séquences sont dans les dernières lignes
        for line in reversed(last_lines):
            # Vérifier que la ligne commence par 6 chiffres
            if not re.match(r'^\d{6}', line):
                continue

            # Extraire la date et l'heure du début de la ligne
            try:
                log_time_str = line.split()[0]
                log_time = get_log_time(log_time_str)
                
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
                        
                        sequence_found_flag = True
                        break
                if sequence_found_flag:
                    # Sortir de la boucle des lignes si une séquence est trouvée
                    break

    # Parcourir les séquences dans l'ordre et mettre à jour results
    for key in sequences.values():
        if key in found_sequences:
            print(f"Il y a {white_on_blue(time_difference_display)}: {black_on_white(found_sequences[key])}")
            results[key] = {
                'message': found_sequences[key],
                'period': ends_with_even_or_odd(log_time_str)
            }
            return results
        
    return results

def highlight_calls(wanted_callsigns_list):
    return black_on_purple(", ".join(wanted_callsigns_list))

def monitor_file(
        file_path,
        window_title, 
        control_function_name, 
        control_log_analysis_tracking,
        frequency_hopping,
        time_hopping,
        your_callsign,
        wanted_callsigns_list,
        instance_mode,
        stop_event,        
    ):
    global hop_index
    # Sequences
    global cq_call_selected
    global reception_report_received
    global report_received_73
    global reply_to_my_call
    global best_regards_received_for_my_call    
    global best_regards_sent_to_call_selected
    global best_regards
    global report_received_73_for_my_call
    global respond_with_positive_signal_report
    global respond_with_negative_signal_report
    global confirm_signal_and_respond_with_positive_signal_report
    global confirm_signal_and_respond_with_negative_signal_report

    print(f"\n=== Démarrage Monitoring pour {control_function_name} {bright_green('[' + instance_mode + ']')} {highlight_calls(wanted_callsigns_list)} ===")

    wsjt_ready = False
    jtdx_ready = False
    force_next_hop = False
    last_exit_message = None
    active_call = None 
    enable_tx = False
    period_found = None
    last_file_time_update = None

    log_analysis_tracking = {
        'total_analysis': 0,
        'last_analysis_time': None 
    }

    if len(wanted_callsigns_list) > 1:
        if control_function_name == 'WSJT':
            wsjt_ready = prepare_wsjt(window_title)
        elif control_function_name == 'JTDX':
            jtdx_ready = prepare_jtdx(window_title)
    else:
        if control_function_name == 'WSJT':
            wsjt_ready = prepare_wsjt(window_title, wanted_callsigns_list[0])
        elif control_function_name == 'JTDX':
            jtdx_ready = prepare_jtdx(window_title, wanted_callsigns_list[0])
    
    if time_hopping and frequency_hopping:
        change_qrg_jtdx(jtdx_window_title, format_with_comma(frequency_hopping[hop_index]))
        frequency_uptime = time.time()

    while not stop_event.is_set():
        current_mod_time = os.path.getmtime(file_path)
        
        # Vérification de la date de modification du fichier
        if last_file_time_update is None or current_mod_time != last_file_time_update:
            # Attention pour le compteur inutile de compatibliser chaque itération 
            # car JTDX peut par exemple écrire plusieurs fois dans le log pour une seule séquence 
            # if last_file_time_update is None or (current_mod_time - last_file_time_update) >= 3:
            log_analysis_tracking['total_analysis'] += 1
            log_analysis_tracking['last_analysis_time'] = current_mod_time
            last_file_time_update = current_mod_time  

            if not active_call:
                # Rechercher dans le fichier un call à partir de la liste
                for wanted_callsigns in wanted_callsigns_list:
                    sequences_to_find = generate_sequences(your_callsign, wanted_callsigns)
                    # Attention, on peut avoir à lire de nombreuses fois le fichier de log
                    sequences_found = find_sequences(file_path, sequences_to_find)
                    if any(sequences_found.values()):
                        active_call = wanted_callsigns
                        print(f"{white_on_blue('Focus sur')} {active_call}")
                        break

            if active_call:
                sequences_to_find = generate_sequences(your_callsign, active_call)
                sequences_found = find_sequences(file_path, sequences_to_find)

                # Check for exit loop
                exit_message = False

                # Regular normal mode
                if instance_mode == "Normal":
                    sequences_to_check = [
                        best_regards_sent_to_call_selected,
                        best_regards_received_for_my_call
                    ]
                # Might be Hound or Super hound    
                else:
                    sequences_to_check = [
                        report_received_73_for_my_call
                    ]

                # Recherche de la première séquence de sortie décodée
                for sequence in sequences_to_check:
                    if sequences_found[sequence]:
                        sequence_found = sequence
                        exit_message = sequences_found[sequence]['message']                            
                        break 

                if exit_message and last_exit_message != exit_message:
                    print(f"Séquence de sortie trouvée {white_on_red(sequence_found)}: {black_on_white(exit_message)}")
                    # Mise à jours de la dernière séquence de sortie
                    last_exit_message = exit_message
                    
                    if control_function_name == 'JTDX':
                        if instance_mode != "Normal":
                            jtdx_ready = disable_tx_jtdx(window_title)
                    elif control_function_name == 'WSJT':
                        wsjt_ready = wait_and_log_wstj_qso(window_title)          

                    # Retirer l'indicatif des wanted
                    wanted_callsigns_list.remove(active_call)
                    active_call = None

                    # Est ce que le script doit poursuivre en utilisant d'autres fréquences?
                    if frequency_hopping:
                        # Supprime la fréquence car terminé
                        del frequency_hopping[hop_index]
                        if not frequency_hopping:
                            print(white_on_red("Arrêt du script car plus de fréquence à explorer."))                            
                            break                
                        else:
                            force_next_hop = True
                            if control_function_name == 'JTDX':
                                jtdx_ready == False                            
                            elif control_function_name == 'WSJT':
                                wsjt_ready == False
                    elif wanted_callsigns_list:
                        force_next_hop = True
                        print(f"\n=== Reprise Monitoring pour {control_function_name} {highlight_calls(wanted_callsigns_list)} ===")
                    else:
                        print(white_on_red("Arrêt du script car plus d'indicatif à rechercher."))
                        break
                else:
                    sequence_found = None
                    enable_tx = True

                    # Liste des séquences à vérifier, dans l'ordre de priorité
                    sequences_to_check = [
                        cq_call_selected,
                        report_received_73,
                        reply_to_my_call,  
                        reception_report_received, 
                        best_regards,                                                     
                        best_regards_received_for_my_call,
                        report_received_73_for_my_call,
                        respond_with_positive_signal_report,
                        respond_with_negative_signal_report,
                        confirm_signal_and_respond_with_positive_signal_report,
                        confirm_signal_and_respond_with_negative_signal_report
                    ]

                    # Recherche de la première séquence décodée
                    for sequence in sequences_to_check:
                        if sequences_found[sequence]:
                            sequence_found = sequence
                            period_found = sequences_found[sequence]['period']
                                # Dès qu'une séquence est trouvée, on sort de la boucle
                            break 

                    # Si aucune séquence n'a été trouvée, désactiver l'émission 
                    if sequence_found is None:
                        enable_tx = False

                if not force_next_hop and sequence_found:
                    print(f"Séquence trouvée {black_on_brown(sequence_found)} {bright_green('[' + period_found + ']')}. Activation de la fenêtre et check état.")

                if enable_tx:        
                    frequency_uptime = time.time()
                    if control_function_name == 'JTDX':
                        # Changement de la période
                        if period_found == EVEN and jtdx_is_set_to_odd_or_even(window_title) == EVEN:
                            print(f"Passage en période {black_on_brown(ODD)}")
                            toggle_jtdx_to_odd(window_title)
                        elif period_found == ODD and jtdx_is_set_to_odd_or_even(window_title) == ODD:
                            print(f"Passage en période {black_on_brown(EVEN)}")
                            toggle_jtdx_to_even(window_title)
                            
                        if jtdx_ready == False:
                            jtdx_ready = prepare_jtdx(window_title, active_call)
                        # Check sur le bouton Enable TX
                        check_and_enable_tx_jtdx(window_title, 610, 855)
                    elif control_function_name == 'WSJT':
                        if wsjt_ready == False:
                            wsjt_ready = prepare_wsjt(window_title, active_call)
                        # Check sur le bouton DX Call
                        check_and_enable_tx_wsjt(window_title, 640, 750)
                else:
                    if jtdx_ready or wsjt_ready:
                        print(f"{black_on_yellow('Disable TX')}. Pas de séquence trouvée pour {bright_green(active_call)}. Le monitoring se poursuit.")
                        if len(wanted_callsigns_list) > 1:
                            active_call = None 
                                        
                        if control_function_name == 'JTDX':
                            jtdx_ready = False
                            disable_tx_jtdx(window_title)
                        elif control_function_name == 'WSJT':
                            wsjt_ready = False            
        
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
                print(f"{white_on_blue(datetime.datetime.now(datetime.timezone.utc).strftime('%H%Mz %d %b'))} {debug_to_print}. Fréquence modifiée (frequency_hopping)")
        
                frequency_uptime = time.time()

        if datetime.datetime.now() - datetime.datetime.fromtimestamp(current_mod_time) < datetime.timedelta(minutes=5):
            control_log_analysis_tracking(log_analysis_tracking)
        
        time.sleep(wait_time)
    
    return 0

# Définir les chemins de fichiers à analyser
wsjt_file_path = "C:\\Users\\TheBoss\\AppData\\Local\\WSJT-X\\"
jtdx_file_path = "C:\\Users\\TheBoss\\AppData\\Local\\JTDX - FT5000\\"

# Update window tile
wsjt_window_title = "WSJT-X   v2.7.1-devel   by K1JT et al."
jtdx_window_title = "JTDX - FT5000  by HF community                                         v2.2.160-rc7 , derivative work based on WSJT-X by K1JT"


def main(
        instance_type, 
        frequency,
        time_hopping,
        your_callsign,
        wanted_callsigns_list,
        instance_mode,
        control_log_analysis_tracking,
        stop_event
    ):

    try:
        wanted_callsigns_list = [call for call in wanted_callsigns_list.upper().split(",") if len(call) >= 3]
        frequency_hopping = None

        if frequency and ',' in frequency:
            frequency_hopping = list(map(int, frequency.split(',')))
            frequency_hopping = [freq for freq in frequency_hopping if is_valid_frequency(freq)]

            if len(frequency_hopping) > 1 and time_hopping == None:
                time_hopping = default_time_hopping

        if frequency and frequency_hopping == None:
            frequency = int(frequency)

            if is_valid_frequency(frequency):
                restore_and_or_move_window(jtdx_window_title, 0, 90, 1090, 960)
                change_qrg_jtdx(jtdx_window_title, format_with_comma(frequency))
        
        if instance_type == 'JTDX':
            working_file_path = find_latest_file(jtdx_file_path)
            working_window_title = jtdx_window_title
        elif instance_type == 'WSJT':
            working_file_path = find_latest_file(wsjt_file_path)
            working_window_title = wsjt_window_title
        
        print(white_on_red(f"Début du Monitoring pour {your_callsign} du fichier: {working_file_path}"))

        monitor_file(
            working_file_path,
            working_window_title, 
            instance_type, 
            control_log_analysis_tracking,
            frequency_hopping,
            time_hopping,
            your_callsign,
            wanted_callsigns_list,
            instance_mode,
            stop_event
        )
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S") 
        exception = f"{timestamp} Exception: {str(e)}\n"
        traceback = f"{timestamp} Traceback:\n{traceback.format_exc()}\n"
        print(exception)
        print(traceback)
        with open("wait_and_pounce_debug.log", "a") as log_file:
            log_file.write(exception)
            log_file.write(traceback)

    control_log_analysis_tracking(None)
    
    print(f"{white_on_red(f"Fin du Monitoring pour {your_callsign}")} \n")
    
    return 0

if __name__ == "__main__":
    clear_console()
    sys.exit(main())
