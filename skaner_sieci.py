# -*- coding: utf-8 -*-
import socket
import math 
import subprocess
import re
import platform
import time
import os
import locale
import ipaddress
import sys
import concurrent.futures
import threading
import errno
from typing import List, Tuple, Optional, Dict, Any
import shlex

#pip uninstall psutil
#pip install psutil

#pip uninstall requests
#pip install requests

#pip uninstall colorama
#pip install colorama

# Funkcja pomocnicza do instalacji
def zainstaluj_pakiet(nazwa_pakietu: str) -> bool:
    """Próbuje zainstalować pakiet używając pip."""
    print(f"Próba instalacji biblioteki '{nazwa_pakietu}' za pomocą pip...")
    try:
        # Użyj sys.executable, aby upewnić się, że instalujesz dla właściwego Pythona
        # check=True rzuci wyjątek CalledProcessError w razie niepowodzenia pip
        subprocess.run([sys.executable, "-m", "pip", "install", nazwa_pakietu], check=True, capture_output=True)
        print(f"{Fore.GREEN}Biblioteka '{nazwa_pakietu}' została pomyślnie zainstalowana.{Style.RESET_ALL}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Błąd podczas instalacji '{nazwa_pakietu}'.{Style.RESET_ALL}")
        print(f"{Fore.RED}Komunikat błędu pip (stderr):{Style.RESET_ALL}\n{e.stderr.decode(errors='ignore')}")
        print(f"{Fore.YELLOW}Możesz spróbować zainstalować ręcznie: {Style.BRIGHT}pip install {nazwa_pakietu}{Style.RESET_ALL}")
        return False
    except FileNotFoundError:
        print(f"{Fore.RED}Błąd: Nie znaleziono polecenia '{sys.executable} -m pip'.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Upewnij się, że Python i pip są poprawnie zainstalowane i dodane do ścieżki systemowej (PATH).{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Spróbuj zainstalować ręcznie: {Style.BRIGHT}pip install {nazwa_pakietu}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas próby instalacji '{nazwa_pakietu}': {e}{Style.RESET_ALL}")
        return False

def sprawdz_i_zainstaluj_biblioteke(nazwa_pakietu: str, nazwa_importu: str, cel: str) -> bool:
    """Sprawdza dostępność biblioteki, importuje ją lub oferuje instalację."""
    try:
        globals()[nazwa_importu] = __import__(nazwa_importu)
        # Dodatkowe importy specyficzne dla biblioteki (jeśli są potrzebne globalnie)
        if nazwa_pakietu == "requests":
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            globals()['HTTPAdapter'] = HTTPAdapter
            globals()['Retry'] = Retry
        elif nazwa_pakietu == "colorama":
            from colorama import Fore, Style, init
            globals()['Fore'] = Fore
            globals()['Style'] = Style
            globals()['init'] = init
            init(autoreset=True)
        return True
    except ImportError:
        print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
        print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka '{nazwa_pakietu}' nie jest zainstalowana.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{cel}{Style.RESET_ALL}")
        try:
            odpowiedz = input(f"{Fore.YELLOW}Czy chcesz spróbować zainstalować ją teraz? (t/n): {Style.RESET_ALL}").lower().strip()
            if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
                if zainstaluj_pakiet(nazwa_pakietu):
                    print(f"{Fore.CYAN}Instalacja zakończona. Uruchom skrypt ponownie, aby włączyć funkcje zależne od '{nazwa_pakietu}'.{Style.RESET_ALL}")
                    sys.exit(0) # Zakończ skrypt
                else:
                    print(f"Instalacja nie powiodła się. Kontynuowanie bez funkcji '{nazwa_pakietu}'.")
            else:
                print(f"Instalacja pominięta. Kontynuowanie bez funkcji '{nazwa_pakietu}'.")
        except (EOFError, KeyboardInterrupt):
             print(f"\nInstalacja pominięta. Kontynuowanie bez funkcji '{nazwa_pakietu}'.")
        print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
        return False

# --- Sprawdzanie i importowanie bibliotek zewnętrznych ---

# 1. Sprawdzanie Colorama
try:
    from colorama import Fore, Style, init
    COLORAMA_AVAILABLE = True
    init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    # Definiuj atrapy, jeśli import się nie udał
    class DummyColorama:
        def __getattr__(self, name): return ""
    Fore = DummyColorama()
    Style = DummyColorama()
    def init(autoreset=True): pass

    print("\n" + "-" * 70) # Użyj prostego separatora, bo Style może nie być dostępne
    print("\nOstrzeżenie: Biblioteka 'colorama' nie jest zainstalowana.")
    print("Kolorowanie tekstu w konsoli będzie wyłączone.")
    try:
        odpowiedz = input("Czy chcesz spróbować zainstalować ją teraz? (t/n): ").lower().strip()
        if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
            if zainstaluj_pakiet("colorama"):
                print(f"{Fore.CYAN}Instalacja zakończona. Uruchom skrypt ponownie, aby użyć kolorów.{Style.RESET_ALL}") # Fore/Style będą atrapami, jeśli instalacja się nie powiedzie
                sys.exit(0) # Zakończ skrypt po udanej instalacji
            else:
                print("Instalacja nie powiodła się. Kontynuowanie bez kolorów.")
        else:
            print("Instalacja pominięta. Kontynuowanie bez kolorów.")
    except (EOFError, KeyboardInterrupt):
        print("\nInstalacja pominięta. Kontynuowanie bez kolorów.")
    print("-" * 70)


# 2. Sprawdzanie Psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70) # Style jest już zdefiniowane (jako atrapa lub prawdziwe)
    print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka 'psutil' nie jest zainstalowana.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Nie można automatycznie wykryć interfejsów sieciowych i VPN.{Style.RESET_ALL}")
    try:
        odpowiedz = input(f"{Fore.YELLOW}Czy chcesz spróbować zainstalować ją teraz? (t/n): {Style.RESET_ALL}").lower().strip()
        if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
            if zainstaluj_pakiet("psutil"):
                print(f"{Fore.CYAN}Instalacja zakończona. Uruchom skrypt ponownie, aby włączyć funkcje zależne od psutil.{Style.RESET_ALL}")
                sys.exit(0) # Zakończ skrypt
            else:
                print("Instalacja nie powiodła się. Kontynuowanie z ograniczoną funkcjonalnością.")
        else:
            print("Instalacja pominięta. Kontynuowanie z ograniczoną funkcjonalnością.")
    except (EOFError, KeyboardInterrupt):
         print("\nInstalacja pominięta. Kontynuowanie z ograniczoną funkcjonalnością.")
    print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)


# 3. Sprawdzanie Requests
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    # Definiuj atrapy dla klas używanych z requests
    class Retry: pass
    class HTTPAdapter: pass

    print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
    print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka 'requests' nie jest zainstalowana.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Pobieranie bazy OUI z sieci będzie niemożliwe.{Style.RESET_ALL}")
    try:
        odpowiedz = input(f"{Fore.YELLOW}Czy chcesz spróbować zainstalować ją teraz? (t/n): {Style.RESET_ALL}").lower().strip()
        if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
            if zainstaluj_pakiet("requests"):
                print(f"{Fore.CYAN}Instalacja zakończona. Uruchom skrypt ponownie, aby włączyć pobieranie OUI z sieci.{Style.RESET_ALL}")
                sys.exit(0) # Zakończ skrypt
            else:
                print("Instalacja nie powiodła się. Kontynuowanie bez pobierania OUI z sieci.")
        else:
            print("Instalacja pominięta. Kontynuowanie bez pobierania OUI z sieci.")
    except (EOFError, KeyboardInterrupt):
        print("\nInstalacja pominięta. Kontynuowanie bez pobierania OUI z sieci.")
    print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)

# --- Konfiguracja ---

# Prefiksy adresów multicast, które chcemy wykluczyć ze skanowania
MULTICAST_PREFIXES: List[str] = ["224.", "239.", "ff02."]
# Domyślny zakres hostów do pingowania
DEFAULT_START_IP: int = 1
DEFAULT_END_IP: int = 254
# URL bazy OUI i konfiguracja cach
OUI_URL: str = "http://standards-oui.ieee.org/oui/oui.txt"
OUI_LOCAL_FILE: str = "oui.txt"
OUI_UPDATE_INTERVAL: int = 86400 # Co ile sekund aktualizować plik oui.txt (domyślnie 24h)
# Timeout dla operacji sieciowych
REQUESTS_TIMEOUT: int = 15 # Timeout dla pobierania OUI
PING_TIMEOUT_MS: int = 300 # Timeout dla ping w ms (Windows)
PING_TIMEOUT_SEC: float = 0.2 # Timeout dla ping w s (Linux/macOS)
HOSTNAME_LOOKUP_TIMEOUT: float = 0.5 # Timeout dla socket.gethostbyaddr/getnameinfo
VPN_INTERFACE_PREFIXES: List[str] = ['tun', 'tap', 'open', 'wg', 'tailscale'] # Dodano 'tailscale' dla pewności
# Wykrywanie domyślnego kodowania konsoli (szczególnie dla Windows)
DEFAULT_ENCODING = locale.getpreferredencoding(False)
WINDOWS_OEM_ENCODING = 'cp852' # Częste kodowanie OEM w Polsce, można dostosować
MAX_HOSTNAME_WORKERS: int = 10 # Liczba wątków do równoległego pobierania nazw hostów
MAX_PING_WORKERS: int = 3 # <--- Dodaj: Maksymalna liczba równoległych pingów im więcej tym mniejsza dokładność zależnie od komputera
DEFAULT_LINE_WIDTH: int = 125 # Zdefiniuj stałą szerokość linii
INPUT_TIMEOUT_SECONDS = 10 # Czas w sekundach na reakcję użytkownika
MAX_PORT_SCAN_WORKERS: int = 10 # Dostosuj wg potrzeb Maksymalna liczba wątków do skanowania portów dla JEDNEGO hosta
TIMEOUT_SENTINEL = object() # Unikalny obiekt sygnalizujący timeout
OPISY_PORTOW: Dict[int, str] = {
    21: "FTP (File Transfer Protocol)",
    22: "SSH (Secure Shell)",
    23: "Telnet",
    25: "SMTP (Simple Mail Transfer Protocol)",
    53: "DNS (Domain Name System)",
    80: "HTTP (HyperText Transfer Protocol)",
    110: "POP3 (Post Office Protocol v3)",
    135: "Microsoft RPC (Remote Procedure Call)",
    139: "NetBIOS Session Service",
    143: "IMAP (Internet Message Access Protocol)",
    443: "HTTPS (HTTP Secure)",
    445: "Microsoft-DS (SMB - Server Message Block)",
    993: "IMAPS (IMAP Secure)",
    995: "POP3S (POP3 Secure)",
    1723: "PPTP (Point-to-Point Tunneling Protocol)",
    3306: "MySQL Database",
    3389: "RDP (Remote Desktop Protocol)",
    5432: "PostgreSQL Database",
    5900: "VNC (Virtual Network Computing)",
    8000: "Alternatywny HTTP (często serwery deweloperskie)",
    8080: "Alternatywny HTTP (często proxy lub serwery web)",
    8123: "Home Assistant (HTTPS)", # Dodano opis
    4357: "Home Assistant (HTTP)", # Dodano opis
    8443: "Alternatywny HTTPS",
    5060: "SIP (Session Initiation Protocol) - używany do VoIP",
    5061: "SIPS (SIP Secure) - bezpieczna wersja SIP",
    67: "DHCP (Dynamic Host Configuration Protocol) - Server",
    68: "DHCP (Dynamic Host Configuration Protocol) - Client",
    161: "SNMP (Simple Network Management Protocol) - Agent",
    162: "SNMP (Simple Network Management Protocol) - Trap",
    631: "IPP (Internet Printing Protocol) - drukarki sieciowe",
    1433: "Microsoft SQL Server",
    1521: "Oracle Database",
    6667: "IRC (Internet Relay Chat)",
    6697: "IRC over SSL (IRC Secure)",
    2375: "Docker Daemon (bez TLS)",
    2376: "Docker Daemon (z TLS)",
    4000: "Serwery deweloperskie (często używany przez różne frameworki)",
    5000: "Serwery deweloperskie (często Flask w Pythonie)",
    8081: "Alternatywny HTTP (często używany przez serwery proxy lub aplikacje Java)",
    8888: "Jupyter Notebook",
    9000: "FastCGI (często używany z serwerami PHP-FPM)",
    9100: "Exporter Prometheus (metryki aplikacji)",
    9090: "Prometheus Server",
    10250: "Kubelet API (Kubernetes)",
    10255: "Kubelet Read-Only Port (Kubernetes) - bez uwierzytelniania",
    8001: "Kubernetes API Server (port insecure)", # Zazwyczaj zabezpieczony przez proxy
    6443: "Kubernetes API Server (HTTPS)",
    30000-32767: "Zakres NodePort (Kubernetes) - dla eksternalnego dostępu do usług",
    8096: "Jellyfin (HTTP)",
    8989: "Jellyfin (HTTPS)", # Domyślny port HTTPS, może być skonfigurowany
    32400: "Plex Media Server",
    8080: "Audiobookshelf (HTTP) - Domyślny, ale konfigurowalny",
    8443: "Audiobookshelf (HTTPS) - Jeśli skonfigurowano SSL",
    # Inne podobne usługi i ich domyślne porty
}

OS_DEFINITIONS: Dict[str, Dict[str, str]] = {
    # --- Przykładowe wpisy ---
    "LINUX_MEDIA_SAMBA_RDP": {
        "abbr": "Lin/Media (Samba,RDP?)",
        "desc": "Linux Media Center (wykryto SSH, Samba, potencjalnie RDP)"
    },
    "LINUX_MEDIA_SAMBA_RDP_ALT": { # Dla portu 139
        "abbr": "Lin/Media (Samba,RDP?)",
        "desc": "Linux Media Center (wykryto SSH, Samba(139), potencjalnie RDP)"
    },
    # --- POPRAWIONY WPIS ---
    "NAS_MULTIMEDIA": {
        "abbr": "NAS/MediaSrv",
        "desc": "NAS z usługami multimedialnymi (SSH, Web, SMB, Plex, Jellyfin, etc.)"
    },
    # --- KONIEC POPRAWIONEGO WPISU ---
    "HOME_ASSISTANT": {
        "abbr": "HomeAsst",
        "desc": "Home Assistant (wykryto port 8123 lub 4357)"
    },
    "WINDOWS_RDP": {
        "abbr": "Win (RDP)",
        "desc": "System Windows (wykryto port Remote Desktop)"
    },
    "LINUX_NAS_SAMBA": {
        "abbr": "Lin/NAS (Samba)",
        "desc": "Linux/NAS (wykryto SSH i Sambę - port 445)"
    },
    "LINUX_NAS_SAMBA_ALT": {
        "abbr": "Lin/NAS (Samba)",
        "desc": "Linux/NAS (wykryto SSH i Sambę - port 139)"
    },
    "LINUX_MAC_SSH_IPP": {
        "abbr": "Lin/Mac (SSH,IPP)",
        "desc": "Linux/macOS (wykryto SSH i port drukowania IPP)"
    },
    "LINUX_MAC_SSH": {
        "abbr": "Lin/Mac (SSH)",
        "desc": "System Linux/macOS (wykryto port SSH)"
    },
    "WINDOWS_SMB": {
        "abbr": "Win (SMB)",
        "desc": "System Windows (wykryto porty SMB/NetBIOS/RPC)"
    },
    "PRINTER_IPP_WEB": {
        "abbr": "Printer (IPP,Web)",
        "desc": "Drukarka sieciowa (wykryto IPP i interfejs web)"
    },
    "PRINTER_IPP": {
        "abbr": "Printer (IPP)",
        "desc": "Drukarka sieciowa (wykryto port IPP)"
    },
    "NETWORK_WEB": {
        "abbr": "NetDev/Web",
        "desc": "Urządzenie sieciowe, urządzenie IoT lub serwer z interfejsem webowym."
    },
    "NETWORK_TELNET": {
        "abbr": "NetDev/Telnet",
        "desc": "Urządzenie sieciowe z dostępem przez Telnet"
    },
    "FTP_SERVER": {
        "abbr": "FTP Serv",
        "desc": "Serwer FTP (wykryto port 21)"
    },
    "VNC_SERVER": {
        "abbr": "VNC Serv",
        "desc": "Serwer VNC (wykryto port 5900)"
    },
    "DNS_SERVER": {
        "abbr": "DNS Serv",
        "desc": "Serwer DNS (wykryto port 53)"
    },
    "NETWORK_SNMP": {
        "abbr": "NetDev (SNMP)",
        "desc": "Urządzenie sieciowe zarządzane przez SNMP (port 161)"
    },
    "UNKNOWN_PORTS": {
        "abbr": "Nieznany (Ports)",
        "desc": "Nieznany typ urządzenia (wykryto otwarte porty)"
    },
    "UNKNOWN_NO_PORTS": {
        "abbr": "Nieznany (No Ports)",
        "desc": "Nieznany typ urządzenia (brak otwartych portów)"
    }
    # --- Uzupełnij o wszystkie ID używane w OS_FILTERS ---
}


