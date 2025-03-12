import psutil
import threading
import time
import os

pid = 27725  # Remplace par le PID du programme cible

def get_threads_info(pid):
    """Affiche la liste des threads d'un processus donné."""
    try:
        p = psutil.Process(pid)
        print(f"\n📊 Threads actifs du programme avec PID {pid}:\n")

        # Dictionnaire des threads actifs
        thread_names = {thread.ident: thread.name for thread in threading.enumerate()}

        # Récupérer les threads du processus cible
        for thread in p.threads():
            tid = thread.id
            cpu_time = thread.user_time + thread.system_time
            thread_name = thread_names.get(tid, f"Thread-{tid}")  # Essaye d'associer un nom

            print(f"🧵 Thread: {thread_name} (ID: {tid}) | CPU Time: {cpu_time:.5f}s")

    except psutil.NoSuchProcess:
        print(f"❌ Le processus avec PID {pid} n'existe pas.")
    except psutil.AccessDenied:
        print(f"⛔ Accès refusé. Exécute le script avec `sudo python script.py`.")

def analyze_threads_cpu(pid):
    """Analyse l'utilisation CPU des threads d'un processus."""
    try:
        p = psutil.Process(pid)
        print(f"\n📊 Threads analyse du programme avec PID {pid}:\n")

        # Associer les identifiants de threads à des noms
        thread_names = {thread.ident: thread.name for thread in threading.enumerate()}

        # Snapshot initial des CPU times
        threads_before = {t.id: t.user_time + t.system_time for t in p.threads()}
        time.sleep(1)  # Pause de 1 seconde pour voir l'évolution

        # Snapshot après 1 seconde
        threads_after = {t.id: t.user_time + t.system_time for t in p.threads()}
        
        total_cpu_time = sum(threads_after[tid] - threads_before.get(tid, 0) for tid in threads_after)

        print(f"\n📊 Threads CPU Usage du programme avec PID {pid}:\n")

        for thread in p.threads():
            tid = thread.id
            cpu_time = threads_after[tid] - threads_before.get(tid, 0)
            cpu_percent = (cpu_time / total_cpu_time) * 100 if total_cpu_time > 0 else 0
            thread_name = thread_names.get(tid, f"Thread-{tid}")

            print(f"🧵 Thread: {thread_name} (ID: {tid}) | CPU Usage: {cpu_percent:.2f}% | CPU Time: {cpu_time:.5f}s")

    except psutil.NoSuchProcess:
        print(f"❌ Le processus avec PID {pid} n'existe pas.")
    except psutil.AccessDenied:
        print(f"⛔ Accès refusé. Exécute le script avec `sudo python script.py`.")

# Exécuter les fonctions
get_threads_info(pid)
analyze_threads_cpu(pid)