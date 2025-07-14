import sys
import os
import time
import requests
import subprocess

def pobierz_aktualizacje(url, nazwa_pliku):
    print(f"Aktualizator: Pobieranie nowej wersji z {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Zapisz do pliku tymczasowego, aby uniknąć uszkodzenia w razie błędu
        nazwa_pliku_tymczasowego = nazwa_pliku + ".new"
        with open(nazwa_pliku_tymczasowego, 'wb') as f:
            f.write(response.content)
        # Zastąp stary plik nowym - to jest operacja atomowa na większości systemów
        os.replace(nazwa_pliku_tymczasowego, nazwa_pliku)
        print(f"Aktualizator: Pomyślnie nadpisano plik {nazwa_pliku}.")
        return True
    except Exception as e:
        print(f"Aktualizator: Błąd podczas pobierania lub zapisywania aktualizacji: {e}")
        with open("update_error.log", "w") as f_err:
            f_err.write(str(e))
        return False

if __name__ == "__main__":
    url_pobierania = 'https://raw.githubusercontent.com/endiendi/skaner_sieci/refs/heads/main/skaner_sieci.py'
    nazwa_pliku_docelowego = 'G:\\Mój dysk\\Projekt\\python\\skaner_sieci\\skaner_sieci.py'
    oryginalne_argumenty = ['skaner_sieci.py']

    print("Aktualizator: Uruchomiono proces aktualizacji...")
    time.sleep(2) # Dajmy chwilę na zamknięcie głównego skryptu

    if pobierz_aktualizacje(url_pobierania, nazwa_pliku_docelowego):
        print("Aktualizator: Aktualizacja zakończona. Ponowne uruchamianie skryptu w tym samym oknie...")
        try:
            # Użyj os.execv, aby zastąpić bieżący proces (update.py) nowym (skaner_sieci.py),
            # dziedzicząc to samo okno konsoli.
            os.execv(sys.executable, [sys.executable] + oryginalne_argumenty)
        except Exception as e:
            print(f"Aktualizator: Nie udało się ponownie uruchomić skryptu: {e}")
            # Jeśli execv zawiedzie, skrypt będzie kontynuował i się zakończy.
    else:
        print("Aktualizator: Aktualizacja nie powiodła się. Proszę zaktualizować ręcznie.")
    
    # Usuń skrypt aktualizatora po zakończeniu
    try:
        # Ten kod nigdy się nie wykona, jeśli os.execv się powiedzie,
        # co jest w porządku. Zostawiamy go jako fallback na wypadek błędu execv
        # lub nieudanej aktualizacji.
        os.remove(__file__) 
    except OSError as e:
        print(f"Aktualizator: Nie udało się usunąć skryptu pomocniczego: {e}")

    sys.exit(0)