OS_ABBREVIATIONS: Dict[str, str] = {
    key: definition["abbr"] for key, definition in OS_DEFINITIONS.items()
}


# Konfiguracja kolumn dla rozszerzonej tabeli
KOLUMNY_TABELI: Dict[str, Dict[str, Any]] = {
    "lp":           {"naglowek": "Lp.",             "szerokosc": 3},
    "ip":           {"naglowek": "Adres IP",        "szerokosc": 14},
    "mac":          {"naglowek": "Adres MAC",       "szerokosc": 18},
    "host":         {"naglowek": "Nazwa Hostu",     "szerokosc": 21},
    "porty":        {"naglowek": "Otwarte Porty",   "szerokosc": 31},
    "os":           {"naglowek": "System (Przyp.)", "szerokosc": 17},
    "oui":          {"naglowek": "Producent (OUI)", "szerokosc": 30}
}
# Domyślnie wyświetlane kolumny
DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA: List[str] = ["lp", "ip", "mac", "host", "porty", "os", "oui"] # Zmieniono host_porty na host i porty

# Nowa struktura filtrów OS
OS_FILTERS: List[Dict[str, Any]] = [
    {
        "id": "NAS_MULTIMEDIA",
        "ports_any": set(),
        "ports_all": {22, 80, 139, 445, 8000, 8001, 8080, 8096, 32400},
        "priority": 8 # Bardzo wysoki priorytet ze względu na specyficzność
    },
    {
        "id": "LINUX_MEDIA_SAMBA_RDP", # Identyfikator dla Linux+SSH+Samba(445)+potencjalnie RDP
        "ports_any": set(),           # Nie potrzebujemy 'any'
        "ports_all": {22, 445},       # WYMAGA SSH i SMB (port 445)
        "priority": 15                # WYŻSZY priorytet (niższy numer) niż WINDOWS_RDP (20)
    },
    {
        "id": "LINUX_MEDIA_SAMBA_RDP_ALT", # Identyfikator dla Linux+SSH+Samba(139)+potencjalnie RDP
        "ports_any": set(),
        "ports_all": {22, 139},       # WYMAGA SSH i SMB (port 139)
        "priority": 16                # Minimalnie niższy priorytet niż wersja z 445, ale wciąż > 20
    },
    {
        "id": "HOME_ASSISTANT",
        "ports_any": {8123, 4357}, # Musi mieć przynajmniej jeden z tych
        "ports_all": set(),        # Nie wymaga innych konkretnych portów
        "priority": 10             # Wysoki priorytet
    },
    {
        "id": "WINDOWS_RDP",
        "ports_any": {3389},
        "ports_all": set(),
        "priority": 20
    },
    {
        "id": "LINUX_NAS_SAMBA",
        "ports_any": set(),
        "ports_all": {22, 445}, # Wymaga SSH i SMB (port 445)
        "priority": 30
    },
    {
        "id": "LINUX_NAS_SAMBA_ALT", # Alternatywna reguła dla Samby (port 139)
        "ports_any": set(),
        "ports_all": {22, 139},
        "priority": 31
    },
    {
        "id": "LINUX_MAC_SSH_IPP",
        "ports_any": set(),
        "ports_all": {22, 631}, # Wymaga SSH i IPP
        "priority": 35
    },
    {
        "id": "LINUX_MAC_SSH",
        "ports_any": {22},      # Wystarczy SSH
        "ports_all": set(),
        "priority": 40          # Niższy priorytet niż bardziej specyficzne reguły SSH
    },
    {
        "id": "WINDOWS_SMB",
        "ports_any": {135, 139, 445}, # Wystarczy jeden z portów SMB/RPC
        "ports_all": set(),
        "priority": 50          # Niższy priorytet niż RDP
    },
    {
        "id": "PRINTER_IPP_WEB",
        "ports_any": {80, 443, 8080}, # Wymaga portu web
        "ports_all": {631},          # ORAZ portu IPP
        "priority": 60
    },
    {
        "id": "PRINTER_IPP",
        "ports_any": {631},
        "ports_all": set(),
        "priority": 65
    },
    {
        "id": "NETWORK_WEB",
        "ports_any": {80, 443, 8000, 8080, 8081, 8443}, # Generyczny serwer/urządzenie web
        "ports_all": set(),
        "priority": 70
    },
    {
        "id": "NETWORK_TELNET",
        "ports_any": {23},
        "ports_all": set(),
        "priority": 80
    },
    {
        "id": "FTP_SERVER",
        "ports_any": {21},
        "ports_all": set(),
        "priority": 81
    },
    {
        "id": "VNC_SERVER",
        "ports_any": {5900},
        "ports_all": set(),
        "priority": 82
    },
    {
        "id": "DNS_SERVER",
        "ports_any": {53},
        "ports_all": set(),
        "priority": 83
    },
    {
        "id": "NETWORK_SNMP",
        "ports_any": {161},
        "ports_all": set(),
        "priority": 84
    },
    # Reguły zapasowe (UNKNOWN_PORTS, UNKNOWN_NO_PORTS) są obsługiwane na końcu, jeśli żaden filtr nie pasuje.
]


def wybierz_kolumny_do_wyswietlenia(
    wszystkie_kolumny: Dict[str, Dict[str, Any]] = KOLUMNY_TABELI,
    domyslne_kolumny: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA
) -> List[str]:
    """
    Pozwala użytkownikowi interaktywnie wybrać kolumny do wyświetlenia w tabeli.

    Args:
        wszystkie_kolumny: Słownik definicji wszystkich dostępnych kolumn.
        domyslne_kolumny: Lista kluczy kolumn wybranych domyślnie.

    Returns:
        Lista kluczy wybranych kolumn.
    """
    # Pobierz klucze w oryginalnej kolejności
    oryginalne_klucze = list(wszystkie_kolumny.keys())
    # Klucze dostępne do wyboru przez użytkownika (bez 'lp')
    klucze_do_wyboru = [k for k in oryginalne_klucze if k != 'lp']
    # Klucze aktualnie wybrane przez użytkownika (bez 'lp', które jest dodawane na końcu)
    wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']

    while True:
        print("\n" + "-" * 60)
        print(f"Wybierz kolumny do wyświetlenia:")
        print("-" * 60)
        # Wyświetlaj tylko kolumny dostępne do wyboru
        for i, klucz in enumerate(klucze_do_wyboru):
            # Sprawdzaj obecność w `wybrane_klucze_uzytkownika`
            znacznik = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if klucz in wybrane_klucze_uzytkownika else f"{Fore.RED}[ ]{Style.RESET_ALL}"
            naglowek = wszystkie_kolumny[klucz]['naglowek']
            print(f"  {znacznik} {i+1}. {naglowek} ({klucz})")

        print("-" * 60)
        print(f"Opcje: Wpisz {Fore.LIGHTMAGENTA_EX}numer(y){Style.RESET_ALL} kolumn, aby je przełączyć (np. 24).")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}a{Style.RESET_ALL}', aby zaznaczyć/odznaczyć wszystkie.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}d{Style.RESET_ALL}', aby przywrócić domyślne.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}q{Style.RESET_ALL}' lub naciśnij {Fore.LIGHTMAGENTA_EX}Enter{Style.RESET_ALL}, aby zatwierdzić wybór.")
        print("-" * 60)

        try:
            wybor = input("Twój wybór: ").lower().strip()

            if not wybor or wybor == 'q':
                # --- CZYSZCZENIE ---
                # Przesuń kursor o odpowiednią liczbę linii w górę i wyczyść
                liczba_linii_do_wyczyszczenia = len(klucze_do_wyboru) + 10 # Linie z kolumnami + opcje/separatory + nagłówek
                for _ in range(liczba_linii_do_wyczyszczenia):
                    sys.stdout.write("\033[A\033[K")
                sys.stdout.flush()
                # --- KONIEC CZYSZCZENIA ---
                # Dodaj 'lp' na początku przed zwróceniem
                finalne_wybrane = ['lp'] + [k for k in oryginalne_klucze if k in wybrane_klucze_uzytkownika]
                # print(f"Wybrane kolumny: {', '.join(finalne_wybrane)}")
                sys.stdout.write("\033[A") # Przesuń kursor w górę
                break # Zakończ pętlę



            elif wybor == 'a':
                # Jeśli wszystkie są już zaznaczone, odznacz wszystkie. W przeciwnym razie zaznacz wszystkie.
                if set(wybrane_klucze_uzytkownika) == set(klucze_do_wyboru):
                    wybrane_klucze_uzytkownika.clear()
                else:
                    wybrane_klucze_uzytkownika = list(klucze_do_wyboru)

            elif wybor == 'd':
                # Przywróć domyślne, ale bez 'lp'
                wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']

            elif wybor.isdigit():
                # Iteruj przez każdą cyfrę w wprowadzonym ciągu
                przetworzono_poprawnie = True
                for cyfra in wybor:
                    try:
                        indeks = int(cyfra) - 1
                        if 0 <= indeks < len(klucze_do_wyboru):
                            klucz_do_przelaczenia = klucze_do_wyboru[indeks]
                            if klucz_do_przelaczenia in wybrane_klucze_uzytkownika:
                                wybrane_klucze_uzytkownika.remove(klucz_do_przelaczenia)
                            else:
                                wybrane_klucze_uzytkownika.append(klucz_do_przelaczenia)
                        else:
                            print(f"{Fore.YELLOW}Nieprawidłowy numer kolumny: {cyfra}. Pomijanie.{Style.RESET_ALL}")
                            przetworzono_poprawnie = False
                    except ValueError: # Na wypadek gdyby cyfra nie była cyfrą (chociaż isdigit() powinno to wyłapać)
                        print(f"{Fore.YELLOW}Nieprawidłowy znak w sekwencji: '{cyfra}'. Pomijanie.{Style.RESET_ALL}")
                        przetworzono_poprawnie = False
                else:
                    pass # Jeśli nie było błędu dla tej cyfry, kontynuuj
            else:
                print(f"{Fore.YELLOW}Nieznana opcja. Spróbuj ponownie.{Style.RESET_ALL}")

            # --- CZYSZCZENIE PO KAŻDEJ AKCJI (oprócz wyjścia) ---
            # Liczba linii: nagłówek(3) + kolumny(len) + sep(1) + opcje(3) + sep(1) + input(1) + ew. błąd(1) = len + 11
            liczba_linii_do_wyczyszczenia = len(klucze_do_wyboru) + 11
            for _ in range(liczba_linii_do_wyczyszczenia):
                sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()
            # --- KONIEC CZYSZCZENIA ---


        except (EOFError, KeyboardInterrupt):
            obsluz_przerwanie_uzytkownika()
        except Exception as e:
             print(f"\n{Fore.RED}Błąd podczas przetwarzania wyboru: {e}{Style.RESET_ALL}")
             # W razie błędu, bezpieczniej wrócić do domyślnych
             print("Przywracanie domyślnych kolumn.")
             wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']
             finalne_wybrane = ['lp'] + [k for k in oryginalne_klucze if k in wybrane_klucze_uzytkownika]
             break

    # Zwróć ostatecznie wybrane klucze, upewniając się, że 'lp' jest na początku
    return finalne_wybrane



def pobierz_nazwe_producenta_oui(mac: Optional[str], baza_oui: Dict[str, str]) -> str:
    """
    Pobiera oczyszczoną nazwę producenta na podstawie adresu MAC i bazy OUI.

    Args:
        mac: Adres MAC urządzenia (np. "AA:BB:CC:DD:EE:FF") lub None.
        baza_oui: Słownik bazy OUI, gdzie kluczem jest prefiks OUI
                  w formacie "XX-XX-XX", a wartością nazwa producenta.

    Returns:
        Oczyszczona nazwa producenta (bez dopisków typu '(hex)') lub "Nieznany",
        jeśli MAC jest nieprawidłowy, nie znaleziono go w bazie lub wystąpił błąd.
    """
    # Sprawdzenie podstawowej poprawności adresu MAC
    if not mac or mac == "Nieznany MAC" or len(mac) < 8:
        return "Nieznany"

    # Wyodrębnienie prefiksu OUI (pierwsze 3 bajty) i normalizacja formatu do XX-XX-XX
    oui_prefix = mac[:8].upper().replace(":", "-")

    # Wyszukanie producenta w bazie OUI
    producent = baza_oui.get(oui_prefix)

    if producent:
        # Usunięcie dopisków typu '(hex)' lub '(base 16)' na końcu nazwy,
        # ignorując wielkość liter i ewentualne białe znaki wokół nawiasów.
        oczyszczony_producent = re.sub(r'\s*\((?:hex|base 16)\)\s*$', '', producent, flags=re.IGNORECASE).strip()
        return oczyszczony_producent
    else:
        # Jeśli prefiks nie został znaleziony w bazie
        return "Nieznany"

# Wklej tę funkcję np. po funkcji pobierz_nazwe_hosta
def pobierz_nazwy_hostow_rownolegle(ips_do_sprawdzenia: List[str], max_workers: int = MAX_HOSTNAME_WORKERS) -> Dict[str, str]:
    """
    Pobiera nazwy hostów dla podanej listy adresów IP równolegle.

    Args:
        ips_do_sprawdzenia: Lista adresów IP do sprawdzenia.
        max_workers: Maksymalna liczba wątków do użycia.

    Returns:
        Słownik mapujący adres IP na jego nazwę hosta (lub "Nieznana"/"Błąd").
    """
    hostname_cache: Dict[str, str] = {}
    total_lookups = len(ips_do_sprawdzenia)
    completed_lookups = 0

    if total_lookups == 0:
        return hostname_cache # Zwróć pusty słownik, jeśli nie ma IP

    print(f"Pobieranie nazw hostów dla {total_lookups} adresów (max {max_workers} wątków)...")
    try:
        # Upewnij się, że nie tworzymy więcej wątków niż zadań
        actual_workers = min(max_workers, total_lookups)
        if actual_workers <= 0: return hostname_cache

        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
            future_to_ip = {executor.submit(pobierz_nazwe_hosta, ip): ip for ip in ips_do_sprawdzenia}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    hostname = future.result()
                    hostname_cache[ip] = hostname
                except Exception as exc:
                    # Logowanie błędu, ale kontynuacja
                    print(f'\n{Fore.YELLOW}Wątek pobierania nazwy dla {ip} zgłosił wyjątek: {exc}{Style.RESET_ALL}')
                    hostname_cache[ip] = "Błąd" # Oznacz błąd w cache
                completed_lookups += 1
                print(f"\rPostęp pobierania nazw: {completed_lookups}/{total_lookups} adresów sprawdzonych...", end="")
    except KeyboardInterrupt:
        # Pozwól głównej pętli obsłużyć przerwanie
        print(f"\n{Fore.YELLOW}Przerwano pobieranie nazw hostów.{Style.RESET_ALL}")
        # Zwróć to, co udało się zebrać do tej pory
    finally:
        # Wyczyść linię postępu
        print("\r" + " " * 70 + "\r", end="")

    print("Pobieranie nazw hostów zakończone.")
    return hostname_cache


