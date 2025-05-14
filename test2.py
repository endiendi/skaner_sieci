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
import webbrowser
import html
import json

from dataclasses import dataclass, field

@dataclass
class DeviceInfo:
    ip: str
    mac: Optional[str] = None
    hostname: str = "Nieznana"
    open_ports: List[int] = field(default_factory=list)
    guessed_os: str = "Nieznany OS"
    oui_vendor: str = "Nieznany"
    is_host: bool = False
    is_gateway: bool = False
    source: str = "Nieznany" # Np. 'ping', 'arp', 'both'
    hostname_resolved_dns: Optional[str] = None # Nazwa z DNS/NetBIOS
    hostname_from_file: Optional[str] = None
    open_custom_server_ports: List[int] = field(default_factory=list) # Otwarte porty z pliku port_serwer.txt
    dns_lookup_raw_result: str = "Nieznana" # Przechowa oryginalny wynik z gethostbyaddr/getnameinfo

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
NAZWY_MAC_PLIK: str = "mac_nazwy.txt" # Nazwa pliku z niestandardowymi nazwami MAC
NIESTANDARDOWE_PORTY_SERWERA_PLIK: str = "port_serwer.txt" # Nazwa pliku dla niestandardowych portów serwera
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
    8000: "Alternatywny HTTP",
    8001: "Alternatywny HTTPS",
    8080: "Alternatywny HTTPS (często proxy lub serwery web)",
    8123: "Home Assistant (HTTPS)", 
    4357: "Home Assistant (HTTP)", 
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
    8001: "Kubernetes API Server (port insecure)", 
    6443: "Kubernetes API Server (HTTPS)",
    30000-32767: "Zakres NodePort (Kubernetes) - dla eksternalnego dostępu do usług",
    8096: "Jellyfin (HTTP)",
    8989: "Jellyfin (HTTPS)", 
    32400: "Plex Media Server",
    8080: "Audiobookshelf (HTTP) - Domyślny, ale konfigurowalny",
    13378: "Audiobookshelf (HTTP) - Domyślny, ale konfigurowalny",
    8443: "Audiobookshelf (HTTPS) - Jeśli skonfigurowano SSL",
    
    # Inne podobne usługi i ich domyślne porty
}

