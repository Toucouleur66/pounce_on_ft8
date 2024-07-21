import time

hop_index = 0
frequency_uptime = time.time()
time_hopping = 5 
frequency_hopping = [28091, 14093, 10131]
while True:
    print(f"Temps: {time.time()}", end='\r')
    if (time.time() - frequency_uptime) > time_hopping:
        print(f"{time_hopping} seconde(s) écoulée(s). Fréquence changée (frequency_hopping): {frequency_hopping[hop_index]}Khz")
        hop_index = (hop_index + 1) % len(frequency_hopping)
        frequency_uptime = time.time()

        if frequency_hopping:
            print("here")
            del frequency_hopping[hop_index]
            if not frequency_hopping:
                break
            
    time.sleep(0.2)     