def wyswietl_legende_systemow(
    wyniki_os: Dict[str, str],
    definicje_systemow: Dict[str, Dict[str, str]] = OS_DEFINITIONS # Użyj nowego słownika
) -> None:
    """
    Wyświetla legendę dla skrótów systemów operacyjnych/typów urządzeń,
    które zostały zidentyfikowane podczas skanowania, używając pełnych opisów.

    Args:
        wyniki_os: Słownik mapujący IP na przypuszczalny skrót systemu {ip: skrot_os}.
        definicje_systemow: Słownik mapujący ID na definicje {id: {"abbr": skrot, "desc": opis}}.
    """
    uzyte_skroty_set = set(wyniki_os.values()) # Zbiera unikalne skróty (np. "Win (SMB)")

    if uzyte_skroty_set:
        wyswietl_tekst_w_linii("-", DEFAULT_LINE_WIDTH, "Legenda skrótów systemów/urządzeń", Fore.LIGHTYELLOW_EX, Fore.LIGHTCYAN_EX, True)
        posortowane_skroty = sorted(list(uzyte_skroty_set))
        try:
            max_skrot_len = max(len(s) for s in posortowane_skroty) if posortowane_skroty else 10
        except ValueError:
             max_skrot_len = 10

        # Mapowanie skrótu (abbr) na pełny opis (desc) dla użytych skrótów
        skrot_do_opisu: Dict[str, str] = {}
        for key, definition in definicje_systemow.items():
            # Sprawdź, czy skrót z definicji jest jednym z tych, które wystąpiły w wynikach
            if definition.get("abbr") in uzyte_skroty_set:
                # Stwórz mapowanie: skrót -> pełny opis
                skrot_do_opisu[definition["abbr"]] = definition.get("desc", "Brak opisu") # Dodano .get dla bezpieczeństwa

        # Wyświetl legendę
        for skrot in posortowane_skroty:
            # Pobierz pełny opis używając skrótu jako klucza w nowym mapowaniu
            opis_pelny = skrot_do_opisu.get(skrot, "Brak opisu w definicjach") # Pobierz opis
            print(f"  {Fore.LIGHTMAGENTA_EX}{skrot:<{max_skrot_len}}{Style.RESET_ALL} : {opis_pelny}") # Wyświetl skrót : opis



def wyswietl_legende_portow(wyniki_portow: Dict[str, List[int]], opisy: Dict[int, str] = OPISY_PORTOW) -> None:
    """
    Wyświetla legendę dla portów, które zostały znalezione jako otwarte
    na co najmniej jednym z zeskanowanych hostów.

    Args:
        wyniki_portow: Słownik mapujący IP na listę otwartych portów {ip: [port1, port2,...]}.
        opisy: Słownik mapujący numery portów na ich opisy.
    """
    # Zbierz wszystkie unikalne otwarte porty ze wszystkich hostów
    wszystkie_otwarte_porty_set = set()
    for lista_portow in wyniki_portow.values():
        wszystkie_otwarte_porty_set.update(lista_portow)

    # Jeśli znaleziono jakiekolwiek otwarte porty, wyświetl legendę
    if wszystkie_otwarte_porty_set:
        wyswietl_tekst_w_linii("-", DEFAULT_LINE_WIDTH, "Legenda znalezionych otwartych portów", Fore.LIGHTYELLOW_EX, Fore.LIGHTCYAN_EX, True)

        # Posortuj numery portów
        posortowane_porty = sorted(list(wszystkie_otwarte_porty_set))

        # Wyświetl opis dla każdego znalezionego portu
        for port in posortowane_porty:
            opis = opisy.get(port, "Nieznana usługa") # Pobierz opis lub użyj domyślnego
            print(f"  Port {Fore.LIGHTMAGENTA_EX}{port:<5}{Style.RESET_ALL}: {opis}")

        # Możesz dodać linię końcową, jeśli chcesz
        # print("-" * DEFAULT_LINE_WIDTH)
    # Jeśli żaden port nie został znaleziony jako otwarty, nic nie rób