OS_DEFINITIONS: Dict[str, Dict[str, str]] = {
    # --- Przykładowe wpisy ---
    "LINUX_MEDIA_SAMBA_RDP": {
        "abbr": "Lin/Media (Samba,RDP?)",
        "desc": "Linux Media Center (wykryto SSH, Samba, potencjalnie RDP)"
    },
    "LINUX_MEDIA_SAMBA_RDP_ALT": { 
        "abbr": "Lin/Media (Samba,RDP?)",
        "desc": "Linux Media Center (wykryto SSH, Samba(139), potencjalnie RDP)"
    },
    "NAS_MULTIMEDIA": {
        "abbr": "NAS/MediaSrv",
        "desc": "NAS z usługami multimedialnymi (SSH, Web, SMB, Plex, Jellyfin, etc.)"
    },
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

# def wybierz_kolumny_do_wyswietlenia(
#     wszystkie_kolumny: Dict[str, Dict[str, Any]] = KOLUMNY_TABELI,
#     domyslne_kolumny: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA
# ) -> List[str]:
#     """
#     Pozwala użytkownikowi interaktywnie wybrać kolumny do wyświetlenia w tabeli.

#     Args:
#         wszystkie_kolumny: Słownik definicji wszystkich dostępnych kolumn.
#         domyslne_kolumny: Lista kluczy kolumn wybranych domyślnie.

#     Returns:
#         Lista kluczy wybranych kolumn.
#     """
#     # Pobierz klucze w oryginalnej kolejności
#     oryginalne_klucze = list(wszystkie_kolumny.keys())
#     # Klucze dostępne do wyboru przez użytkownika (bez 'lp')
#     klucze_do_wyboru = [k for k in oryginalne_klucze if k != 'lp']
#     # Klucze aktualnie wybrane przez użytkownika (bez 'lp', które jest dodawane na końcu)
#     wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']

#     while True:
#         print("\n" + "-" * 60)
#         print(f"Wybierz kolumny do wyświetlenia:")
#         print("-" * 60)
#         # Wyświetlaj tylko kolumny dostępne do wyboru
#         for i, klucz in enumerate(klucze_do_wyboru):
#             # Sprawdzaj obecność w `wybrane_klucze_uzytkownika`
#             znacznik = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if klucz in wybrane_klucze_uzytkownika else f"{Fore.RED}[ ]{Style.RESET_ALL}"
#             naglowek = wszystkie_kolumny[klucz]['naglowek']
#             print(f"  {znacznik} {i+1}. {naglowek} ({klucz})")
#         print("-" * 60)
#         print("-" * 60)
#         print("-" * 60)
#         print(f"Opcje: Wpisz {Fore.LIGHTMAGENTA_EX}numer(y){Style.RESET_ALL} kolumn, aby je przełączyć (np. 24).")
#         print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}a{Style.RESET_ALL}', aby zaznaczyć/odznaczyć wszystkie.")
#         print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}d{Style.RESET_ALL}', aby przywrócić domyślne.")
#         print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}q{Style.RESET_ALL}' lub naciśnij {Fore.LIGHTMAGENTA_EX}Enter{Style.RESET_ALL}, aby zatwierdzić wybór.")
#         print("-" * 60)

#         try:
#             wybor = input("Twój wybór: ").lower().strip()

#             if not wybor or wybor == 'q':
#                 # --- CZYSZCZENIE ---
#                 # Przesuń kursor o odpowiednią liczbę linii w górę i wyczyść
#                 liczba_linii_do_wyczyszczenia = len(klucze_do_wyboru) + 10 # Linie z kolumnami + opcje/separatory + nagłówek
#                 for _ in range(liczba_linii_do_wyczyszczenia):
#                     sys.stdout.write("\033[A\033[K")
#                 sys.stdout.flush()
#                 # --- KONIEC CZYSZCZENIA ---
#                 # Dodaj 'lp' na początku przed zwróceniem
#                 finalne_wybrane = ['lp'] + [k for k in oryginalne_klucze if k in wybrane_klucze_uzytkownika]
#                 # print(f"Wybrane kolumny: {', '.join(finalne_wybrane)}")
#                 sys.stdout.write("\033[A") # Przesuń kursor w górę
#                 break # Zakończ pętlę



#             elif wybor == 'a':
#                 # Jeśli wszystkie są już zaznaczone, odznacz wszystkie. W przeciwnym razie zaznacz wszystkie.
#                 if set(wybrane_klucze_uzytkownika) == set(klucze_do_wyboru):
#                     wybrane_klucze_uzytkownika.clear()
#                 else:
#                     wybrane_klucze_uzytkownika = list(klucze_do_wyboru)

#             elif wybor == 'd':
#                 # Przywróć domyślne, ale bez 'lp'
#                 wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']

#             elif wybor.isdigit():
#                 # Iteruj przez każdą cyfrę w wprowadzonym ciągu
#                 przetworzono_poprawnie = True
#                 for cyfra in wybor:
#                     try:
#                         indeks = int(cyfra) - 1
#                         if 0 <= indeks < len(klucze_do_wyboru):
#                             klucz_do_przelaczenia = klucze_do_wyboru[indeks]
#                             if klucz_do_przelaczenia in wybrane_klucze_uzytkownika:
#                                 wybrane_klucze_uzytkownika.remove(klucz_do_przelaczenia)
#                             else:
#                                 wybrane_klucze_uzytkownika.append(klucz_do_przelaczenia)
#                         else:
#                             print(f"{Fore.YELLOW}Nieprawidłowy numer kolumny: {cyfra}. Pomijanie.{Style.RESET_ALL}")
#                             przetworzono_poprawnie = False
#                     except ValueError: # Na wypadek gdyby cyfra nie była cyfrą (chociaż isdigit() powinno to wyłapać)
#                         print(f"{Fore.YELLOW}Nieprawidłowy znak w sekwencji: '{cyfra}'. Pomijanie.{Style.RESET_ALL}")
#                         przetworzono_poprawnie = False
#                 else:
#                     pass # Jeśli nie było błędu dla tej cyfry, kontynuuj
#             else:
#                 print(f"{Fore.YELLOW}Nieznana opcja. Spróbuj ponownie.{Style.RESET_ALL}")

#             # --- CZYSZCZENIE PO KAŻDEJ AKCJI (oprócz wyjścia) ---
#             # Liczba linii: nagłówek(3) + kolumny(len) + sep(1) + opcje(3) + sep(1) + input(1) + ew. błąd(1) = len + 11
#             liczba_linii_do_wyczyszczenia = len(klucze_do_wyboru) + 11
#             for _ in range(liczba_linii_do_wyczyszczenia):
#                 sys.stdout.write("\033[A\033[K")
#             sys.stdout.flush()
#             # --- KONIEC CZYSZCZENIA ---


#         except (EOFError, KeyboardInterrupt):
#             obsluz_przerwanie_uzytkownika()
#         except Exception as e:
#              print(f"\n{Fore.RED}Błąd podczas przetwarzania wyboru: {e}{Style.RESET_ALL}")
#              # W razie błędu, bezpieczniej wrócić do domyślnych
#              print("Przywracanie domyślnych kolumn.")
#              wybrane_klucze_uzytkownika = [k for k in domyslne_kolumny if k != 'lp']
#              finalne_wybrane = ['lp'] + [k for k in oryginalne_klucze if k in wybrane_klucze_uzytkownika]
#              break

#     # Zwróć ostatecznie wybrane klucze, upewniając się, że 'lp' jest na początku
#     return finalne_wybrane


def wybierz_kolumny_do_wyswietlenia_menu(
    wszystkie_kolumny: Dict[str, Dict[str, Any]] = KOLUMNY_TABELI,
    domyslne_kolumny: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA
) -> List[int]: # Funkcja zwraca listę numerów
    """
    Pozwala użytkownikowi interaktywnie wybrać kolumny do wyświetlenia w tabeli
    oraz czy uwzględnić ten wybór w raporcie HTML jako jedną z opcji.
    Zwraca listę numerów (1-based) wszystkich wybranych opcji.

    Args:
        wszystkie_kolumny: Słownik definicji wszystkich dostępnych kolumn.
        domyslne_kolumny: Lista kluczy kolumn wybranych domyślnie.

    Returns:
        Lista numerów (1-based) wybranych opcji (kolumn oraz opcji HTML).
    """
    # Pobierz klucze w oryginalnej kolejności
    oryginalne_klucze = list(wszystkie_kolumny.keys())
    # Klucze dostępne do wyboru przez użytkownika (bez 'lp')
    klucze_do_wyboru_rzeczywiste = [k for k in oryginalne_klucze if k != 'lp']
    
    # Inicjalizacja listy numerów wybranych rzeczywistych kolumn
    wybrane_numery_kolumn_rzeczywistych: List[int] = []
    domyslne_klucze_bez_lp = [k for k in domyslne_kolumny if k != 'lp']
    for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
        if key_in_choosable in domyslne_klucze_bez_lp:
            wybrane_numery_kolumn_rzeczywistych.append(i + 1) # 1-based numer
    
    # Stan dla opcji HTML
    uwzglednij_w_html_selected = False # Domyślnie zaznaczone

    # Numer opcji HTML będzie następnym numerem po rzeczywistych kolumnach
    numer_opcji_html = len(klucze_do_wyboru_rzeczywiste) + 1
    tekst_opcji_html = "Uwzględnić wybór w raporcie HTML"

    while True:
        print("\n" + "-" * 60)
        print(f"Wybierz opcje do wyświetlenia/aktywacji:")
        print("-" * 60)
        
        # Wyświetlaj rzeczywiste kolumny
        for i, klucz in enumerate(klucze_do_wyboru_rzeczywiste):
            numer_biezacej_kolumny = i + 1
            znacznik = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if numer_biezacej_kolumny in wybrane_numery_kolumn_rzeczywistych else f"{Fore.RED}[ ]{Style.RESET_ALL}"
            naglowek = wszystkie_kolumny[klucz]['naglowek']
            print(f"  {znacznik} {numer_biezacej_kolumny}. {naglowek} ({klucz})")
        
        # Dodaj opcję HTML na końcu listy
        znacznik_html = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if uwzglednij_w_html_selected else f"{Fore.RED}[ ]{Style.RESET_ALL}"
        print(f"  {znacznik_html} {numer_opcji_html}. {tekst_opcji_html}")
        
        liczba_wyswietlonych_opcji_wszystkich = len(klucze_do_wyboru_rzeczywiste) + 1 # +1 dla opcji HTML
        print("-" * 60)
        print(f"Opcje: Wpisz {Fore.LIGHTMAGENTA_EX}numer(y){Style.RESET_ALL} opcji, aby je przełączyć (np. 2{numer_opcji_html}).")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}a{Style.RESET_ALL}', aby zaznaczyć/odznaczyć wszystkie opcje.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}d{Style.RESET_ALL}', aby przywrócić domyślne ustawienia.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}q{Style.RESET_ALL}' lub naciśnij {Fore.LIGHTMAGENTA_EX}Enter{Style.RESET_ALL}, aby zatwierdzić wybór.")
        print("-" * 60)

        try:
            wybor = input("Twój wybór: ").lower().strip()

            if not wybor or wybor == 'q':
                liczba_linii_do_wyczyszczenia = liczba_wyswietlonych_opcji_wszystkich + 10
                for _ in range(liczba_linii_do_wyczyszczenia):
                    sys.stdout.write("\033[A\033[K")
                sys.stdout.flush()
                sys.stdout.write("\033[A") 
                break 

            elif wybor == 'a':
                # Sprawdź, czy wszystkie rzeczywiste kolumny ORAZ opcja HTML są zaznaczone
                wszystkie_rzeczywiste_zaznaczone = len(wybrane_numery_kolumn_rzeczywistych) == len(klucze_do_wyboru_rzeczywiste)
                if wszystkie_rzeczywiste_zaznaczone and uwzglednij_w_html_selected:
                    wybrane_numery_kolumn_rzeczywistych.clear()
                    uwzglednij_w_html_selected = False
                else:
                    wybrane_numery_kolumn_rzeczywistych = [i + 1 for i in range(len(klucze_do_wyboru_rzeczywiste))]
                    uwzglednij_w_html_selected = True

            elif wybor == 'd':
                # Przywróć domyślne dla rzeczywistych kolumn
                wybrane_numery_kolumn_rzeczywistych.clear()
                for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
                    if key_in_choosable in domyslne_klucze_bez_lp:
                        wybrane_numery_kolumn_rzeczywistych.append(i + 1)
                # Przywróć domyślne dla opcji HTML
                uwzglednij_w_html_selected = True

            elif wybor.isdigit():
                for cyfra_str in wybor:
                    try:
                        numer_wybrany = int(cyfra_str)
                        
                        if 1 <= numer_wybrany <= len(klucze_do_wyboru_rzeczywiste):
                            # Wybór dotyczy rzeczywistej kolumny
                            if numer_wybrany in wybrane_numery_kolumn_rzeczywistych:
                                wybrane_numery_kolumn_rzeczywistych.remove(numer_wybrany)
                            else:
                                wybrane_numery_kolumn_rzeczywistych.append(numer_wybrany)
                        elif numer_wybrany == numer_opcji_html:
                            # Wybór dotyczy opcji HTML
                            uwzglednij_w_html_selected = not uwzglednij_w_html_selected
                        else:
                            print(f"{Fore.YELLOW}Nieprawidłowy numer opcji: {cyfra_str}. Pomijanie.{Style.RESET_ALL}")
                    except ValueError:
                        print(f"{Fore.YELLOW}Nieprawidłowy znak w sekwencji: '{cyfra_str}'. Pomijanie.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Nieznana opcja. Spróbuj ponownie.{Style.RESET_ALL}")

            liczba_linii_do_wyczyszczenia = liczba_wyswietlonych_opcji_wszystkich + 11
            for _ in range(liczba_linii_do_wyczyszczenia):
                sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()

        except (EOFError, KeyboardInterrupt):
            obsluz_przerwanie_uzytkownika()
        except Exception as e:
             print(f"\n{Fore.RED}Błąd podczas przetwarzania wyboru: {e}{Style.RESET_ALL}")
             # W razie błędu, bezpieczniej wrócić do domyślnych
             print("Przywracanie domyślnych ustawień.")
             wybrane_numery_kolumn_rzeczywistych.clear()
             for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
                 if key_in_choosable in domyslne_klucze_bez_lp:
                     wybrane_numery_kolumn_rzeczywistych.append(i + 1)
             uwzglednij_w_html_selected = True
             break

    # Przygotowanie finalnej listy wybranych numerów
    finalne_wybrane_numery_wszystkie = list(set(wybrane_numery_kolumn_rzeczywistych)) # Unikalne numery kolumn
    if uwzglednij_w_html_selected:
        if numer_opcji_html not in finalne_wybrane_numery_wszystkie: # Dodaj tylko jeśli jeszcze nie ma
            finalne_wybrane_numery_wszystkie.append(numer_opcji_html)
    
    return sorted(list(set(finalne_wybrane_numery_wszystkie))) # Posortuj i upewnij się o unikalności