def skanuj_port(ip: str, port: int, timeout: float = 0.2) -> Optional[int]:
    """
    Sprawdza, czy dany port TCP jest otwarty na podanym adresie IP.

    Args:
        ip: Adres IP celu.
        port: Numer portu do sprawdzenia.
        timeout: Czas oczekiwania na połączenie w sekundach.

    Returns:
        Numer portu (int) jeśli jest otwarty, None w przeciwnym razie.
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        wynik = sock.connect_ex((ip, port))
        if wynik == 0:
            # print(f"Port {port} OTWARTY na {ip}") # Debug
            return port # <-- Zwróć numer portu, jeśli otwarty
        # else: # Debug
            # if wynik == errno.ECONNREFUSED:
            #     print(f"Port {port} ZAMKNIĘTY (odrzucono) na {ip}")
            # else:
            #     print(f"Port {port} FILTROWANY/NIEDOSTĘPNY (kod: {wynik}) na {ip}")
        return None # <-- Zwróć None, jeśli zamknięty lub błąd połączenia
    except socket.timeout:
        # print(f"Port {port} TIMEOUT na {ip}") # Debug
        return None # <-- Zwróć None przy timeout
    except socket.gaierror:
        # print(f"Błąd nazwy dla {ip}") # Debug
        return None # <-- Zwróć None przy błędzie nazwy
    except socket.error as e:
        # print(f"Błąd gniazda dla {ip}:{port} - {e}") # Debug
        return None # <-- Zwróć None przy innym błędzie gniazda
    finally:
        if sock:
            sock.close()

def skanuj_wybrane_porty_dla_ip(ip: str, porty_do_skanowania: Optional[List[int]] = None, timeout: float = 0.2) -> List[int]:
    """
    Skanuje podaną listę portów TCP na danym adresie IP równolegle
    i zwraca listę otwartych portów. Domyślnie skanuje porty zdefiniowane
    jako klucze w słowniku OPISY_PORTOW.

    Args:
        ip: Adres IP celu.
        porty_do_skanowania: Opcjonalna lista numerów portów do sprawdzenia.
                             Jeśli None, używane są klucze z OPISY_PORTOW.
        timeout: Czas oczekiwania na połączenie dla każdego portu w sekundach.

    Returns:
        Lista numerów (int) otwartych portów. Zwraca pustą listę w razie błędów
        lub gdy żaden port z listy nie jest otwarty.
    """
    otwarte_porty: List[int] = []
    if not ip: # Podstawowa walidacja
        return otwarte_porty

    # --- Użyj kluczy z OPISY_PORTOW jako domyślnej listy portów ---
    ports_to_scan = porty_do_skanowania if porty_do_skanowania is not None else list(OPISY_PORTOW.keys())
    # -------------------------------------------------------------

    if not ports_to_scan:
        # print(f"Brak portów do skanowania dla {ip}.") # Debug
        return otwarte_porty

    # print(f"Rozpoczynanie skanowania {len(ports_to_scan)} portów dla {ip} (max {MAX_PORT_SCAN_WORKERS} wątków)...") # Debug

    try:
        # Upewnij się, że nie tworzymy więcej wątków niż portów do skanowania
        max_workers = min(MAX_PORT_SCAN_WORKERS, len(ports_to_scan))
        if max_workers <= 0: # Zapobiegaj błędom przy 0 portach
             return otwarte_porty

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Tworzymy mapowanie future -> port, aby wiedzieć, który port był skanowany
            future_to_port = {executor.submit(skanuj_port, ip, port, timeout): port for port in ports_to_scan}

            # Zbieramy wyniki w miarę ich kończenia
            for future in concurrent.futures.as_completed(future_to_port):
                port_skanowany = future_to_port[future]
                try:
                    wynik = future.result() # Pobierz wynik (numer portu lub None)
                    if wynik is not None: # Jeśli skanuj_port zwrócił numer portu
                        otwarte_porty.append(wynik)
                except Exception as exc:
                    # Logowanie błędu dla konkretnego portu, ale kontynuacja skanowania innych
                    # print(f"Błąd podczas skanowania portu {port_skanowany} na {ip}: {exc}") # Debug
                    pass # Ignoruj błędy pojedynczych portów, aby nie przerywać całego skanowania

    except KeyboardInterrupt:
        # Jeśli użytkownik przerwie (Ctrl+C) podczas skanowania portów dla tego IP
        # print(f"\n{Fore.YELLOW}Przerwano skanowanie portów dla {ip}.{Style.RESET_ALL}")
        # obsluz_przerwanie_uzytkownika() # Obsłuż przerwanie globalnie - lepiej w main
        # Zwracamy to, co udało się znaleźć do tej pory
        pass # Pozwól obsłudze w main złapać KeyboardInterrupt
    except Exception as e:
        # Ogólny błąd przy tworzeniu puli wątków lub inny nieoczekiwany
        print(f"{Fore.RED}Nieoczekiwany błąd podczas skanowania portów dla {ip}: {e}{Style.RESET_ALL}")

    # Sortujemy listę otwartych portów przed zwróceniem
    otwarte_porty.sort()
    # print(f"Skanowanie portów dla {ip} zakończone. Otwarte: {otwarte_porty}") # Debug
    return otwarte_porty

def zgadnij_system_operacyjny(
    ip_address: str,
    otwarte_porty_znane: Optional[List[int]] = None,
    porty_do_skanowania_jesli_nieznane: Optional[List[int]] = None,
    timeout_portu: float = 0.2,
    filtry_os: List[Dict[str, Any]] = OS_FILTERS # Użyj globalnych filtrów jako domyślnych
) -> str:
    """
    Próbuje odgadnąć typ systemu operacyjnego/urządzenia na podstawie otwartych portów TCP,
    używając listy słowników filtrów. Zwraca skrót zdefiniowany w OS_ABBREVIATIONS.

    PRIORYTET: Używa listy `otwarte_porty_znane`, jeśli została podana.
    Jeśli `otwarte_porty_znane` jest None, wykonuje skanowanie portów.

    Args:
        ip_address: Adres IP urządzenia do sprawdzenia.
        otwarte_porty_znane: Opcjonalna lista już znanych otwartych portów dla tego IP.
        porty_do_skanowania_jesli_nieznane: Lista portów do skanowania, jeśli `otwarte_porty_znane` jest None.
                                            Jeśli None, skanuje porty z OPISY_PORTOW.
        timeout_portu: Timeout dla skanowania pojedynczego portu.
        filtry_os: Lista słowników definiujących reguły dopasowania OS.

    Returns:
        Przypuszczalny typ systemu jako string (skrót z OS_ABBREVIATIONS)
        lub komunikat błędu.
    """
    # 1. Walidacja IP
    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        return "Nieprawidłowy adres IP"

    otwarte_porty: List[int] = []

    # 2. Ustalenie listy otwartych portów (z cache lub skanowania)
    if otwarte_porty_znane is not None:
        otwarte_porty = otwarte_porty_znane
    else:
        # Logika skanowania
        porty_do_skanowania = porty_do_skanowania_jesli_nieznane
        komunikat_skanowania = ""
        # Jeśli nie podano listy lub jest pusta, skanuj wszystkie znane porty
        if porty_do_skanowania is None or not porty_do_skanowania:
            porty_do_skanowania = list(OPISY_PORTOW.keys())
            komunikat_skanowania = f"INFO: Brak znanych portów. Skanowanie portów z OPISY_PORTOW dla {ip_address}..."
        else:
            komunikat_skanowania = f"INFO: Brak znanych portów. Skanowanie podanych portów {porty_do_skanowania} dla {ip_address}..."

        print(komunikat_skanowania)
        otwarte_porty = skanuj_wybrane_porty_dla_ip(ip_address, porty_do_skanowania, timeout_portu)
        print(f"INFO: Zakończono skanowanie dla {ip_address}. Otwarte porty: {otwarte_porty}")

    # 3. Heurystyki zgadywania systemu operacyjnego z użyciem filtrów
    if not otwarte_porty:
        return OS_ABBREVIATIONS["UNKNOWN_NO_PORTS"]

    otwarte_porty_set = set(otwarte_porty)

    # Sortuj filtry według priorytetu (niższa liczba = wyższy priorytet)
    posortowane_filtry = sorted(filtry_os, key=lambda x: x.get('priority', 999))

    # Iteruj przez posortowane filtry
    for filtr in posortowane_filtry:
        id_os = filtr.get("id")
        ports_any = filtr.get("ports_any", set())
        ports_all = filtr.get("ports_all", set())

        # Sprawdź warunek 'ports_all' - wszystkie muszą być obecne
        warunek_all_spelniony = ports_all.issubset(otwarte_porty_set)

        # Sprawdź warunek 'ports_any' - przynajmniej jeden musi być obecny (jeśli zdefiniowano)
        warunek_any_spelniony = True # Domyślnie prawda, jeśli ports_any jest puste
        if ports_any:
            warunek_any_spelniony = any(p in otwarte_porty_set for p in ports_any)

        # Jeśli oba warunki są spełnione, znaleziono dopasowanie
        if warunek_all_spelniony and warunek_any_spelniony:
            # Upewnij się, że ID istnieje w OS_ABBREVIATIONS
            if id_os in OS_ABBREVIATIONS: # Sprawdza w wygenerowanym słowniku
                return OS_ABBREVIATIONS[id_os] # Zwraca skrót (abbr)
            else:
                # Jeśli ID z filtra nie ma odpowiednika w skrótach, zwróć samo ID
                print(f"{Fore.YELLOW}Ostrzeżenie: ID filtra '{id_os}' nie znaleziono w OS_ABBREVIATIONS.{Style.RESET_ALL}")
                return id_os # Zwróć ID filtra jako fallback

    # --- Domyślny przypadek, jeśli żaden filtr nie pasował ---
    # Sprawdź jeszcze raz generyczne przypadki, które mogły nie pasować do specyficznych reguł
    web_ports_found = {p for p in [80, 443, 8000, 8080, 8081, 8443] if p in otwarte_porty_set}
    if web_ports_found:
         # Sprawdźmy jeszcze raz Home Assistant, bo mógł nie pasować do bardziej specyficznych reguł
         if 8123 in otwarte_porty_set or 4357 in otwarte_porty_set:
             # Upewnij się, że HOME_ASSISTANT jest w skrótach
             return OS_ABBREVIATIONS.get("HOME_ASSISTANT", "HomeAsst")
         # Jeśli nie Home Assistant, ale jest web, zwróć generyczny web
         return OS_ABBREVIATIONS.get("NETWORK_WEB", "NetDev/Web")

    # Jeśli nic nie pasowało, a są jakieś otwarte porty
    return OS_ABBREVIATIONS.get("UNKNOWN_PORTS", "Nieznany (Ports)")



def pobierz_wszystkie_aktywne_ip() -> Tuple[Dict[str, List[str]], Optional[str]]:
    """
    Pobiera adresy IP (IPv4) wszystkich aktywnych interfejsów sieciowych
    oraz identyfikuje prawdopodobny główny adres IP używany do połączeń wychodzących.

    Wykorzystuje psutil do znalezienia interfejsów, które są w stanie "UP"
    i zwraca słownik mapujący nazwę interfejsu na listę jego adresów IPv4
    (ignorując loopback i link-local).
    Dodatkowo wywołuje pobierz_ip_interfejsu() w celu znalezienia głównego IP.

    Returns:
        Krotka zawierająca:
        - Słownik, gdzie kluczem jest nazwa interfejsu (str),
          a wartością jest lista adresów IPv4 (List[str]) przypisanych
          do tego interfejsu.
        - Prawdopodobny główny adres IP wychodzący (Optional[str])
          zidentyfikowany przez pobierz_ip_interfejsu(), lub None.
        Zwraca (pusty słownik, None), jeśli psutil jest niedostępny lub wystąpi błąd.
    """
    aktywne_interfejsy_ip: Dict[str, List[str]] = {}
    glowny_ip_wychodzacy: Optional[str] = None

    # Najpierw spróbuj zidentyfikować główny IP wychodzący
    # Ta funkcja już istnieje i robi to dobrze
    glowny_ip_wychodzacy = pobierz_ip_interfejsu()

    if not PSUTIL_AVAILABLE:
        print(f"{Fore.YELLOW}Biblioteka 'psutil' nie jest dostępna. Nie można pobrać pełnej listy interfejsów.{Style.RESET_ALL}")
        # Zwracamy pusty słownik, ale zachowujemy znaleziony główny IP (jeśli się udało)
        return aktywne_interfejsy_ip, glowny_ip_wychodzacy

    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        for nazwa_interfejsu, statystyki in stats.items():
            if statystyki.isup:
                if nazwa_interfejsu in addrs:
                    adresy_ipv4_interfejsu: List[str] = []
                    for snic in addrs[nazwa_interfejsu]:
                        if snic.family == socket.AF_INET:
                            try:
                                ip_addr = ipaddress.ip_address(snic.address)
                                if not ip_addr.is_loopback and not ip_addr.is_link_local:
                                    adresy_ipv4_interfejsu.append(snic.address)
                            except ValueError:
                                continue
                    if adresy_ipv4_interfejsu:
                        aktywne_interfejsy_ip[nazwa_interfejsu] = adresy_ipv4_interfejsu

    except Exception as e:
        print(f"{Fore.RED}Wystąpił błąd podczas pobierania informacji o interfejsach sieciowych z psutil: {e}{Style.RESET_ALL}")
        # W razie błędu psutil, nadal zwracamy to, co udało się znaleźć przez pobierz_ip_interfejsu
        return {}, glowny_ip_wychodzacy

    # Zwracamy słownik wszystkich aktywnych IP oraz zidentyfikowany główny IP
    return aktywne_interfejsy_ip, glowny_ip_wychodzacy

def wyswietl_tekst_w_linii(znak: str,
                           dlugosc_linii: int,
                           tekst: Optional[str] = None,
                           kolor_tekstu: Optional[str] = None,
                           kolor_znaku: Optional[str] = None,
                           dodaj_odstepy: bool = False):
    """
    Wyświetla tekst wyśrodkowany w linii o zadanej długości,
    otoczony podanym znakiem i spacjami, z opcjonalnymi, osobnymi
    kolorami dla tekstu i znaków wypełniających oraz opcjonalnymi odstępami.
    Jeśli tekst nie zostanie podany, wyświetla linię wypełnioną znakiem.

    Args:
        znak: Znak używany do wypełnienia reszty linii. Powinien być pojedynczym znakiem.
        dlugosc_linii: Całkowita docelowa długość linii.
        tekst (Optional[str]): Tekst do wyświetlenia na środku. Jeśli None lub pusty, linia będzie wypełniona znakiem.
        kolor_tekstu (Optional[str]): Opcjonalny kod koloru dla tekstu głównego.
        kolor_znaku (Optional[str]): Opcjonalny kod koloru dla znaków wypełniających.
        dodaj_odstepy (bool): Jeśli True, dodaje pustą linię przed i po głównej linii.
    """
    # Sprawdzenie i korekta znaku
    if not znak:
        znak = "-"
    elif len(znak) > 1:
        znak = znak[0]

    linia_wynikowa = ""

    # Sprawdź, czy tekst został podany i nie jest pusty
    if tekst and tekst.strip():
        # --- Logika dla tekstu ---
        tekst_ze_spacjami = f" {tekst.strip()} " # Usuń ewentualne białe znaki z tekstu
        dlugosc_tekstu = len(tekst_ze_spacjami)

        # Oblicz, ile znaków wypełniających potrzeba
        pozostala_dlugosc = dlugosc_linii - dlugosc_tekstu
        if pozostala_dlugosc < 0:
            pozostala_dlugosc = 0 # Tekst jest dłuższy niż linia

        # Podziel znaki wypełniające na lewą i prawą stronę
        dlugosc_lewa = math.floor(pozostala_dlugosc / 2)
        dlugosc_prawa = math.ceil(pozostala_dlugosc / 2)

        znaki_lewe = znak * dlugosc_lewa
        znaki_prawe = znak * dlugosc_prawa

        # Budowanie linii z kolorami
        # Dodaj lewe znaki z kolorem (jeśli podano)
        if kolor_znaku and COLORAMA_AVAILABLE:
            linia_wynikowa += f"{kolor_znaku}{znaki_lewe}{Style.RESET_ALL}"
        else:
            linia_wynikowa += znaki_lewe

        # Dodaj tekst główny z kolorem (jeśli podano)
        if kolor_tekstu and COLORAMA_AVAILABLE:
            linia_wynikowa += f"{kolor_tekstu}{tekst_ze_spacjami}{Style.RESET_ALL}"
        else:
            linia_wynikowa += tekst_ze_spacjami

        # Dodaj prawe znaki z kolorem (jeśli podano)
        if kolor_znaku and COLORAMA_AVAILABLE:
            linia_wynikowa += f"{kolor_znaku}{znaki_prawe}{Style.RESET_ALL}"
        else:
            linia_wynikowa += znaki_prawe
    else:
        # --- Logika dla braku tekstu (wypełnienie całej linii znakiem) ---
        pelna_linia_znakow = znak * dlugosc_linii
        if kolor_znaku and COLORAMA_AVAILABLE:
            linia_wynikowa = f"{kolor_znaku}{pelna_linia_znakow}{Style.RESET_ALL}"
        else:
            linia_wynikowa = pelna_linia_znakow

    # Dodaj odstęp przed, jeśli wymagane
    if dodaj_odstepy:
        print()

    # Wyświetl finalną linię
    print(linia_wynikowa)

    # Dodaj odstęp po, jeśli wymagane
    if dodaj_odstepy:
        print()


def obsluz_przerwanie_uzytkownika():
    """
    Obsługuje wyjątek KeyboardInterrupt (Ctrl+C).
    Czyści bieżącą linię konsoli, wyświetla standardowy komunikat
    o przerwaniu i kończy działanie skryptu z kodem 0.
    """
    try:
        # Wyczyść bieżącą linię (na wypadek, gdyby kursor był w trakcie input() lub postępu)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
    except Exception:
        # Ignoruj błędy podczas czyszczenia, np. jeśli strumień jest zamknięty
        pass
    # Wyświetl ujednolicony komunikat i zakończ
    print(f"\n{Fore.YELLOW}Przerwano przez użytkownika. Zakończono.{Style.RESET_ALL}\n")
    sys.exit(0) # Zakończ skrypt z kodem sukcesu (bo to intencja użytkownika)

def przelicz_sekundy_na_minuty_sekundy(total_seconds: int) -> str:
  """
  Przelicza całkowitą liczbę sekund na format "minuty:sekundy".

  Args:
    total_seconds: Całkowita liczba sekund do przeliczenia.

  Returns:
    String w formacie "M:SS", gdzie M to minuty, a SS to sekundy
    z wiodącym zerem, jeśli jest to konieczne.
    Zwraca "0:00" dla wartości ujemnych lub zerowych.
  """
  if total_seconds <= 0:
    return "0:00"

  # Oblicz minuty używając dzielenia całkowitego
  minuty = total_seconds // 60
  # Oblicz pozostałe sekundy używając operatora modulo
  sekundy = total_seconds % 60

  # Zwróć sformatowany string, upewniając się, że sekundy mają dwa miejsca
  # (np. 7 sekund jako "07")
  return f"{minuty}:{sekundy:02d}"



def pobierz_brame_domyslna() -> Optional[str]:
    """
    Pobiera adres IP bramy domyślnej dla bieżącego systemu operacyjnego.

    Próbuje użyć standardowych poleceń systemowych:
    - Windows: 'route print'
    - Linux: 'ip route'
    - macOS: 'netstat -nr'

    Returns:
        Adres IP bramy domyślnej jako string (np. "192.168.1.1")
        lub None, jeśli nie można go znaleźć lub wystąpił błąd.
    """
    system = platform.system().lower()
    gateway_ip = None
    cmd = []
    pattern = None
    encoding = DEFAULT_ENCODING # Domyślne kodowanie

    try:
        if system == "windows":
            # Szukamy linii z trasą 0.0.0.0, maską 0.0.0.0
            # Brama jest zwykle w trzeciej kolumnie (po sieci i masce)
            cmd = ["route", "print", "0.0.0.0"]
            # route print często używa kodowania OEM
            encoding = WINDOWS_OEM_ENCODING
            # Wzorzec szuka linii zaczynającej się od 0.0.0.0, potem 0.0.0.0,
            # a następnie przechwytuje następny adres IP w tej linii.
            # \s+ dopasowuje jedną lub więcej spacji.
            pattern = re.compile(r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+.*", re.MULTILINE)

        elif system == "linux":
            # Szukamy linii zaczynającej się od 'default via'
            cmd = ["ip", "route", "show", "default"]
            encoding = 'utf-8' # ip route zwykle używa UTF-8
            # Wzorzec szuka 'default via', a następnie przechwytuje adres IP
            pattern = re.compile(r"^default via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+.*")

        elif system == "darwin": # macOS
            # Szukamy linii zaczynającej się od 'default'
            cmd = ["netstat", "-nr"]
            encoding = 'utf-8' # netstat zwykle używa UTF-8
            # Wzorzec szuka 'default', a następnie przechwytuje drugi adres IP w linii
            # (pierwszy to 'default', drugi to brama)
            pattern = re.compile(r"^default\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+.*", re.MULTILINE)
        else:
            print(f"Nieobsługiwany system operacyjny dla pobierania bramy domyślnej: {system}")
            return None

        # Uruchomienie polecenia
        process = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore', check=True, shell=False)
        output = process.stdout

        # Przeszukiwanie wyniku za pomocą wyrażenia regularnego
        match = pattern.search(output)
        if match:
            gateway_ip = match.group(1)
            # Dodatkowa weryfikacja, czy to poprawny adres IP (opcjonalnie)
            try:
                # Prosta walidacja formatu
                parts = gateway_ip.split('.')
                if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                    return gateway_ip
                else:
                     print(f"Znaleziono potencjalną bramę, ale ma niepoprawny format: {gateway_ip}")
                     return None
            except ValueError:
                 print(f"Znaleziono potencjalną bramę, ale zawiera nie-liczbowe części: {gateway_ip}")
                 return None
        else:
            # Komunikat, jeśli wzorzec nie został znaleziony w wyniku polecenia
            print(f"Nie znaleziono wzorca bramy domyślnej w wyniku polecenia: {' '.join(cmd)}")
            return None

    except FileNotFoundError:
         print(f"Błąd: Polecenie '{cmd[0]}' nie znalezione. Upewnij się, że jest w ścieżce systemowej.")
         return None
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas wykonywania polecenia '{' '.join(cmd)}': {e}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"Nieoczekiwany błąd podczas pobierania bramy domyślnej: {e}")
        return None

def czy_aktywny_vpn_lub_podobny() -> bool:
    """
    Sprawdza, czy istnieje interfejs VPN, który jest UP.
    Priorytetyzuje:
    1. Interfejsy UP z adresem IP w zakresie CGNAT (100.64.0.0/10) - traktowane jako AKTYWNE.
    2. Interfejsy UP z nazwami 'tun', 'tap', 'wg', 'open' ORAZ posiadające adres IPv4 inny niż loopback/link-local - traktowane jako AKTYWNE.
    3. Interfejsy UP z nazwą 'tailscale' ORAZ posiadające adres IPv4 inny niż loopback/link-local - traktowane jako AKTYWNE.
    4. Interfejsy UP z nazwami 'tun', 'tap', 'wg', 'open' (bez "ważnego" IP) - traktowane jako POTENCJALNE/NIEPOŁĄCZONE.
    5. Interfejsy UP z nazwą 'tailscale' (bez "ważnego" IP) - traktowane jako POTENCJALNE/NIEPOŁĄCZONE.
    Wymaga biblioteki psutil.
    """
    if not PSUTIL_AVAILABLE:
        return False

    tailscale_network = ipaddress.ip_network('100.64.0.0/10')
    primary_vpn_prefixes: List[str] = ['tun', 'tap', 'wg', 'open']
    tailscale_prefix: str = 'tailscale'

    try:
        interfaces_addrs = psutil.net_if_addrs()
        interfaces_stats = psutil.net_if_stats()

        found_by_ip: Optional[str] = None
        found_by_primary_name_with_ip: Optional[str] = None
        found_by_tailscale_name_with_ip: Optional[str] = None
        found_by_primary_name_only: Optional[str] = None
        found_by_tailscale_name_only: Optional[str] = None

        for if_name, stats in interfaces_stats.items():
            if stats.isup:
                if_name_lower = if_name.lower()
                has_valid_ipv4 = False

                if if_name in interfaces_addrs:
                    snic_list = interfaces_addrs[if_name]
                    for snic in snic_list:
                        if snic.family == socket.AF_INET:
                            try:
                                ip_addr = ipaddress.ip_address(snic.address)
                                if ip_addr in tailscale_network:
                                    found_by_ip = if_name
                                    has_valid_ipv4 = True
                                    break
                                if not ip_addr.is_loopback and not ip_addr.is_link_local:
                                    has_valid_ipv4 = True
                            except ValueError:
                                continue
                    if found_by_ip: continue

                name_matches_primary = False
                for prefix in primary_vpn_prefixes:
                    if if_name_lower.startswith(prefix):
                        name_matches_primary = True
                        if has_valid_ipv4:
                            if not found_by_primary_name_with_ip:
                                found_by_primary_name_with_ip = if_name
                        else:
                            if not found_by_primary_name_only:
                                found_by_primary_name_only = if_name
                        break

                if name_matches_primary and not if_name_lower.startswith(tailscale_prefix):
                     continue

                if if_name_lower.startswith(tailscale_prefix):
                    if has_valid_ipv4:
                         if not found_by_tailscale_name_with_ip:
                             found_by_tailscale_name_with_ip = if_name
                    else:
                         if not found_by_tailscale_name_only:
                             found_by_tailscale_name_only = if_name

        # --- Krok 2: Decyzja na podstawie zebranych kandydatów i priorytetów ---
        if found_by_ip:
            wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN (CGNAT) wg adresu IP: {found_by_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            # print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN (CGNAT) wg adresu IP: {found_by_ip}{Style.RESET_ALL}")
            return True
        elif found_by_primary_name_with_ip:
            wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN wg nazwy (główny z IP): {found_by_primary_name_with_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            # print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN wg nazwy (główny z IP): {found_by_primary_name_with_ip}{Style.RESET_ALL}")
            return True
        elif found_by_tailscale_name_with_ip:
             wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN wg nazwy (Tailscale z IP): {found_by_tailscale_name_with_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            #  print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN wg nazwy (Tailscale z IP): {found_by_tailscale_name_with_ip}{Style.RESET_ALL}")
             return True
        # --- ZMIANA KOMUNIKATÓW TUTAJ ---
        elif found_by_primary_name_only:
            # Zmieniono "AKTYWNY" na "potencjalny" i dodano "(może nie być połączony)"
            wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto potencjalny interfejs VPN wg nazwy (główny, może nie być połączony): {found_by_primary_name_only}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            # print(f"\n{Fore.CYAN}Info: Wykryto potencjalny interfejs VPN wg nazwy (główny, może nie być połączony): {found_by_primary_name_only}{Style.RESET_ALL}")
            return False # Zwracama False
        elif found_by_tailscale_name_only:
            # Zmieniono "AKTYWNY" na "potencjalny" i dodano "(może nie być połączony)"
            wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto potencjalny interfejs VPN (może nie być połączony)",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            # print(f"\n{Fore.CYAN}Info: Wykryto potencjalny interfejs VPN (może nie być połączony){Style.RESET_ALL}")
            return False # Zwracama False
        else:
            return False

    except Exception as e:
        print(f"{Fore.YELLOW}Ostrzeżenie: Wystąpił błąd podczas sprawdzania interfejsów sieciowych dla VPN: {e}{Style.RESET_ALL}")
        return False

def pobierz_tabele_arp():
    """
    Pobiera tabelę ARP dla danego systemu operacyjnego.

    Returns:
        str: Zawartość tabeli ARP lub None w przypadku błędu.
    """
    try:
        if platform.system().lower() == "windows":
            wynik = subprocess.check_output("arp -a", shell=True, encoding="utf-8", errors='ignore')
        elif platform.system().lower() == "linux":
            wynik = subprocess.check_output("ip -4 neighbor", shell=True, encoding="utf-8", errors='ignore')
        elif platform.system().lower() == "darwin":  # macOS
            wynik = subprocess.check_output("arp -an", shell=True, encoding="utf-8", errors='ignore')
        else:
            print("Nieobsługiwany system operacyjny.")
            return None
        return wynik
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas pobierania tabeli ARP: {e}")
        return None
    except Exception as e:
        print(f"Inny błąd podczas pobierania tabeli ARP: {e}")
        return None

def parsuj_tabele_arp(wynik_arp: Optional[str], siec_prefix: str) -> Dict[str, str]:
    """
    Parsuje tabelę ARP i zwraca słownik mapujący adresy IP na adresy MAC
    dla wpisów pasujących do podanego prefiksu sieciowego.

    Args:
        wynik_arp: Wyjście polecenia arp.
        siec_prefix: Prefiks sieciowy do filtrowania (np. "192.168.0.").

    Returns:
        Słownik {ip (str): mac (str)}.
    """
    arp_map: Dict[str, str] = {}
    if wynik_arp is None:
        return arp_map

    # Wzorce Regex skompilowane dla wydajności
    ip_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
    mac_pattern = re.compile(r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})")

    linie = wynik_arp.strip().splitlines()
    for linia in linie:
        # Ignoruj linie nagłówkowe lub puste
        if not linia or linia.lower().startswith("interface") or linia.lower().startswith("internet address"):
            continue

        ip_match = ip_pattern.search(linia)
        mac_match = mac_pattern.search(linia)

        if ip_match and mac_match:
            ip = ip_match.group(1)
            mac = mac_match.group(1).upper().replace("-", ":") # Ujednolicenie formatu MAC

            # Sprawdź, czy IP pasuje do prefiksu i nie jest multicastem
            if ip.startswith(siec_prefix) and not any(ip.startswith(mp) for mp in MULTICAST_PREFIXES):
                # Zapisz mapowanie IP -> MAC
                arp_map[ip] = mac
    return arp_map

def _ping_single_ip(ip: str, system: str) -> Optional[str]:
    """
    Wysyła pojedynczy ping do podanego adresu IP.
    Używa bezpiecznego cytowania z shlex.quote i shell=True.

    Args:
        ip: Adres IP do spingowania.
        system: Nazwa systemu operacyjnego ('windows' lub inny).

    Returns:
        Adres IP (str) jeśli ping się powiódł (host odpowiedział), None w przeciwnym razie.
    """
    safe_ip = shlex.quote(ip)
    try:
        if system == "windows":
            # Zwiększamy timeout, aby dać więcej czasu na odpowiedź, zwłaszcza przez VPN
            polecenie_str = f"ping -n 1 -w {PING_TIMEOUT_MS * 2} {safe_ip} > NUL" # Zwiększony timeout
        else: # Linux/macOS
            # Zwiększamy timeout
            polecenie_str = f"ping -c 1 -W {PING_TIMEOUT_SEC * 2} {safe_ip} > /dev/null" # Zwiększony timeout

        # Uruchomienie polecenia z shell=True
        subprocess.run(polecenie_str, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        #print(f"Ping OK: {ip}") # Debug
        return ip # Zwróć IP, jeśli ping udany
    except subprocess.CalledProcessError:
        #print(f"Ping FAIL: {ip}") # Debug
        return None # Ping nieudany (timeout lub inny błąd ping)
    except FileNotFoundError:
        # Błąd krytyczny - ping nie jest dostępny w systemie
        print(f"{Fore.RED}Błąd: Polecenie 'ping' nie znalezione.{Style.RESET_ALL}")
        raise # Rzucamy wyjątek, aby zatrzymać pulę wątków
    except Exception as e:
        print(f"{Fore.RED}Błąd podczas pingowania {ip}: {e}{Style.RESET_ALL}")
        return None # Inny błąd traktujemy jako nieudany ping
    
def polacz_listy_ip(lista_arp: List[str], lista_ping: List[str]) -> List[str]:
    """
    Łączy dwie listy adresów IP, usuwa duplikaty i sortuje wynikową listę.

    Args:
        lista_arp: Lista adresów IP uzyskanych z tabeli ARP.
        lista_ping: Lista adresów IP, które odpowiedziały na ping.

    Returns:
        Posortowana lista unikalnych adresów IP z obu list wejściowych.
    """
    # print("Łączenie list adresów IP z ARP i ping...")

    # Połącz obie listy
    polaczona_lista = lista_arp + lista_ping

    # Usuń duplikaty używając set
    unikalne_ip_set = set(polaczona_lista)

    # Konwertuj z powrotem na listę
    unikalne_ip_lista = list(unikalne_ip_set)

    # Sortuj listę numerycznie dla lepszej czytelności
    try:
        # Użyj ipaddress do poprawnego sortowania adresów IP
        unikalne_ip_lista.sort(key=ipaddress.ip_address)
    except ValueError:
        # Fallback na sortowanie alfabetyczne, jeśli wystąpi błąd
        # (np. jeśli lista zawiera niepoprawne adresy IP)
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można posortować adresów IP numerycznie. Sortowanie alfabetyczne.{Style.RESET_ALL}")
        unikalne_ip_lista.sort()

    # print(f"Połączono i usunięto duplikaty. Łączna liczba unikalnych adresów IP: {len(unikalne_ip_lista)}")
    return unikalne_ip_lista


def pinguj_zakres(siec_prefix: str, start_ip: int, end_ip: int) -> List[str]:
    """
    Pinguj zakres adresów IP w danej podsieci RÓWNOLEGLE, używając puli wątków
    i bezpiecznego shell=True z shlex.quote.

    Args:
        siec_prefix: Prefiks sieciowy (np. "192.168.0.").
        start_ip: Początkowy numer hosta.
        end_ip: Końcowy numer hosta.

    Returns:
        Lista adresów IP (str), które odpowiedziały na ping.
    """
    print(f"Pingowanie zakresu adresów {siec_prefix}{start_ip} - {siec_prefix}{end_ip} (równolegle, max {MAX_PING_WORKERS} wątków)...")
    print("\r" + " " * 70 + "\r", end="") # Wyczyść linię postępu
    system = platform.system().lower()
    ips_to_ping = [f"{siec_prefix}{i}" for i in range(start_ip, end_ip + 1)]
    total_ips = len(ips_to_ping)
    completed_count = 0
    successful_ips: List[str] = [] # Lista do przechowywania udanych IP
    ping_failed_critically = False # Flaga błędu krytycznego

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PING_WORKERS) as executor:
            futures = {executor.submit(_ping_single_ip, ip, system): ip for ip in ips_to_ping}

            for future in concurrent.futures.as_completed(futures):
                completed_count += 1
                print(f"\rPostęp pingowania: {completed_count}/{total_ips} adresów sprawdzonych...", end="")
                ip_processed = futures[future] # Pobierz IP powiązane z tym future

                try:
                    result = future.result() # Pobierz wynik (IP lub None) lub rzuć wyjątek
                    if result: # Jeśli wynik nie jest None (czyli ping się udał)
                        successful_ips.append(result)
                except FileNotFoundError:
                     print(f"\n{Fore.RED}Błąd krytyczny: Polecenie 'ping' nie znalezione. Przerywanie pingowania.{Style.RESET_ALL}")
                     ping_failed_critically = True
                     executor.shutdown(wait=False, cancel_futures=True)
                     break
                except Exception as exc:
                     print(f'\n{Fore.YELLOW}Wątek pingowania dla {ip_processed} zgłosił wyjątek: {exc}{Style.RESET_ALL}')

    except KeyboardInterrupt:
        obsluz_przerwanie_uzytkownika()
    finally:
        # Wyczyść linię postępu
        print("\r" + " " * 70 + "\r", end="") # Wyczyść linię postępu

    if not ping_failed_critically:
        print(f"Pingowanie zakończone. Odpowiedziało {len(successful_ips)} hostów.")
    else:
        print("Pingowanie przerwane z powodu błędu krytycznego.")

    return successful_ips # Zwróć listę udanych IP


def pobierz_nazwe_hosta(ip: str) -> str:
    """Pobiera nazwę hosta dla danego IP z timeoutem."""
    nazwa_wyswietlana = "Nieznana"
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(HOSTNAME_LOOKUP_TIMEOUT)
    try:
        if platform.system().lower() == "windows":
            hostname = socket.gethostbyaddr(ip)[0]
            if hostname != ip:
                nazwa_wyswietlana = hostname
        else:
            hostname, _ = socket.getnameinfo((ip, 0), 0)
            if hostname != ip:
                nazwa_wyswietlana = hostname
    except (socket.herror, socket.gaierror) as e:
        # Możesz odkomentować, jeśli chcesz widzieć błędy rozwiązania nazwy
        # print(f"Info: Nie można rozwiązać nazwy dla {ip}: {e}")
        pass # Nie udało się rozwiązać nazwy
    except socket.timeout:
        # Zmień 'pass' na 'print' do debugowania
        print(f"Info: Timeout ({HOSTNAME_LOOKUP_TIMEOUT}s) podczas pobierania nazwy hosta dla {ip}")
        pass # Możesz zostawić pass, ale print powyżej da informację
    except Exception as e:
        # Zmień 'pass' na 'print' do debugowania
        print(f"Błąd: Nieoczekiwany błąd podczas pobierania nazwy hosta dla {ip}: {e}")
        pass # Możesz zostawić pass, ale print powyżej da informację
    finally:
        socket.setdefaulttimeout(original_timeout) # Przywróć domyślny timeout
    return nazwa_wyswietlana

def pobierz_tabele_arp() -> Optional[str]:
    """
    Pobiera tabelę ARP dla danego systemu operacyjnego.

    Returns:
        str: Zawartość tabeli ARP lub None w przypadku błędu.
    """
    try:
        system = platform.system().lower()
        if system == "windows":
            # Użycie kodowania cp852 (lub innego OEM) może być konieczne dla polskich znaków
            # errors='ignore' pomoże uniknąć błędów dekodowania
            wynik = subprocess.check_output("arp -a", shell=True, encoding='cp852', errors='ignore')
        elif system == "linux":
            wynik = subprocess.check_output("ip -4 neighbor", shell=True, encoding="utf-8", errors='ignore')
        elif system == "darwin":  # macOS
            wynik = subprocess.check_output("arp -an", shell=True, encoding="utf-8", errors='ignore')
        else:
            print(f"Nieobsługiwany system operacyjny: {system}")
            return None
        return wynik
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas pobierania tabeli ARP: {e}")
        return None
    except FileNotFoundError:
        cmd = "arp -a" if platform.system().lower() == "windows" else "ip -4 neighbor" if platform.system().lower() == "linux" else "arp -an"
        print(f"Błąd: Polecenie '{cmd.split()[0]}' nie znalezione.")
        return None
    except Exception as e:
        print(f"Inny błąd podczas pobierania tabeli ARP: {e}")
        return None

def parsuj_tabele_arp(wynik_arp: Optional[str], siec_prefix: str) -> Dict[str, str]:
    """
    Parsuje tabelę ARP i zwraca słownik mapujący adresy IP na adresy MAC
    dla wpisów pasujących do podanego prefiksu sieciowego.

    Args:
        wynik_arp: Wyjście polecenia arp.
        siec_prefix: Prefiks sieciowy do filtrowania (np. "192.168.0.").

    Returns:
        Słownik {ip (str): mac (str)}.
    """
    arp_map: Dict[str, str] = {}
    if wynik_arp is None:
        return arp_map

    # Wzorce Regex skompilowane dla wydajności
    ip_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
    # Bardziej elastyczny wzorzec MAC, akceptujący różne separatory i wielkość liter
    mac_pattern = re.compile(r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}")

    linie = wynik_arp.strip().splitlines()
    for linia in linie:
        # Ignoruj linie nagłówkowe lub puste
        linia_lower = linia.lower()
        if not linia.strip() or linia_lower.startswith("interface") or linia_lower.startswith("internet address") or "ff-ff-ff-ff-ff-ff" in linia_lower:
            continue

        ip_match = ip_pattern.search(linia)
        mac_match = mac_pattern.search(linia)

        if ip_match and mac_match:
            ip = ip_match.group(1)
            mac_raw = mac_match.group(0)
            # Normalizacja MAC do XX:XX:XX:XX:XX:XX
            mac = mac_raw.upper().replace("-", ":")

            # Sprawdź, czy IP pasuje do prefiksu i nie jest multicastem/broadcastem
            # (Broadcast MAC ff:ff:ff:ff:ff:ff jest już filtrowany wyżej)
            if ip.startswith(siec_prefix) and not any(ip.startswith(mp) for mp in MULTICAST_PREFIXES):
                # Zapisz mapowanie IP -> MAC, unikając duplikatów IP (ostatni wpis wygrywa)
                arp_map[ip] = mac
    return arp_map

# --- Nowa funkcja ---
def pobierz_ip_z_arp(siec_prefix: str) -> List[str]:
    """
    Pobiera listę adresów IP z tabeli ARP pasujących do danego prefiksu sieciowego.

    Args:
        siec_prefix: Prefiks sieciowy do filtrowania (np. "192.168.0.").

    Returns:
        Lista adresów IP (str) znalezionych w tabeli ARP dla danego prefiksu,
        lub pusta lista w przypadku błędu lub braku pasujących wpisów.
    """
    print(f"Pobieranie adresów IP z tabeli ARP dla prefiksu: {siec_prefix}...")
    wynik_arp_raw = pobierz_tabele_arp()
    if wynik_arp_raw is None:
        print("Nie udało się pobrać tabeli ARP.")
        return []

    mapa_arp = parsuj_tabele_arp(wynik_arp_raw, siec_prefix)

    # Klucze słownika mapa_arp to adresy IP
    lista_ip = list(mapa_arp.keys())

    # if lista_ip:
    #     print(f"Znaleziono {len(lista_ip)} adresów IP w tabeli ARP dla prefiksu {siec_prefix}.")
    # else:
    #     print(f"Nie znaleziono adresów IP w tabeli ARP dla prefiksu {siec_prefix}.")

    return lista_ip

def pobierz_mac_adres(ip_address: Optional[str]) -> Optional[str]:
    """
    Pobiera adres MAC dla podanego lokalnego adresu IP.
    Używa różnych metod w zależności od systemu operacyjnego.

    Args:
        ip_address: Lokalny adres IP interfejsu.

    Returns:
        Adres MAC w formacie XX:XX:XX:XX:XX:XX lub None.
    """
    if not ip_address:
        return None

    system = platform.system().lower()
    mac_address = None

    try:
        if system == "windows":
            # Metoda 1: Użycie getmac (szybsze i często bardziej niezawodne)
            try:
                # getmac /fo list /v
                cmd = ["getmac", "/fo", "list", "/v"]
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding=WINDOWS_OEM_ENCODING, errors='ignore', check=True, shell=False)
                output = proc.stdout

                current_mac: Optional[str] = None
                # Parsowanie wyjścia getmac
                for line in output.splitlines():
                    line = line.strip()
                    if "Physical Address" in line or "Adres fizyczny" in line:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            current_mac = parts[1].strip().replace("-", ":").upper()
                    # Sprawdź, czy nazwa transportowa zawiera szukany adres IP
                    elif ("Transport Name" in line or "Nazwa transportowa" in line) and ip_address in line:
                        if current_mac:
                            mac_address = current_mac
                            break # Znaleziono MAC dla właściwego interfejsu
                if mac_address: return mac_address

            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                print(f"Informacja: Polecenie 'getmac' nie powiodło się ({e}), próba z 'ipconfig /all'.")

            # Metoda 2: Fallback na ipconfig /all (wolniejsze, bardziej złożone parsowanie)
            try:
                cmd = ["ipconfig", "/all"]
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding=WINDOWS_OEM_ENCODING, errors='ignore', check=True, shell=False)
                output = proc.stdout

                adapter_section = None
                mac_in_section = None
                # Znajdź sekcję adaptera zawierającą podany adres IP
                current_section_lines = []
                for line in output.splitlines():
                    if line and not line.startswith(' '): # Początek nowej sekcji adaptera
                        # Sprawdź poprzednią sekcję
                        if ip_address in "".join(current_section_lines):
                            adapter_section = current_section_lines
                            break
                        current_section_lines = [line]
                    else:
                        current_section_lines.append(line)
                # Sprawdź ostatnią sekcję
                if not adapter_section and ip_address in "".join(current_section_lines):
                    adapter_section = current_section_lines

                # Jeśli znaleziono sekcję, wyszukaj w niej adres MAC
                if adapter_section:
                    for line in adapter_section:
                        if "Physical Address" in line or "Adres fizyczny" in line:
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                mac_in_section = parts[1].strip().replace("-", ":").upper()
                                break
                    if mac_in_section: return mac_in_section

            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                print(f"Błąd podczas pobierania adresu MAC (ipconfig): {e}")

        elif system == "linux":
            try:
                # Znajdź nazwę interfejsu dla danego IP
                cmd_addr = ["ip", "-4", "addr", "show"]
                proc_addr = subprocess.run(cmd_addr, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True, shell=False)
                interface_name = None
                for line in proc_addr.stdout.splitlines():
                    if f"inet {ip_address}/" in line:
                        # Linia np.: "    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic noprefixroute eth0"
                        interface_name = line.strip().split()[-1]
                        break

                if interface_name and interface_name != 'lo':
                    # Pobierz adres MAC dla znalezionego interfejsu
                    cmd_link = ["ip", "link", "show", interface_name]
                    proc_link = subprocess.run(cmd_link, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True, shell=False)
                    mac_match = re.search(r"link/ether\s+([0-9a-fA-F:]{17})", proc_link.stdout)
                    if mac_match:
                        return mac_match.group(1).upper()
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                print(f"Błąd podczas pobierania adresu MAC (ip addr/link): {e}")

        elif system == "darwin": # macOS
            try:
                # Użyj ifconfig, parsowanie może być bardziej złożone
                cmd = ["ifconfig"]
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True, shell=False)
                output = proc.stdout
                # Podziel wyjście na bloki dla każdego interfejsu
                interface_blocks = re.split(r'^\w', output, flags=re.MULTILINE)[1:] # Podział po nazwie interfejsu na początku linii
                correct_block = None
                for block in interface_blocks:
                    if f"inet {ip_address} " in block:
                        correct_block = block
                        break

                if correct_block:
                    mac_match = re.search(r"ether\s+([0-9a-fA-F:]{17})", correct_block)
                    if mac_match:
                        return mac_match.group(1).upper()
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                print(f"Błąd podczas pobierania adresu MAC (ifconfig): {e}")

        # Jeśli żadna metoda nie zadziałała
        print(f"Nie udało się znaleźć adresu MAC dla IP {ip_address} w systemie {system}.")
        return None

    except Exception as e:
        print(f"Nieoczekiwany błąd podczas pobierania adresu MAC: {e}")
        return None

def pokaz_arp_z_nazwami(
    siec_prefix: str,
    hosty_odpowiadajace: List[str],
    baza_oui: Dict[str, str],
    wyniki_portow: Dict[str, List[int]],
    hostname_cache: Dict[str, str] # <-- NOWY PARAMETR
) -> None:
    """
    Wyświetla listę urządzeń, używając przekazanych nazw hostów.
    (Reszta opisu bez zmian)
    Args:
        siec_prefix: Prefiks sieciowy.
        hosty_odpowiadajace: Lista IP, które odpowiedziały.
        baza_oui: Słownik OUI.
        wyniki_portow: Słownik otwartych portów.
        hostname_cache: Słownik z wcześniej pobranymi nazwami hostów {ip: nazwa}.
    """
    # print("\nOdczytywanie lokalnej tabeli ARP...") # Usunięto pobieranie nazw
    wynik_arp = pobierz_tabele_arp()
    arp_map: Dict[str, str] = {} # Zapewnij, że arp_map jest zawsze zdefiniowane
    if wynik_arp is None:
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można pobrać tabeli ARP. Adresy MAC mogą być niedostępne.{Style.RESET_ALL}")
    else:
        arp_map = parsuj_tabele_arp(wynik_arp, siec_prefix) # arp_map jest typu Dict[str, str]

    host_ip = pobierz_ip_interfejsu()
    host_mac = pobierz_mac_adres(host_ip) if host_ip else None
    gateway_ip = pobierz_brame_domyslna()

    # --- Przygotowanie listy IP do wyświetlenia (bez zmian) ---
    ips_do_wyswietlenia_set = set(hosty_odpowiadajace)
    if host_ip and host_ip.startswith(siec_prefix):
        ips_do_wyswietlenia_set.add(host_ip)
    if gateway_ip and gateway_ip.startswith(siec_prefix):
        ips_do_wyswietlenia_set.add(gateway_ip)

    final_ip_list = list(ips_do_wyswietlenia_set)
    try:
        final_ip_list.sort(key=lambda ip: list(map(int, ip.split('.'))))
    except ValueError:
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można posortować adresów IP. Sortowanie alfabetyczne.{Style.RESET_ALL}")
        final_ip_list.sort()

    # --- USUNIĘTO: Przyspieszenie pobierania nazw hostów ---
    # Teraz nazwy są przekazywane w hostname_cache

    # --- Wyświetlanie tabeli (logika bez zmian, ale używa hostname_cache) ---
    lp_width = len(str(len(final_ip_list))) + 1 if final_ip_list else 3
    host_port_width = 45
    total_width = DEFAULT_LINE_WIDTH
    separator_line = "-" * total_width

    print("\n")
    wyswietl_tekst_w_linii("-", total_width, "Znalezione urządzenia w sieci (Podstawowa Tabela)", Fore.LIGHTYELLOW_EX, Fore.LIGHTCYAN_EX)
    print(f"{Fore.LIGHTYELLOW_EX}{'Lp.':<{lp_width}} {'Adres IP':<16} {'Adres MAC':<20} {'Nazwa Hostu / Porty':<{host_port_width}} {'Producent (OUI)':<35}{Style.RESET_ALL}")
    print(separator_line)

    if not final_ip_list:
        print(f"{Fore.YELLOW}Nie znaleziono żadnych aktywnych urządzeń w zakresie lub nie udało się ich przetworzyć.{Style.RESET_ALL}")
    else:
        for idx, ip in enumerate(final_ip_list, start=1):
            # Pobierz MAC z mapy ARP lub użyj MAC hosta, jeśli to host lokalny
            mac = arp_map.get(ip) # Może być None
            if ip == host_ip and host_mac:
                mac = host_mac
            mac_display = mac if mac else "Nieznany MAC" # Użyj "Nieznany MAC", jeśli mac jest None

            # --- UŻYJ hostname_cache ---
            nazwa_hosta_raw = hostname_cache.get(ip, "Nieznana") # Pobierz z cache
            # --------------------------

            otwarte_porty_dla_ip = wyniki_portow.get(ip, [])
            porty_str = f" [{', '.join(map(str, otwarte_porty_dla_ip))}]" if otwarte_porty_dla_ip else ""
            nazwa_z_portami = f"{nazwa_hosta_raw}{porty_str}"

            producent_oui = pobierz_nazwe_producenta_oui(mac_display, baza_oui)
            is_local_host = (ip == host_ip)
            is_gateway = (ip == gateway_ip)
            oznaczenia = []
            if is_local_host: oznaczenia.append("(Ty)")
            if is_gateway: oznaczenia.append("(Brama)")
            oznaczenie_str = " ".join(oznaczenia)

            nazwa_finalna = nazwa_z_portami
            if oznaczenie_str:
                if nazwa_hosta_raw in ["Nieznana", "Błąd"] and not porty_str:
                    nazwa_finalna = f"{ip} {oznaczenie_str}"
                else:
                    nazwa_finalna = f"{nazwa_z_portami} {oznaczenie_str}"

            # line_format = f"{str(idx):<{lp_width}} {ip:<16} {mac:<20} {nazwa_finalna:<{host_port_width}.{host_port_width}} {producent_oui:<35.35}"
            line_format = f"{str(idx):<{lp_width}} {ip:<16} {mac_display:<20} {nazwa_finalna:<{host_port_width}.{host_port_width}} {producent_oui:<35.35}" # Użyj mac_display
            # Logika kolorowania bez zmian
            if nazwa_hosta_raw != "Nieznana" and nazwa_hosta_raw != "Błąd":
                print(f"{Fore.CYAN}{line_format}{Style.RESET_ALL}")
            elif producent_oui != "Nieznany":
                print(f"{Fore.GREEN}{line_format}{Style.RESET_ALL}")
            elif nazwa_hosta_raw == "Błąd":
                 print(f"{Fore.RED}{line_format}{Style.RESET_ALL}")
            else:
                print(line_format)

    print(separator_line)


# Zmodyfikowana funkcja wyswietl_rozszerzona_tabele_urzadzen
def wyswietl_rozszerzona_tabele_urzadzen(
    siec_prefix: str,
    hosty_odpowiadajace: List[str],
    baza_oui: Dict[str, str],
    wyniki_portow: Dict[str, List[int]],
    hostname_cache: Dict[str, str], # <-- NOWY PARAMETR
    kolumny_do_wyswietlenia: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA
) -> Dict[str, str]:
    """
    Wyświetla rozszerzoną listę urządzeń, używając przekazanych nazw hostów.
    (Reszta opisu bez zmian)
    Args:
        siec_prefix: Prefiks sieciowy.
        hosty_odpowiadajace: Lista IP, które odpowiedziały.
        baza_oui: Słownik OUI.
        wyniki_portow: Słownik otwartych portów.
        hostname_cache: Słownik z wcześniej pobranymi nazwami hostów {ip: nazwa}.
        kolumny_do_wyswietlenia: Lista kluczy kolumn do wyświetlenia.
    """
    # print("\nOdczytywanie lokalnej tabeli ARP i zgadywanie systemów...") # Zmieniono opis
    wynik_arp = pobierz_tabele_arp()
    arp_map: Dict[str, str] = {}
    if wynik_arp is None:
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można pobrać tabeli ARP. Adresy MAC mogą być niedostępne.{Style.RESET_ALL}")
    else:
        arp_map = parsuj_tabele_arp(wynik_arp, siec_prefix)

    host_ip = pobierz_ip_interfejsu()
    host_mac = pobierz_mac_adres(host_ip) if host_ip else None
    gateway_ip = pobierz_brame_domyslna()

    # --- Przygotowanie listy IP do wyświetlenia (bez zmian) ---
    # ips_do_wyswietlenia_set = set(hosty_odpowiadajace)
    ping_ips_set = set(hosty_odpowiadajace)
    arp_ips_set = {ip for ip in arp_map.keys() if ip.startswith(siec_prefix)}
    ips_do_wyswietlenia_set = ping_ips_set.union(arp_ips_set)

    if host_ip and host_ip.startswith(siec_prefix):
        ips_do_wyswietlenia_set.add(host_ip)
    if gateway_ip and gateway_ip.startswith(siec_prefix):
        ips_do_wyswietlenia_set.add(gateway_ip)

    final_ip_list = list(ips_do_wyswietlenia_set)
    try:
        final_ip_list.sort(key=lambda ip: list(map(int, ip.split('.'))))
    except ValueError:
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można posortować adresów IP. Sortowanie alfabetyczne.{Style.RESET_ALL}")
        final_ip_list.sort()
    arp_only_ips = arp_ips_set - ping_ips_set
    # --- ZMODYFIKOWANO: Przyspieszenie ZGADYWANIA OS (nazwy już mamy) ---
    os_cache: Dict[str, str] = {}
    total_tasks = len(final_ip_list) # Teraz tylko zgadywanie OS
    completed_tasks = 0

    if final_ip_list:
        print(f"Identyfikacja możliwych systemów operacyjnych dla wykrytych hostów. {total_tasks} adresów (max {MAX_HOSTNAME_WORKERS} wątków)...")
        try:
            # Upewnij się, że nie tworzymy więcej wątków niż zadań
            actual_workers = min(MAX_HOSTNAME_WORKERS, total_tasks)
            if actual_workers <= 0: actual_workers = 1 # Minimum 1 worker

            with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
                # TYLKO zadania zgadywania systemu
                future_to_ip_os = {
                    executor.submit(zgadnij_system_operacyjny, ip, otwarte_porty_znane=wyniki_portow.get(ip, [])): ip
                    for ip in final_ip_list
                }
                # Usunięto future_to_ip_host
                all_futures = future_to_ip_os # Teraz tylko OS futures

                for future in concurrent.futures.as_completed(all_futures):
                    ip = all_futures[future]
                    try:
                        result = future.result()
                        # Usunięto sprawdzanie 'if future in future_to_ip_host'
                        os_cache[ip] = result # Zapisz wynik OS
                    except Exception as exc:
                        # Usunięto task_type
                        print(f'\n{Fore.YELLOW}Wątek zgadywania OS dla {ip} zgłosił wyjątek: {exc}{Style.RESET_ALL}')
                        # Usunięto hostname_cache[ip] = "Błąd"
                        os_cache[ip] = "Błąd OS" # Oznacz błąd OS
                    completed_tasks += 1
                    # Zaktualizowano tekst postępu
                    print(f"\rPostęp zgadywania OS: {completed_tasks}/{total_tasks} zadań ukończonych...", end="")
        except KeyboardInterrupt:
            obsluz_przerwanie_uzytkownika()
        finally:
            print("\r" + " " * 70 + "\r", end="")
    else:
        print("Brak adresów IP do sprawdzenia.")
    # ------------------------------------------------------------------

    # --- Wyświetlanie tabeli (logika bez zmian, ale używa hostname_cache) ---
    aktywne_kolumny = {k: v for k, v in KOLUMNY_TABELI.items() if k in kolumny_do_wyswietlenia}
    total_width = sum(col["szerokosc"] for col in aktywne_kolumny.values()) + len(aktywne_kolumny) - 1
    separator_line = "-" * total_width

    print("\n")
    wyswietl_tekst_w_linii("-", total_width, "Podsumowanie skanowania urządzeń w sieci", Fore.LIGHTGREEN_EX, Fore.LIGHTCYAN_EX)

    header_parts = []
    for col_key in kolumny_do_wyswietlenia:
        if col_key in aktywne_kolumny:
            col_config = aktywne_kolumny[col_key]
            header_parts.append(f"{col_config['naglowek']:<{col_config['szerokosc']}}")
    print(f"{Fore.LIGHTYELLOW_EX}{' '.join(header_parts)}{Style.RESET_ALL}")
    print(separator_line)

    if not final_ip_list:
        print(f"{Fore.YELLOW}Nie znaleziono żadnych aktywnych urządzeń w zakresie lub nie udało się ich przetworzyć.{Style.RESET_ALL}")
    else:
        for idx, ip in enumerate(final_ip_list, start=1):
            mac = arp_map.get(ip)
            if ip == host_ip and host_mac: mac = host_mac
            mac_display = mac if mac else "Nieznany MAC"

            # --- UŻYJ hostname_cache ---
            nazwa_hosta_raw = hostname_cache.get(ip, "Nieznana") # Pobierz z cache
            # --------------------------
            zgadniety_os = os_cache.get(ip, "Nieznany OS") # Pobierz z cache OS

            otwarte_porty_dla_ip = wyniki_portow.get(ip, [])
            porty_str = ', '.join(map(str, otwarte_porty_dla_ip)) if otwarte_porty_dla_ip else ""

            producent_oui = pobierz_nazwe_producenta_oui(mac_display, baza_oui)
            is_local_host = (ip == host_ip)
            is_gateway = (ip == gateway_ip)
            oznaczenia = []
            if is_local_host: oznaczenia.append("(Ty)")
            if is_gateway: oznaczenia.append("(Brama)")
            oznaczenie_str = " ".join(oznaczenia)
            # (Opcjonalnie) Dodaj oznaczenie dla hostów tylko z ARP
            if ip in arp_only_ips:
                oznaczenia.append("(ARP Only)")
            oznaczenie_str = " ".join(oznaczenia)

            nazwa_finalna = nazwa_hosta_raw
            if oznaczenie_str:
                if nazwa_hosta_raw in ["Nieznana", "Błąd"]:
                    nazwa_finalna = f"{ip} {oznaczenie_str}"
                else:
                    nazwa_finalna = f"{nazwa_hosta_raw} {oznaczenie_str}"

            row_data = {
                "lp": str(idx),
                "ip": ip,
                "mac": mac_display,
                "host": nazwa_finalna,
                "porty": porty_str,
                "os": zgadniety_os,
                "oui": producent_oui
            }

            line_parts = []
            for col_key in kolumny_do_wyswietlenia:
                if col_key in aktywne_kolumny:
                    col_config = aktywne_kolumny[col_key]
                    data = row_data.get(col_key, "")
                    formatted_data = f"{data:<{col_config['szerokosc']}.{col_config['szerokosc']}}"
                    line_parts.append(formatted_data)

            line_format = ' '.join(line_parts)
            # (Opcjonalnie) Zmodyfikuj logikę kolorowania dla hostów tylko z ARP
            if ip in arp_only_ips:
                print(f"{Fore.MAGENTA}{line_format}{Style.RESET_ALL}") # Np. na fioletowo
            else:
                # Logika kolorowania bez zmian
                if nazwa_hosta_raw != "Nieznana" and nazwa_hosta_raw != "Błąd":
                    print(f"{Fore.CYAN}{line_format}{Style.RESET_ALL}")
                elif producent_oui != "Nieznany":
                    print(f"{Fore.GREEN}{line_format}{Style.RESET_ALL}")
                elif nazwa_hosta_raw == "Błąd" or zgadniety_os == "Błąd OS":
                    print(f"{Fore.RED}{line_format}{Style.RESET_ALL}")
                else:
                    print(line_format)

    print(separator_line)
    return os_cache



def pobierz_prefiks_sieciowy() -> Optional[str]:
    """
    Pobiera prefiks sieciowy (pierwsze 3 oktety) aktywnego interfejsu.

    Returns:
        Prefiks sieciowy (np. "192.168.0.") lub None w przypadku błędu.
    """
    ip_address = pobierz_ip_interfejsu() # Użyj tej samej metody co do pobrania IP hosta

    if ip_address:
        parts = ip_address.split(".")
        if len(parts) == 4: # Upewnij się, że to poprawny adres IPv4
            # Zakładamy maskę /24 dla prostoty, zwracamy np. "192.168.0."
            return ".".join(parts[:3]) + "."
        else:
            print(f"Nieoczekiwany format adresu IP: {ip_address}")
            return None
    else:
        print("Nie można automatycznie wykryć adresu IP interfejsu.")
        return None

def odczytaj_baze_oui_z_pliku(plik_lokalny):
    """Odczytuje bazę OUI z pliku lokalnego."""
    baza_oui = {}
    try:
        with open(plik_lokalny, "r", encoding="utf-8") as f:
            baza_oui_txt = f.read()
        print("Odczytano bazę OUI z pliku lokalnego.")
        return pobierz_baze_z_tekstu(baza_oui_txt)
    except Exception as e:
        print(f"Błąd podczas odczytu pliku lokalnego: {e}")
        return {}

def pobierz_baze_oui(url: str = OUI_URL, plik_lokalny: str = OUI_LOCAL_FILE,
                     timeout: int = REQUESTS_TIMEOUT, aktualizacja_co: int = OUI_UPDATE_INTERVAL) -> Dict[str, str]:
    """
    Pobiera bazę OUI z URL lub odczytuje z pliku lokalnego, jeśli jest aktualny.
    Jeśli 'requests' nie jest zainstalowane, próbuje tylko odczytać plik lokalny.
    """
    baza_oui: Dict[str, str] = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plik_lokalny_path = os.path.join(script_dir, plik_lokalny)

    plik_aktualny = False
    if os.path.exists(plik_lokalny_path):
        try:
            czas_modyfikacji = os.path.getmtime(plik_lokalny_path)
            if time.time() - czas_modyfikacji < aktualizacja_co:
                print("Lokalna baza OUI jest aktualna.")
                plik_aktualny = True
            else:
                 # Wyświetl komunikat o aktualizacji tylko jeśli requests jest dostępne
                 if REQUESTS_AVAILABLE:
                     print("Lokalna baza OUI jest przestarzała, próba aktualizacji...")
                 else:
                     print("Lokalna baza OUI jest przestarzała, ale 'requests' nie jest zainstalowane. Używam starej wersji.")
                     plik_aktualny = True # Traktuj jako aktualny, jeśli nie można pobrać nowej
        except Exception as e:
             print(f"{Fore.YELLOW}Błąd podczas sprawdzania wieku pliku OUI: {e}{Style.RESET_ALL}")

    if plik_aktualny:
        baza_oui = odczytaj_baze_oui_z_pliku(plik_lokalny_path)
        if baza_oui:
            return baza_oui
        else:
             # Próbuj pobrać z sieci tylko jeśli plik jest nieaktualny/uszkodzony I requests jest dostępne
             if REQUESTS_AVAILABLE:
                 print("Nie udało się odczytać aktualnego pliku OUI, próba pobrania z sieci.")
             else:
                 print(f"{Fore.YELLOW}Nie udało się odczytać pliku OUI. Pobieranie z sieci niemożliwe (brak 'requests').{Style.RESET_ALL}")
                 return {} # Zwróć pusty słownik, jeśli odczyt pliku zawiódł i sieć jest niemożliwa

    # --- Sekcja pobierania z sieci ---
    # Sprawdź jawnie, czy requests jest dostępne przed próbą użycia
    if not REQUESTS_AVAILABLE:
        print(f"{Fore.YELLOW}Biblioteka 'requests' nie jest zainstalowana. Nie można pobrać bazy OUI z sieci.{Style.RESET_ALL}")
        # Spróbuj odczytać plik lokalny ostatni raz (nawet jeśli przestarzały)
        print("Próba użycia ostatniej znanej wersji bazy OUI z pliku lokalnego...")
        return odczytaj_baze_oui_z_pliku(plik_lokalny_path)

    # Jeśli requests JEST dostępne, kontynuuj pobieranie z sieci
    print(f"Pobieranie bazy OUI z {url}...")
    try:
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)

        # --- DODAJ NAGŁÓWEK USER-AGENT TUTAJ ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # Użyj nagłówka w żądaniu GET
        response = http.get(url, timeout=timeout, headers=headers) # <-- Dodano headers=headers
        response.raise_for_status()
        baza_oui_txt = response.text
        print("Pobrano bazę OUI z sieci.")

        # Zapisz pobraną bazę do pliku
        try:
            with open(plik_lokalny_path, "w", encoding="utf-8") as f:
                f.write(baza_oui_txt)
            print(f"Zapisano bazę OUI do pliku lokalnego: {plik_lokalny_path}")
        except Exception as e:
            print(f"{Fore.RED}Błąd podczas zapisu do pliku lokalnego OUI ({plik_lokalny_path}): {e}{Style.RESET_ALL}")

        # Sparsuj pobrany tekst
        baza_oui = pobierz_baze_z_tekstu(baza_oui_txt)
        return baza_oui

    except requests.exceptions.RequestException as e:
        # Zaktualizuj obsługę błędu, aby pokazać kod statusu, jeśli jest dostępny
        error_message = f"Błąd podczas pobierania bazy OUI z sieci: {e}"
        if e.response is not None:
             error_message += f" (Status Code: {e.response.status_code})"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        print("Sprawdź połączenie internetowe i czy URL jest nadal poprawny.")
        print("Próba użycia ostatniej znanej wersji bazy OUI z pliku lokalnego...")
        return odczytaj_baze_oui_z_pliku(plik_lokalny_path) # Zwróci pusty dict, jeśli plik nie istnieje/nie da się odczytać
    except Exception as e:
        print(f"{Fore.RED}Inny błąd podczas przetwarzania bazy OUI: {e}{Style.RESET_ALL}")
        return odczytaj_baze_oui_z_pliku(plik_lokalny_path) # Zapasowo spróbuj plik



def pobierz_baze_z_tekstu(baza_oui_txt):
    """Parsuje tekst bazy OUI i zwraca słownik."""
    baza_oui = {}
    for linia in baza_oui_txt.splitlines():
        # Pomijaj puste linie i komentarze
        if not linia.strip() or linia.startswith("#"):
            continue
        # Dopasuj OUI (3 pary szesnastkowe oddzielone myślnikami) i nazwę organizacji
        match = re.search(r"([0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2})\s+(.+)", linia)
        if match:
            oui, organizacja = match.groups()
            baza_oui[oui.upper()] = organizacja.strip()
    return baza_oui

# Wymaga zainstalowanego psutil

def pobierz_ip_przez_psutil() -> Optional[str]:
    if not PSUTIL_AVAILABLE: # Użyj flagi zdefiniowanej na początku skryptu
         print("Psutil niedostępny, nie można użyć tej metody.")
         return None
    try:
        interfaces = psutil.net_if_addrs()
        for if_name, snic_list in interfaces.items():
            # Pomiń loopback i potencjalnie inne niechciane interfejsy
            if if_name.lower().startswith('lo') or 'loopback' in if_name.lower():
                continue
            for snic in snic_list:
                # Szukaj adresu IPv4, który nie jest link-local (169.254...)
                if snic.family == socket.AF_INET:
                    try:
                        ip_addr = ipaddress.ip_address(snic.address)
                        if not ip_addr.is_loopback and not ip_addr.is_link_local:
                            # Zwróć pierwszy znaleziony "dobry" adres IPv4
                            # UWAGA: To nadal może nie być adres domyślnej trasy!
                            return snic.address
                    except ValueError:
                        continue # Ignoruj niepoprawne adresy
        return None # Nie znaleziono odpowiedniego adresu
    except Exception as e:
        print(f"Błąd podczas pobierania IP przez psutil: {e}")
        return None

# Przykład użycia:
# lokalny_ip_psutil = pobierz_ip_przez_psutil()
# print(f"IP przez psutil: {lokalny_ip_psutil}")


def pobierz_ip_interfejsu() -> Optional[str]: # Dodano type hint dla przejrzystości
    """Pobiera adres IP interfejsu używanego do połączeń wychodzących."""
    try:
        # Tworzenie tymczasowego gniazda do połączenia z zewnętrznym serwerem
        # Nie wysyła danych, tylko inicjuje połączenie, by system wybrał interfejs
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1) # Krótki timeout na połączenie
            # Użycie adresu IP zamiast nazwy domenowej, aby uniknąć zależności od DNS
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        # Wyklucz adresy loopback i APIPA
        if ip_address != "127.0.0.1" and not ip_address.startswith("169.254."):
            return ip_address
        else:
            # Jeśli uzyskany adres to loopback/APIPA, spróbuj innej metody (jeśli dostępna)
            # lub zwróć None, bo ta metoda nie dała użytecznego adresu.
            # W tym przypadku zwracamy None.
            print("Ostrzeżenie: Metoda socket.connect zwróciła adres lokalny/APIPA.")
            return None
    except socket.timeout:
        print("Błąd timeout podczas próby połączenia z 8.8.8.8 (sprawdzanie IP).")
        return None
    except OSError as e: # Np. Network is unreachable
        print(f"Błąd sieci podczas pobierania IP interfejsu: {e}")
        return None
    except Exception as e:
        print(f"Nieoczekiwany błąd podczas pobierania IP interfejsu: {e}")
        return None


def pobierz_baze_z_tekstu(baza_oui_txt: str) -> Dict[str, str]:
    """Parsuje tekst bazy OUI i zwraca słownik."""
    baza_oui: Dict[str, str] = {}
    oui_pattern = re.compile(r"^([0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2})\s+\((?:hex|base 16)\)\s+(.+)$", re.IGNORECASE)

    for linia in baza_oui_txt.splitlines():
        linia = linia.strip() # Usuń białe znaki z początku/końca
        if not linia or linia.startswith("#"): # Ignoruj puste linie i komentarze
            continue

        match = oui_pattern.match(linia)
        if match:
            oui, organizacja = match.groups()
            # Klucz to OUI (XX-XX-XX), wartość to nazwa organizacji
            baza_oui[oui.upper()] = organizacja.strip()
        # else: # Opcjonalnie: pokaż linie, które nie pasują do wzorca (do debugowania)
            # print(f"Linia OUI nie pasuje do wzorca: {linia}")

    if not baza_oui:
        print("Ostrzeżenie: Nie udało się sparsować żadnych wpisów OUI z pobranego tekstu.")
    return baza_oui

def pobierz_i_zweryfikuj_prefiks() -> Optional[str]:
    """
    Pobiera prefiks sieciowy. Jeśli zostanie wykryty automatycznie,
    prosi użytkownika o potwierdzenie lub podanie innego.
    W przeciwnym razie prosi o ręczne wprowadzenie.
    Czyści linię promptu po poprawnym wyborze.
    """
    siec_prefix_automatyczny = pobierz_prefiks_sieciowy()
    potwierdzony_prefiks: Optional[str] = None

    if siec_prefix_automatyczny:
        # Automatyczne wykrywanie powiodło się - zapytaj użytkownika
        print(f"Wykryty prefiks sieciowy: '{siec_prefix_automatyczny}'.")
        while potwierdzony_prefiks is None: # Pytaj dopóki nie uzyskasz poprawnego prefiksu
            try:
                prompt_text = f"Potwierdź {Fore.LIGHTMAGENTA_EX}[Enter]{Style.RESET_ALL}, podaj inny prefiks lub {Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL} aby zakończyć: "
                odpowiedz = input(prompt_text)

                if not odpowiedz.strip(): # Użytkownik nacisnął Enter
                    potwierdzony_prefiks = siec_prefix_automatyczny
                    # --- CZYSZCZENIE LINII PROMPTU ---
                    sys.stdout.write("\033[A\033[K") # Przesuń kursor w górę, wyczyść linię
                    sys.stdout.flush()
                    # --- KONIEC CZYSZCZENIA ---
                    print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                else: # Użytkownik podał inny prefiks
                    nowy_prefiks = odpowiedz.strip()
                    if not nowy_prefiks.endswith("."):
                        nowy_prefiks += "."
                    # Prosta walidacja formatu XXX.YYY.ZZZ.
                    if re.match(r"^(\d{1,3}\.){3}$", nowy_prefiks):
                         parts = nowy_prefiks.split('.')[:-1]
                         try:
                             if all(0 <= int(p) <= 255 for p in parts):
                                 potwierdzony_prefiks = nowy_prefiks
                                 # --- CZYSZCZENIE LINII PROMPTU ---
                                 sys.stdout.write("\033[A\033[K") # Przesuń kursor w górę, wyczyść linię
                                 sys.stdout.flush()
                                 # --- KONIEC CZYSZCZENIA ---
                                 print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                             else:
                                 # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                                 sys.stdout.write("\033[A\033[K")
                                 sys.stdout.flush()
                                 # --- KONIEC CZYSZCZENIA ---
                                 print(f"{Fore.YELLOW}Ostrzeżenie: Jeden z oktetów w podanym prefiksie jest poza zakresem 0-255. Spróbuj ponownie.{Style.RESET_ALL}")
                                 # Pętla while będzie kontynuowana
                         except ValueError:
                              # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                              sys.stdout.write("\033[A\033[K")
                              sys.stdout.flush()
                              # --- KONIEC CZYSZCZENIA ---
                              print(f"{Fore.YELLOW}Ostrzeżenie: Podany prefiks zawiera nie-liczbowe części. Spróbuj ponownie.{Style.RESET_ALL}")
                              # Pętla while będzie kontynuowana
                    else:
                        # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                        sys.stdout.write("\033[A\033[K")
                        sys.stdout.flush()
                        # --- KONIEC CZYSZCZENIA ---
                        print(f"{Fore.YELLOW}Niepoprawny format podanego prefiksu (oczekiwano np. 192.168.1.). Spróbuj ponownie.{Style.RESET_ALL}")
                        # Pętla while będzie kontynuowana

            except EOFError:
                # Wyczyść linię promptu jeśli wystąpił EOF
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                print("\nNie można pobrać odpowiedzi (EOF). Używam automatycznie wykrytego prefiksu.")
                potwierdzony_prefiks = siec_prefix_automatyczny # Akceptuj automatyczny w razie EOF
                break # Wyjdź z pętli while
            except KeyboardInterrupt:
                obsluz_przerwanie_uzytkownika() # Ta funkcja obsługuje wyjście
            except Exception as e:
                 # Wyczyść linię promptu
                 sys.stdout.write("\r\033[K")
                 sys.stdout.flush()
                 print(f"\n{Fore.RED}Błąd podczas pobierania odpowiedzi: {e}{Style.RESET_ALL}")
                 print(f"Używam automatycznie wykrytego prefiksu: {siec_prefix_automatyczny}")
                 potwierdzony_prefiks = siec_prefix_automatyczny # Akceptuj automatyczny w razie błędu
                 break # Wyjdź z pętli while

    else:
        # Automatyczne wykrywanie nie powiodło się - przejdź do ręcznego wprowadzania
        print(f"{Fore.YELLOW}Nie udało się automatycznie wykryć prefiksu sieciowego.{Style.RESET_ALL}")
        while potwierdzony_prefiks is None:
            try:
                prompt_text = f"Podaj prefiks sieciowy (np. 192.168.1.) lub {Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL} aby zakończyć: "
                odpowiedz = input(prompt_text)

                if not odpowiedz.strip():
                    # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                    sys.stdout.write("\033[A\033[K")
                    sys.stdout.flush()
                    # --- KONIEC CZYSZCZENIA ---
                    print(f"{Fore.YELLOW}Prefiks nie może być pusty. Spróbuj ponownie.{Style.RESET_ALL}")
                    continue # Wróć do początku pętli while

                nowy_prefiks = odpowiedz.strip()
                if not nowy_prefiks.endswith("."):
                    nowy_prefiks += "."

                if re.match(r"^(\d{1,3}\.){3}$", nowy_prefiks):
                    parts = nowy_prefiks.split('.')[:-1]
                    try:
                        if all(0 <= int(p) <= 255 for p in parts):
                            potwierdzony_prefiks = nowy_prefiks
                            # --- CZYSZCZENIE LINII PROMPTU ---
                            sys.stdout.write("\033[A\033[K") # Przesuń kursor w górę, wyczyść linię
                            sys.stdout.flush()
                            # --- KONIEC CZYSZCZENIA ---
                            print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                        else:
                            # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                            sys.stdout.write("\033[A\033[K")
                            sys.stdout.flush()
                            # --- KONIEC CZYSZCZENIA ---
                            print(f"{Fore.YELLOW}Ostrzeżenie: Jeden z oktetów w podanym prefiksie jest poza zakresem 0-255. Spróbuj ponownie.{Style.RESET_ALL}")
                    except ValueError:
                         # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                         sys.stdout.write("\033[A\033[K")
                         sys.stdout.flush()
                         # --- KONIEC CZYSZCZENIA ---
                         print(f"{Fore.YELLOW}Ostrzeżenie: Podany prefiks zawiera nie-liczbowe części. Spróbuj ponownie.{Style.RESET_ALL}")
                else:
                    # --- CZYSZCZENIE LINII PROMPTU PRZED BŁĘDEM ---
                    sys.stdout.write("\033[A\033[K")
                    sys.stdout.flush()
                    # --- KONIEC CZYSZCZENIA ---
                    print(f"{Fore.YELLOW}Niepoprawny format prefiksu (oczekiwano np. 192.168.1.). Spróbuj ponownie.{Style.RESET_ALL}")

            except EOFError:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                print("\nNie można pobrać prefiksu od użytkownika (EOF). Przerywam.")
                return None # Zwróć None, aby główna część mogła zareagować
            except KeyboardInterrupt:
                obsluz_przerwanie_uzytkownika()
            except Exception as e:
                 sys.stdout.write("\r\033[K")
                 sys.stdout.flush()
                 print(f"\n{Fore.RED}Błąd podczas pobierania odpowiedzi: {e}{Style.RESET_ALL}")
                 return None # Zwróć None w razie błędu

    return potwierdzony_prefiks

# --- Główna część skryptu ---
if __name__ == "__main__":
    # try:
        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"Skaner Sieci Lokalnej",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)


        wszystkie_ip, glowny_ip = pobierz_wszystkie_aktywne_ip()
        # Sprawdź obecność VPN lub inne i wyświetl ostrzeżenie tylko jeśli psutil jest dostępny
        if PSUTIL_AVAILABLE:
            # Użyj nowej nazwy funkcji
            if czy_aktywny_vpn_lub_podobny():
                wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"OSTRZEŻENIE: Wykryto aktywny interfejs VPN lub podobny (np. Tailscale).",Fore.LIGHTYELLOW_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"Może to zakłócać rozpoznawanie nazw hostów w Twojej sieci lokalnej (LAN).",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"Jeśli nazwy hostów lokalnych nie są wyświetlane poprawnie (pokazuje 'Nieznana'), spróbuj:",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"1. Skonfigurować VPN, aby używał lokalnych serwerów DNS (jeśli to możliwe, np. Split DNS).",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"2. Tymczasowo wyłączyć VPN na czas działania skryptu.",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)

        # ... (kod sprawdzający VPN i wyświetlający IP/MAC hosta) ...
        host_ip = glowny_ip #pobierz_ip_interfejsu()
        host_mac = pobierz_mac_adres(host_ip) #if host_ip else "Nieznany"
        print(f"Adres IP komputera: {host_ip if host_ip else 'Nieznany'}")
        print(f"Adres MAC komputera: {host_mac if host_mac else 'Nieznany'}")

        # Pobierz i zweryfikuj prefiks sieciowy używając nowej funkcji
        siec_prefix = pobierz_i_zweryfikuj_prefiks()
        kolumny_wybrane_przez_uzytkownika = wybierz_kolumny_do_wyswietlenia()
        # Sprawdź, czy udało się uzyskać prefiks
        if siec_prefix is None:
            print(f"{Fore.RED}Nie udało się ustalić prefiksu sieciowego. Zakończono.{Style.RESET_ALL}")
            sys.exit(1) # Zakończ skrypt, jeśli prefiks nie został ustalony

        # Pobierz bazę OUI (użyj poprawionej funkcji z cache)
        print("\nPobieranie/ładowanie bazy OUI...")
        baza_oui = pobierz_baze_oui(url=OUI_URL, plik_lokalny=OUI_LOCAL_FILE, timeout=REQUESTS_TIMEOUT, aktualizacja_co=OUI_UPDATE_INTERVAL)
        if not baza_oui:
            print(f"{Fore.YELLOW}OSTRZEŻENIE: Nie udało się załadować bazy OUI. Nazwy producentów nie będą dostępne.{Style.RESET_ALL}")
            baza_oui = {} # Użyj pustego słownika

        # Skanowanie sieci
        print("\nRozpoczynanie skanowania sieci (ping)...")
        start_arp_time = time.time() # Przesunięto start timera tutaj
        
        hosty_ktore_odpowiedzialy = pinguj_zakres(siec_prefix, DEFAULT_START_IP, DEFAULT_END_IP)
        adresy_ip_z_arp = pobierz_ip_z_arp(siec_prefix)
        polaczona_lista_ip = polacz_listy_ip(adresy_ip_z_arp, hosty_ktore_odpowiedzialy)

        # --- SKANOWANIE PORTÓW (NOWY KROK) ---
        wyniki_skanowania_portow: Dict[str, List[int]] = {}
        if polaczona_lista_ip: # Skanuj porty tylko jeśli są hosty
            print("\nSkanowania wybranych portów dla aktywnych hostów...")
            # start_scan_time = time.time()
            # Użyjemy puli wątków do równoległego skanowania RÓŻNYCH hostów
            MAX_HOST_SCAN_WORKERS = MAX_HOSTNAME_WORKERS # Możesz ustawić inną wartość

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_HOST_SCAN_WORKERS) as host_executor:
                    # Użyj funkcji skanuj_wybrane_porty_dla_ip, która sama używa wątków do portów
                    future_to_ip_scan = {host_executor.submit(skanuj_wybrane_porty_dla_ip, ip): ip for ip in polaczona_lista_ip}

                    processed_hosts = 0
                    total_hosts_to_scan = len(polaczona_lista_ip)

                    for future in concurrent.futures.as_completed(future_to_ip_scan):
                        ip_skanowany = future_to_ip_scan[future]
                        try:
                            lista_otwartych = future.result()
                            wyniki_skanowania_portow[ip_skanowany] = lista_otwartych
                        except Exception as exc:
                            print(f'\n{Fore.YELLOW}Skanowanie portów dla {ip_skanowany} zgłosił wyjątek: {exc}{Style.RESET_ALL}')
                            wyniki_skanowania_portow[ip_skanowany] = [] # Zapisz pustą listę w razie błędu

                        processed_hosts += 1
                        print(f"\rPostęp skanowania portów: {processed_hosts}/{total_hosts_to_scan} hostów sprawdzonych...", end="")

            except KeyboardInterrupt:
                obsluz_przerwanie_uzytkownika()
            finally:
                print("\r" + " " * 70 + "\r", end="") # Wyczyść linię postępu
        else:
            print("\nBrak aktywnych hostów do skanowania portów.")
        # --- KONIEC SKANOWANIA PORTÓW ---

        host_ip = pobierz_ip_interfejsu()
        gateway_ip = pobierz_brame_domyslna()
        ips_do_przetworzenia_set = set(polaczona_lista_ip)
        if host_ip and host_ip.startswith(siec_prefix):
            ips_do_przetworzenia_set.add(host_ip)
        if gateway_ip and gateway_ip.startswith(siec_prefix):
            ips_do_przetworzenia_set.add(gateway_ip)
        final_ip_list_do_przetworzenia = list(ips_do_przetworzenia_set)
        try:
            final_ip_list_do_przetworzenia.sort(key=lambda ip: list(map(int, ip.split('.'))))
        except ValueError:
            final_ip_list_do_przetworzenia.sort()
        # ---------------------------------------------------------

        # --- NOWOŚĆ: Pobierz nazwy hostów RAZ ---
        nazwy_hostow_cache = pobierz_nazwy_hostow_rownolegle(final_ip_list_do_przetworzenia)
        # ---------------------------------------

        # Wyświetlanie wyników - przekaż cache nazw hostów
        # Możesz usunąć wywołanie pokaz_arp_z_nazwami, jeśli używasz tylko rozszerzonej tabeli
        # pokaz_arp_z_nazwami(
        #     siec_prefix,
        #     hosty_ktore_odpowiedzialy, # Lub final_ip_list_do_przetworzenia? Zależy co chcesz pokazać
        #     baza_oui,
        #     wyniki_skanowania_portow,
        #     nazwy_hostow_cache # <-- Przekaż cache
        # )

        # kolumny_wybrane_przez_uzytkownika = wybierz_kolumny_do_wyswietlenia()
        os_cache_wyniki = wyswietl_rozszerzona_tabele_urzadzen(
            siec_prefix,
            polaczona_lista_ip, # Lub final_ip_list_do_przetworzenia?
            baza_oui,
            wyniki_skanowania_portow,
            nazwy_hostow_cache, # <-- Przekaż cache nazw
            kolumny_wybrane_przez_uzytkownika
            # kolumny_do_wyswietlenia=... # Opcjonalnie
        )
        end_arp_time = time.time() # Koniec timera
        # Wyświetl czas wykonania pod tabelą
        czas_trwania_sekundy = end_arp_time - start_arp_time
        print(f"\nCałkowity czas skanowania (ping + ARP + nazwy + porty): {czas_trwania_sekundy:.2f} sekund. Czyli {przelicz_sekundy_na_minuty_sekundy(round(czas_trwania_sekundy))} min:sek")

        # --- WYŚWIETL LEGENDĘ PORTÓW (NOWY KROK) ---
        wyswietl_legende_portow(wyniki_skanowania_portow)
        # --- KONIEC WYŚWIETLANIA LEGENDY ---
        wyswietl_legende_systemow(os_cache_wyniki) # Przekaż wyniki zgadywania OS

        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"Skanowanie zakończone. Przewiń wyżej, aby zobaczyć wyniki.",Fore.LIGHTCYAN_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)

    # except Exception as main_exc:
    #      print(f"\n{Fore.RED}Wystąpił nieoczekiwany błąd w głównej części skryptu: {main_exc}{Style.RESET_ALL}")
    #      # Możesz dodać tutaj bardziej szczegółowe logowanie błędu
    # finally:
    #     # UWAGA: Użycie os._exit jest ostatecznością. Może powodować problemy
    #     # z niezapisanymi danymi lub nieposprzątanymi zasobami.
    #     # print("Zakończenie skryptu...") # Opcjonalny komunikat debugowania
        sys.exit(0) # Użyj standardowego wyjścia