def wybierz_kolumny_do_wyswietlenia(
    wszystkie_kolumny_map: Dict[str, Dict[str, Any]] = KOLUMNY_TABELI,
    domyslne_kolumny_dla_menu: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA
) -> Tuple[List[str], bool]:
    """
    Wyświetla menu wyboru kolumn i opcji HTML, a następnie tłumaczy
    numeryczny wybór użytkownika na listę kluczy kolumn i flagę HTML.

    Args:
        wszystkie_kolumny_map: Słownik definicji wszystkich dostępnych kolumn.
        domyslne_kolumny_dla_menu: Lista kluczy kolumn, które będą domyślnie
                                   zaznaczone w menu.

    Returns:
        Krotka: (Lista kluczy wybranych kolumn do wyświetlenia,
                   wartość boolowska dla opcji "Uwzględnić wybór w raporcie HTML").
    """
    # Krok 1: Użytkownik wybiera opcje numerycznie za pomocą menu
    wybrane_numery_opcji = wybierz_kolumny_do_wyswietlenia_menu(wszystkie_kolumny_map, domyslne_kolumny_dla_menu)
    print(f"Wybrane numery opcji: {wybrane_numery_opcji}")


    oryginalne_klucze_wszystkich_kolumn = list(wszystkie_kolumny_map.keys())
    klucze_kolumn_do_wyboru_rzeczywiste = [k for k in oryginalne_klucze_wszystkich_kolumn if k != 'lp']

    numer_opcji_html = len(klucze_kolumn_do_wyboru_rzeczywiste) + 1

    finalnie_wybrane_klucze_kolumn_temp: List[str] = []
    uwzglednij_w_html_wybrane = False

    for numer_opcji in wybrane_numery_opcji:
        if 1 <= numer_opcji <= len(klucze_kolumn_do_wyboru_rzeczywiste):
            # To jest numer rzeczywistej kolumny
            klucz_kolumny = klucze_kolumn_do_wyboru_rzeczywiste[numer_opcji - 1]
            finalnie_wybrane_klucze_kolumn_temp.append(klucz_kolumny)
        elif numer_opcji == numer_opcji_html:
            # To jest numer opcji HTML
            uwzglednij_w_html_wybrane = True

    # Przygotowanie finalnej listy kluczy kolumn, z 'lp' na początku i zachowaniem oryginalnej kolejności
    # dla pozostałych wybranych kolumn.
    ostateczne_klucze_do_wyswietlenia: List[str] = ['lp']
    for klucz in oryginalne_klucze_wszystkich_kolumn:
        if klucz != 'lp' and klucz in finalnie_wybrane_klucze_kolumn_temp:
            ostateczne_klucze_do_wyswietlenia.append(klucz)

    return ostateczne_klucze_do_wyswietlenia, uwzglednij_w_html_wybrane




# --- Główna część skryptu ---
if __name__ == "__main__":
    

    # Teraz wywołujemy tylko jedną funkcję, która obsługuje menu i tłumaczenie
    finalne_klucze_kolumn, czy_html_raport = wybierz_kolumny_do_wyswietlenia(
        wszystkie_kolumny_map=KOLUMNY_TABELI, # Można pominąć, jeśli używamy domyślnych
        domyslne_kolumny_dla_menu=DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA # Można pominąć
    )
    
    print(f"Finalnie wybrane klucze kolumn do wyświetlenia: {finalne_klucze_kolumn}")
    # print(f"Uwzględnić wybór w raporcie HTML: {'Tak' if czy_html_raport else 'Nie'}")