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

def sprawdz_i_utworz_plik(nazwa_pliku: str, przykladowa_tresc: Optional[str] = None) -> None:
    """
    Sprawdza, czy plik istnieje w tym samym katalogu co skrypt.
    Jeśli plik nie istnieje, tworzy go i opcjonalnie dodaje przykładową treść.

    Args:
        nazwa_pliku: Nazwa pliku do sprawdzenia/utworzenia.
        przykladowa_tresc: Opcjonalna treść do zapisania w nowym pliku.
    """
    # Uzyskaj ścieżkę do katalogu, w którym znajduje się bieżący skrypt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Połącz ścieżkę katalogu z nazwą pliku
    pelna_sciezka_pliku = os.path.join(script_dir, nazwa_pliku)

    green_color = Fore.GREEN if COLORAMA_AVAILABLE else ""
    yellow_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
    red_color = Fore.RED if COLORAMA_AVAILABLE else ""
    reset_color = Style.RESET_ALL if COLORAMA_AVAILABLE else ""

    if not os.path.exists(pelna_sciezka_pliku):
        try:
            with open(pelna_sciezka_pliku, "w", encoding="utf-8") as f:
                if przykladowa_tresc:
                    f.write(przykladowa_tresc)
            print(f"{green_color}Plik '{nazwa_pliku}' został pomyślnie utworzony w '{script_dir}'.{reset_color}")
            if przykladowa_tresc:
                print(f"{green_color}Dodano przykładową treść.{reset_color}")
        except IOError as e:
            print(f"{red_color}Błąd: Nie można utworzyć pliku '{nazwa_pliku}' w '{script_dir}'. Powód: {e}{reset_color}")
        except Exception as e:
            print(f"{red_color}Nieoczekiwany błąd podczas tworzenia pliku '{nazwa_pliku}': {e}{reset_color}")
    else:
        # Komunikat o istnieniu pliku jest opcjonalny, można go usunąć, jeśli nie jest potrzebny przy każdym wczytaniu
        # print(f"{yellow_color}Plik '{nazwa_pliku}' już istnieje w '{script_dir}'.{reset_color}")
        pass # Plik istnieje, nic nie rób

def pobierz_tabele_arp() -> Optional[str]:
    """
    Pobiera tabelę ARP dla danego systemu operacyjnego, łącząc najlepsze cechy
    i eliminując wady poprzednich wersji.

    Używa `shell=False` dla bezpieczeństwa i lepszej praktyki.
    Poprawnie obsługuje kodowanie dla różnych systemów (np. cp852 dla Windows).
    Zapewnia szczegółową obsługę błędów, w tym FileNotFoundError.

    Returns:
        str: Zawartość tabeli ARP jako string, lub None w przypadku błędu.
    """
    system_os = platform.system().lower()
    cmd_list: List[str] = []
    # Użyj globalnie zdefiniowanych stałych dla kodowania
    encoding_to_use: str = DEFAULT_ENCODING # Domyślnie utf-8

    if system_os == "windows":
        cmd_list = ["arp", "-a"]
        encoding_to_use = WINDOWS_OEM_ENCODING
    elif system_os == "linux":
        cmd_list = ["ip", "-4", "neighbor"]
        # Dla Linuxa, DEFAULT_ENCODING (zazwyczaj utf-8) jest odpowiednie
    elif system_os == "darwin":  # macOS
        cmd_list = ["arp", "-an"]
        # Dla macOS, DEFAULT_ENCODING (zazwyczaj utf-8) jest odpowiednie
    else:
        print(f"{Fore.YELLOW}Nieobsługiwany system operacyjny dla pobierania tabeli ARP: {system_os}{Style.RESET_ALL}")
        return None

    try:
        # Użycie shell=False i przekazanie polecenia jako listy jest bezpieczniejsze.
        # stderr=subprocess.STDOUT przechwytuje również błędy do e.output.
        process_output_bytes = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
        wynik = process_output_bytes.decode(encoding_to_use, errors='ignore')
        return wynik
    except subprocess.CalledProcessError as e:
        # e.output zawiera stdout i stderr, jeśli stderr=subprocess.STDOUT
        error_details = e.output.decode(encoding_to_use, errors='ignore').strip() if e.output else str(e)
        print(f"{Fore.RED}Błąd podczas wykonywania polecenia '{' '.join(cmd_list)}': {error_details}{Style.RESET_ALL}")
        return None
    except FileNotFoundError:
        # cmd_list[0] to nazwa samego polecenia
        print(f"{Fore.RED}Błąd: Polecenie '{cmd_list[0]}' nie znalezione. Upewnij się, że jest zainstalowane i w ścieżce systemowej (PATH).{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas pobierania tabeli ARP za pomocą '{' '.join(cmd_list)}': {e}{Style.RESET_ALL}")
        return None


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
    
def polacz_listy_ip(
    lista_arp: List[str],
    lista_ping: List[str],
    host_ip: Optional[str],
    gateway_ip: Optional[str],
    siec_prefix: str
) -> List[str]:
    """
    Łączy adresy IP z ARP, ping, dodaje IP hosta i bramy (jeśli pasują do prefiksu),
    usuwa duplikaty i sortuje wynikową listę.

    Args:
        lista_arp: Lista adresów IP uzyskanych z tabeli ARP.
        lista_ping: Lista adresów IP, które odpowiedziały na ping.
        host_ip: Adres IP komputera lokalnego.
        gateway_ip: Adres IP bramy domyślnej.
        siec_prefix: Prefiks sieciowy do sprawdzania przynależności host_ip i gateway_ip.

    Returns:
        Posortowana lista unikalnych adresów IP do przetworzenia.
    """
    # print("Łączenie list adresów IP z ARP i ping...")

    unikalne_ip_set = set(lista_arp)
    unikalne_ip_set.update(lista_ping)
    if host_ip and host_ip.startswith(siec_prefix):
        unikalne_ip_set.add(host_ip)
    if gateway_ip and gateway_ip.startswith(siec_prefix):
        unikalne_ip_set.add(gateway_ip)

    final_ip_list = list(unikalne_ip_set)

    # Sortuj listę numerycznie dla lepszej czytelności
    try:
        # Użyj ipaddress do poprawnego sortowania adresów IP
        final_ip_list.sort(key=ipaddress.ip_address)
    except ValueError:
        # Fallback na sortowanie alfabetyczne, jeśli wystąpi błąd
        # (np. jeśli lista zawiera niepoprawne adresy IP)
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można posortować adresów IP numerycznie. Sortowanie alfabetyczne.{Style.RESET_ALL}")
        final_ip_list.sort()

    # print(f"Połączono i usunięto duplikaty. Łączna liczba unikalnych adresów IP: {len(unikalne_ip_lista)}")
    return final_ip_list

def skanuj_porty_rownolegle(
    ips_do_skanowania: List[str],
    max_host_workers: int = MAX_HOSTNAME_WORKERS # Użyj tej samej stałej co dla nazw/OS
) -> Dict[str, List[int]]:
    """
    Skanuje wybrane porty (domyślnie z OPISY_PORTOW) dla listy adresów IP równolegle.

    Args:
        ips_do_skanowania: Lista adresów IP do przeskanowania.
        max_host_workers: Maksymalna liczba wątków do skanowania RÓŻNYCH hostów.

    Returns:
        Słownik mapujący adres IP na listę otwartych portów.
    """
    wyniki_skanowania: Dict[str, List[int]] = {}
    if not ips_do_skanowania:
        print("\nBrak aktywnych hostów do skanowania portów.")
        return wyniki_skanowania

    print(f"\nSkanowanie wybranych portów dla {len(ips_do_skanowania)} aktywnych hostów...")
    try:
        actual_workers = min(max_host_workers, len(ips_do_skanowania))
        if actual_workers <= 0: actual_workers = 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as host_executor:
            # Użyj funkcji skanuj_wybrane_porty_dla_ip, która sama używa wątków do portów
            future_to_ip_scan = {host_executor.submit(skanuj_wybrane_porty_dla_ip, ip): ip for ip in ips_do_skanowania}

            # Reszta logiki z pętlą for as_completed... (bez zmian)
            # ... (skopiuj tutaj pętlę for future in concurrent.futures.as_completed...) ...
            # --- Początek skopiowanej pętli ---
            processed_hosts = 0
            total_hosts_to_scan = len(ips_do_skanowania)
            for future in concurrent.futures.as_completed(future_to_ip_scan):
                ip_skanowany = future_to_ip_scan[future]
                try:
                    lista_otwartych = future.result()
                    wyniki_skanowania[ip_skanowany] = lista_otwartych
                except Exception as exc:
                    print(f'\n{Fore.YELLOW}Skanowanie portów dla {ip_skanowany} zgłosiło wyjątek: {exc}{Style.RESET_ALL}')
                    wyniki_skanowania[ip_skanowany] = [] # Zapisz pustą listę w razie błędu
                processed_hosts += 1
                print(f"\rPostęp skanowania portów: {processed_hosts}/{total_hosts_to_scan} hostów sprawdzonych...", end="")
            # --- Koniec skopiowanej pętli ---
    except KeyboardInterrupt:
        obsluz_przerwanie_uzytkownika() # Obsługa przerwania
    finally:
        print("\r" + " " * 70 + "\r", end="") # Wyczyść linię postępu
    print("Skanowanie portów zakończone.")
    return wyniki_skanowania

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

# Wymaga zainstalowanego psutil

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

def agreguj_informacje_o_urzadzeniach(
    lista_ip_do_przetworzenia: List[str],
    arp_map: Dict[str, str],
    nazwy_hostow_cache: Dict[str, str],
    wyniki_skanowania_portow: Dict[str, List[int]],
    os_cache_wyniki: Dict[str, str],
    baza_oui: Dict[str, str],
    host_ip: Optional[str],
    host_mac: Optional[str],
    gateway_ip: Optional[str],
    hosty_ktore_odpowiedzialy: List[str], # Potrzebne do określenia źródła
    mac_nazwy_map: Dict[str, str],
    configured_custom_server_ports_map: Dict[str, List[int]] # Zmieniono z List[int] na Dict[str, List[int]]
) -> List[DeviceInfo]:
    """Agreguje zebrane informacje o urządzeniach w listę obiektów DeviceInfo."""
    lista_urzadzen: List[DeviceInfo] = []
    print("Agregowanie informacji o urządzeniach...")

    for ip in lista_ip_do_przetworzenia:
        mac = arp_map.get(ip)
        if ip == host_ip and host_mac: # Użyj MAC hosta, jeśli jest znany
            mac = host_mac
        
        resolved_dns_name = nazwy_hostow_cache.get(ip, "Nieznana")
        custom_name_from_file: Optional[str] = None
        hostname_final = resolved_dns_name

        if mac and mac in mac_nazwy_map:
            custom_name_from_file = mac_nazwy_map[mac]
            # Logika łączenia nazw
            if resolved_dns_name == "Nieznana" or resolved_dns_name == "Błąd" or resolved_dns_name == ip:
                hostname_final = custom_name_from_file
            elif custom_name_from_file and custom_name_from_file != resolved_dns_name:
                hostname_final = f"{resolved_dns_name} ({custom_name_from_file})"

        vendor = pobierz_nazwe_producenta_oui(mac, baza_oui) if mac else "Nieznany"

        # Określ źródło (czy odpowiedział na ping, czy był w ARP, czy oba)
        source = "Nieznany"
        in_ping = ip in hosty_ktore_odpowiedzialy
        in_arp = ip in arp_map
        if in_ping and in_arp:
            source = "Ping+ARP"
        elif in_ping:
            source = "Ping"
        elif in_arp:
            source = "ARP"

        # Pobierz wszystkie otwarte porty dla bieżącego IP
        device_all_open_ports = wyniki_skanowania_portow.get(ip, [])
        
        # Identyfikuj, które z otwartych portów urządzenia są niestandardowymi portami serwera
        open_custom_ports_on_device_for_this_ip: List[int] = []
        all_configured_custom_ports_set = set()
        if configured_custom_server_ports_map:
            for proto_ports in configured_custom_server_ports_map.values():
                all_configured_custom_ports_set.update(proto_ports)
        
        if all_configured_custom_ports_set:
            open_custom_ports_on_device_for_this_ip = [
                port for port in device_all_open_ports if port in all_configured_custom_ports_set
            ]
        # --- KONIEC POPRAWKI ---

        device = DeviceInfo(
            ip=ip,
            mac=mac,
            hostname=hostname_final,
            open_ports=device_all_open_ports, # Zapisz wszystkie otwarte porty
            guessed_os=os_cache_wyniki.get(ip, "Nieznany OS"),
            oui_vendor=vendor,
            is_host=(ip == host_ip),
            is_gateway=(ip == gateway_ip),
            source=source,
            hostname_resolved_dns=resolved_dns_name if resolved_dns_name not in ["Nieznana", "Błąd", ip] else None,
            hostname_from_file=custom_name_from_file,
            open_custom_server_ports=open_custom_ports_on_device_for_this_ip,
            dns_lookup_raw_result=resolved_dns_name # Zapisz surowy wynik z DNS/NetBIOS
        )
        lista_urzadzen.append(device)

    print("Agregacja zakończona.")
    return lista_urzadzen


def wyswietl_tabele_urzadzen( 
    lista_urzadzen: List[DeviceInfo],
    kolumny_do_wyswietlenia: List[str],
) -> None:
    """
    Wyświetla tabelę urządzeń na podstawie listy obiektów DeviceInfo.

    Args:
        lista_urzadzen: Lista obiektów DeviceInfo do wyświetlenia.
        kolumny_do_wyswietlenia: Lista kluczy kolumn do wyświetlenia.
    """
    # --- Wyświetlanie tabeli ---
    aktywne_kolumny = {k: v for k, v in KOLUMNY_TABELI.items() if k in kolumny_do_wyswietlenia}
    # Oblicz szerokość i separator jak wcześniej...
    # Upewnij się, że szerokość jest obliczana poprawnie
    try:
        # Oblicz sumę szerokości tylko dla aktywnych kolumn, które są w `kolumny_do_wyswietlenia`
        total_width = sum(col["szerokosc"] for col_key, col in aktywne_kolumny.items() if col_key in kolumny_do_wyswietlenia)
        # Dodaj liczbę separatorów (liczba aktywnych kolumn - 1)
        num_separators = len([k for k in kolumny_do_wyswietlenia if k in aktywne_kolumny]) - 1
        if num_separators > 0:
            total_width += num_separators
        if total_width <= 0: total_width = DEFAULT_LINE_WIDTH # Fallback
    except Exception:
        total_width = DEFAULT_LINE_WIDTH # Fallback w razie błędu
    separator_line = "-" * total_width

    print("\n")

    wyswietl_tekst_w_linii("-", total_width, "Podsumowanie skanowania urządzeń w sieci", Fore.LIGHTGREEN_EX, Fore.LIGHTCYAN_EX) # Zmieniono kolor tytułu

    # Wyświetl nagłówek...
    header_parts = []
    for col_key in kolumny_do_wyswietlenia:
        if col_key in aktywne_kolumny:
            col_config = aktywne_kolumny[col_key]
            header_parts.append(f"{col_config['naglowek']:<{col_config['szerokosc']}}")
    # Użyj COLORAMA_AVAILABLE do warunkowego kolorowania
    if COLORAMA_AVAILABLE:
        print(f"{Fore.LIGHTYELLOW_EX}{' '.join(header_parts)}{Style.RESET_ALL}")
    else:
        print(' '.join(header_parts))
    print(separator_line)

    if not lista_urzadzen:
        print(f"{Fore.YELLOW}Nie znaleziono żadnych urządzeń do wyświetlenia.{Style.RESET_ALL}")
    else:
        for idx, device in enumerate(lista_urzadzen, start=1):
            mac_display = device.mac if device.mac else "Nieznany MAC"
            porty_str = ', '.join(map(str, device.open_ports)) if device.open_ports else ""

            oznaczenia = []
            if device.is_host: oznaczenia.append("(Ty)")
            if device.is_gateway: oznaczenia.append("(Brama)")
            if device.source == "ARP": oznaczenia.append("(ARP Only)") # Dodano oznaczenie ARP
            oznaczenie_str = " ".join(oznaczenia)

            nazwa_finalna = device.hostname
            if oznaczenie_str:
                if device.hostname in ["Nieznana", "Błąd"]:
                    # nazwa_finalna = f"{device.ip} {oznaczenie_str}"
                    nazwa_finalna = f"{device.hostname} {oznaczenie_str}"
                else:
                    nazwa_finalna = f"{device.hostname} {oznaczenie_str}"

            row_data = {
                "lp": str(idx),
                "ip": device.ip,
                "mac": mac_display,
                "host": nazwa_finalna,
                "porty": porty_str,
                "os": device.guessed_os,
                "oui": device.oui_vendor
                # Można dodać 'source', jeśli jest w KOLUMNY_TABELI
            }

            line_parts = []
            for col_key in kolumny_do_wyswietlenia:
                if col_key in aktywne_kolumny:
                    col_config = aktywne_kolumny[col_key]
                    data = row_data.get(col_key, "")

                    # Logika kolorowania z priorytetami
                    color = Fore.WHITE # Domyślny kolor
                    if device.dns_lookup_raw_result == "Błąd" or device.guessed_os == "Błąd OS":
                        color = Fore.RED
                    elif device.source == "ARP": # Tylko ARP (nie odpowiedział na ping)
                        color = Fore.MAGENTA
                    elif device.hostname_resolved_dns: # Nazwa rozwiązana przez DNS/NetBIOS (i nie jest to "Nieznana", "Błąd" ani IP)
                        color = Fore.CYAN
                    elif device.oui_vendor != "Nieznany": # Producent OUI znany
                        color = Fore.GREEN

                    # Przytnij dane do szerokości kolumny
                    formatted_data = f"{data:<{col_config['szerokosc']}.{col_config['szerokosc']}}"

                    # Dodaj kolor do części linii tylko jeśli colorama jest dostępne
                    if COLORAMA_AVAILABLE:
                         line_parts.append(f"{color}{formatted_data}{Style.RESET_ALL}")
                    else:
                         line_parts.append(formatted_data)

            line_format = ' '.join(line_parts)
            print(line_format) # Kolory są już w line_parts

    print(separator_line)
    # Funkcja już nic nie zwraca

def zgadnij_systemy_rownolegle(
    ips_do_sprawdzenia: List[str],
    wyniki_portow: Dict[str, List[int]],
    max_workers: int = MAX_HOSTNAME_WORKERS # Użyj tej samej stałej co dla nazw
) -> Dict[str, str]:
    """
    Zgaduje systemy operacyjne dla podanej listy adresów IP równolegle.

    Args:
        ips_do_sprawdzenia: Lista adresów IP do sprawdzenia.
        wyniki_portow: Słownik z wynikami skanowania portów {ip: [porty]}.
        max_workers: Maksymalna liczba wątków do użycia.

    Returns:
        Słownik mapujący adres IP na przypuszczalny typ systemu (lub "Błąd OS").
    """
    os_cache: Dict[str, str] = {}
    if not ips_do_sprawdzenia:
        return os_cache

    print(f"\nIdentyfikacja możliwych systemów operacyjnych dla {len(ips_do_sprawdzenia)} adresów...")
    try:
        total_tasks_os = len(ips_do_sprawdzenia)
        for i, ip in enumerate(ips_do_sprawdzenia):
            try:
                os_cache[ip] = zgadnij_system_operacyjny(ip, otwarte_porty_znane=wyniki_portow.get(ip, []))
            except Exception as exc:
                print(f'\n{Fore.YELLOW}Błąd podczas zgadywania OS dla {ip}: {exc}{Style.RESET_ALL}')
                os_cache[ip] = "Błąd OS" # Oznacz błąd
            # Aktualizacja postępu (opcjonalnie, może spowalniać przy dużej liczbie IP)
            print(f"\rPostęp zgadywania OS: {i + 1}/{total_tasks_os}...", end="")        
    except KeyboardInterrupt:
        obsluz_przerwanie_uzytkownika() # Lub rzuć dalej, jeśli obsługa jest wyżej
    finally:
        print("\r" + " " * 70 + "\r", end="") # Wyczyść linię postępu
    print("Zgadywanie systemów zakończone.")
    return os_cache

def wczytaj_mac_nazwy_z_pliku(nazwa_pliku: str = NAZWY_MAC_PLIK) -> Dict[str, str]:
    """
    Wczytuje niestandardowe nazwy urządzeń przypisane do adresów MAC z pliku.
    Plik powinien znajdować się w tej samej lokalizacji co skrypt.
    Format linii w pliku: MAC_ADRES NAZWA_URZADZENIA (separatorem może być spacja, przecinek, średnik, tabulator).
    Linie zaczynające się od '#' są ignorowane jako komentarze.
    """
    mac_nazwy_map: Dict[str, str] = {}
        # Domyślna treść dla pliku mac_nazwy.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plik_path = os.path.join(script_dir, nazwa_pliku)

    # Regex do ekstrakcji MAC adresu z początku linii
    # Akceptuje MAC z dwukropkami, myślnikami lub bez separatorów.
    mac_pattern_extract = re.compile(
        r"^([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})[:-]?([0-9A-Fa-f]{2})"
    )

    # Domyślna treść dla pliku mac_nazwy.txt
    przykladowa_tresc_mac_nazwy = """# Przykładowy plik z niestandardowymi nazwami dla adresów MAC.
# Każda linia powinna zawierać adres MAC, a następnie nazwę.
# Separatorami mogą być spacje lub tabulatory.
# Linie zaczynające się od '#' są ignorowane jako komentarze.
# Przykłady:
# AA:BB:CC:DD:EE:FF MojSerwerNAS
# 11-22-33-44-55-66 DrukarkaBiuro
# 001122334455 KameraIP
FF:FF:FF:FF:FF:FF PrzykładowaNazwa"""
    sprawdz_i_utworz_plik(nazwa_pliku, przykladowa_tresc_mac_nazwy)

    if not os.path.exists(plik_path):
        print(f"{Fore.YELLOW}Informacja: Plik '{nazwa_pliku}' nie został znaleziony w lokalizacji skryptu. Nazwy niestandardowe nie zostaną wczytane.{Style.RESET_ALL}")
        return mac_nazwy_map

    print(f"Próba wczytania niestandardowych nazw urządzeń z pliku: '{plik_path}'...")
    try:
        with open(plik_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"): # Ignoruj puste linie i komentarze
                    continue

                mac_match = mac_pattern_extract.match(line)
                if mac_match:
                    mac_parts = mac_match.groups()
                    normalized_mac = ":".join(part.upper() for part in mac_parts)
                    
                    # Reszta linii po dopasowanym MAC to nazwa
                    name_part = line[mac_match.end():].strip()
                    # Usuń popularne separatory wiodące dla części z nazwą
                    name_part = re.sub(r"^[ \t,;]+", "", name_part)

                    if name_part:
                        mac_nazwy_map[normalized_mac] = name_part
                    else:
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Znaleziono MAC '{normalized_mac}', ale brak nazwy.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nie udało się sparsować MAC adresu. Linia: '{line}'{Style.RESET_ALL}")
        
        if mac_nazwy_map:
            print(f"\n{Fore.GREEN}Pomyślnie wczytano {len(mac_nazwy_map)} niestandardowych nazw urządzeń.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Nie wczytano żadnych niestandardowych nazw urządzeń z pliku '{nazwa_pliku}' (plik może być pusty lub zawierać tylko komentarze).{Style.RESET_ALL}")

    except IOError as e:
        print(f"{Fore.RED}Błąd odczytu pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas przetwarzania pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")

    return mac_nazwy_map

def wczytaj_niestandardowe_porty_serwera(nazwa_pliku: str = NIESTANDARDOWE_PORTY_SERWERA_PLIK) -> Dict[str, List[int]]:
    """
    Wczytuje listę niestandardowych portów serwera (HTTP/HTTPS) z pliku.
    Plik powinien znajdować się w tej samej lokalizacji co skrypt.
    Format: sekcje [http] lub [https], a pod nimi numery portów.
    Linie zaczynające się od '#' są ignorowane jako komentarze.
    """
    niestandardowe_porty_map: Dict[str, List[int]] = {"http": [], "https": []}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plik_path = os.path.join(script_dir, nazwa_pliku)

    # Domyślna treść dla pliku port_serwer.txt
    domyslna_tresc_port_serwer = """# Przykładowy plik z niestandardowymi portami dla serwerów HTTP/HTTPS
# Linie zaczynające się od '#' są ignorowane.
[http]
80
[https]
443"""
    # Najpierw sprawdź/utwórz plik z domyślną treścią, jeśli nie istnieje
    sprawdz_i_utworz_plik(nazwa_pliku, domyslna_tresc_port_serwer)

    plik_path = os.path.join(script_dir, nazwa_pliku)

    if not os.path.exists(plik_path):
        print(f"{Fore.YELLOW}Informacja: Plik '{nazwa_pliku}' nie został znaleziony. Brak niestandardowych portów serwera do wczytania.{Style.RESET_ALL}")
        return niestandardowe_porty_map

    print(f"Próba wczytania niestandardowych portów serwera z pliku: '{plik_path}'...")
    try:
        current_section: Optional[str] = None # Dodano inicjalizację current_section
        with open(plik_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):  # Ignoruj puste linie i komentarze
                    continue
                
                section_match = re.match(r"^\[(https?)\]$", line, re.IGNORECASE)
                if section_match:
                    current_section = section_match.group(1).lower()
                    if current_section not in niestandardowe_porty_map: # Powinno być 'http' lub 'https'
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nieznana sekcja '{current_section}'. Oczekiwano [http] lub [https]. Pomijanie sekcji.{Style.RESET_ALL}")
                        current_section = None # Ignoruj porty do czasu znalezienia prawidłowej sekcji
                    continue

                if current_section:
                    try:
                        port = int(line)
                        if 1 <= port <= 65535:
                            if port not in niestandardowe_porty_map[current_section]: # Unikaj duplikatów w danej sekcji
                                niestandardowe_porty_map[current_section].append(port)
                        else:
                            print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Port '{port}' jest poza prawidłowym zakresem (1-65535) w sekcji '{current_section}'. Pomijanie.{Style.RESET_ALL}")
                    except ValueError:
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nie udało się sparsować numeru portu '{line}' w sekcji '{current_section}'. Pomijanie.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Port '{line}' znaleziony poza sekcją [http] lub [https]. Pomijanie.{Style.RESET_ALL}")
  

        total_ports_loaded = len(niestandardowe_porty_map["http"]) + len(niestandardowe_porty_map["https"])
        if total_ports_loaded > 0:
            print(f"{Fore.GREEN}Pomyślnie wczytano {total_ports_loaded} niestandardowych portów serwera.{Style.RESET_ALL}")
            if niestandardowe_porty_map["http"]:
                niestandardowe_porty_map["http"].sort()
                print(f"  HTTP porty: {niestandardowe_porty_map['http']}")
            if niestandardowe_porty_map["https"]:
                niestandardowe_porty_map["https"].sort()
                print(f"  HTTPS porty: {niestandardowe_porty_map['https']}")
        else:
            print(f"{Fore.YELLOW}Nie wczytano żadnych niestandardowych portów serwera z pliku '{nazwa_pliku}'.{Style.RESET_ALL}")

    except IOError as e:
        print(f"{Fore.RED}Błąd odczytu pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas przetwarzania pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")

    return niestandardowe_porty_map

def rozdziel_nazwe_pliku(pelna_nazwa_pliku: str) -> tuple[str, str]:
    """
    Rozdziela pełną nazwę pliku na nazwę bazową i rozszerzenie.

    Args:
        pelna_nazwa_pliku: Pełna nazwa pliku (np. "raport_skanowania.html").

    Returns:
        Krotka zawierająca dwie wartości:
        - Nazwa bazowa pliku (np. "raport_skanowania").
        - Rozszerzenie pliku z kropką (np. ".html").
          Jeśli plik nie ma rozszerzenia, druga wartość będzie pustym stringiem.
    """
    nazwa_bazowa, rozszerzenie = os.path.splitext(pelna_nazwa_pliku)
    return nazwa_bazowa, rozszerzenie

# Przykład użycia:
nazwa_pliku_html = "raport_skanowania.html"
nazwa, rozs = rozdziel_nazwe_pliku(nazwa_pliku_html)
# print(f"Pełna nazwa: {nazwa_pliku_html}")
# print(f"Nazwa bazowa: {nazwa}")
# print(f"Rozszerzenie: {rozs}")

nazwa_pliku_bez_rozszerzenia = "plik_bez_kropki"
nazwa, rozs = rozdziel_nazwe_pliku(nazwa_pliku_bez_rozszerzenia)
# print(f"\nPełna nazwa: {nazwa_pliku_bez_rozszerzenia}")
# print(f"Nazwa bazowa: {nazwa}")
# print(f"Rozszerzenie: {rozs}")

nazwa_pliku_z_kropkami = "plik.z.wieloma.kropkami.txt"
nazwa, rozs = rozdziel_nazwe_pliku(nazwa_pliku_z_kropkami)
# print(f"\nPełna nazwa: {nazwa_pliku_z_kropkami}")
# print(f"Nazwa bazowa: {nazwa}")
# print(f"Rozszerzenie: {rozs}")

plik_zaczynajacy_od_kropki = ".bashrc"
nazwa, rozs = rozdziel_nazwe_pliku(plik_zaczynajacy_od_kropki)
# print(f"\nPełna nazwa: {plik_zaczynajacy_od_kropki}")
# print(f"Nazwa bazowa: {nazwa}") # Zwróci ".bashrc


def zapisz_tabele_urzadzen_do_html(
    lista_urzadzen: List[DeviceInfo],
    kolumny_do_wyswietlenia: List[str],
    opisy_portow_globalne: Dict[int, str],
    configured_custom_server_ports_map: Dict[str, List[int]],
    nazwa_pliku_html: str = "raport_skanowania.html", # Domyślna nazwa pliku
    siec_prefix: Optional[str] = None # Opcjonalny prefiks sieci do dodania do nazwy pliku
) -> Optional[str]: # Zmieniono typ zwracany na Optional[str]
    """
    Zapisuje tabelę urządzeń do pliku HTML z interaktywnym sortowaniem.
    (Reszta opisu bez zmian)
    """
    nazwa_bazowa_pliku, rozszerzenie_pliku = rozdziel_nazwe_pliku(nazwa_pliku_html)

    if siec_prefix:
        prefix_dla_nazwy = siec_prefix.rstrip('.').replace('.', '_')
        prefix_with_start_ip = f"{prefix_dla_nazwy}_{DEFAULT_START_IP}"
        finalna_nazwa_pliku_html = f"{nazwa_bazowa_pliku}_{prefix_with_start_ip}{rozszerzenie_pliku}"
    else:
        finalna_nazwa_pliku_html = nazwa_pliku_html

    aktywne_kolumny = {k: v for k, v in KOLUMNY_TABELI.items() if k in kolumny_do_wyswietlenia}
    
    # Konwertuj listę kolumn do formatu JSON dla JavaScript
    kolumny_do_wyswietlenia_json = json.dumps(kolumny_do_wyswietlenia)


    html_content = f"""
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport Skanowania Sieci</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }}
        h1 {{ text-align: center; color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); background-color: #fff; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; text-align: center; position: relative; }} /* Dodano position: relative */
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f1f1f1; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .legend-section {{ margin-top: 30px; padding: 15px; background-color: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .legend-section h2 {{ margin-top: 0; color: #4CAF50; }}
        .legend-section ul {{ list-style-type: none; padding-left: 0; }}
        .legend-section li {{ margin-bottom: 5px; }}
        .device-row td {{ vertical-align: top; }}
        
        /* Style dla sortowania */
        th.sortable-header {{ cursor: pointer; }}
        th.sortable-header:hover {{ background-color: #3e8e41; }}
        .sort-indicator {{
            display: inline-block; /* Zmieniono na inline-block dla lepszego pozycjonowania */
            margin-left: 5px;
            color: #a0d0a0; /* Jaśniejszy kolor dla nieaktywnych wskaźników */
            font-size: 0.9em;
            /* Pozycjonowanie wskaźnika, jeśli chcemy go np. po prawej stronie */
            /* position: absolute; */
            /* right: 10px; */
            /* top: 50%; */
            /* transform: translateY(-50%); */
        }}
        .sort-indicator.active {{
            color: white; /* Kolor aktywnego wskaźnika */
        }}
    </style>
</head>
<body>
    <h1>Raport Skanowania Sieci</h1>
    <table>
        <thead>
            <tr>
"""
    # Nagłówki tabeli
    for col_key in kolumny_do_wyswietlenia:
        if col_key in aktywne_kolumny:
            col_config = aktywne_kolumny[col_key]
            header_text = html.escape(col_config['naglowek'])
            if col_key not in ["lp", "porty"]: # Kolumny Lp i Otwarte Porty nie są sortowalne
                html_content += f"""
                <th class="sortable-header" data-column-key="{html.escape(col_key)}">
                    {header_text}
                    <span class="sort-indicator">&#x25B2;&#x25BC;</span>
                </th>
"""
            else:
                html_content += f"                <th>{header_text}</th>\n"
    html_content += """
            </tr>
        </thead>
        <tbody id="devicesTableBody">
"""

     # Wiersze tabeli
    for idx, device in enumerate(lista_urzadzen, start=1):
        mac_display = device.mac if device.mac else "Nieznany MAC"
        
        # ... (logika generowania porty_html_output bez zmian) ...
        open_ports_html_parts = []
        if device.open_ports:
            for port_num in sorted(list(device.open_ports)):
                port_display_str = str(port_num)
                if port_num in device.open_custom_server_ports: 
                    protocol = "http" 
                    if configured_custom_server_ports_map.get("https") and port_num in configured_custom_server_ports_map["https"]:
                        protocol = "https"
                    elif configured_custom_server_ports_map.get("http") and port_num in configured_custom_server_ports_map["http"]:
                         protocol = "http"
                    link_href = f"{protocol}://{html.escape(device.ip)}:{port_num}"
                    port_display_str = f'<a href="{link_href}" target="_blank">{port_num}</a>'
                open_ports_html_parts.append(port_display_str)
        porty_html_output = ', '.join(open_ports_html_parts) if open_ports_html_parts else ""


        oznaczenia = []
        if device.is_host: oznaczenia.append("(Ty)")
        if device.is_gateway: oznaczenia.append("(Brama)")
        if device.source == "ARP": oznaczenia.append("(ARP Only)")
        oznaczenie_str = " ".join(oznaczenia)

        # --- UPROSZCZONA LOGIKA DLA NAZWY HOSTA W HTML (jak w terminalu) ---
        # Zawsze używaj device.hostname jako podstawy
        content_for_host_display = html.escape(device.hostname)

        # Połącz podstawową treść z oznaczeniami
        if oznaczenie_str:
            nazwa_do_wyswietlenia_hosta = f"{content_for_host_display} {html.escape(oznaczenie_str)}"
        else:
            nazwa_do_wyswietlenia_hosta = content_for_host_display

        row_data_base = {
            "lp": str(idx),
            "ip": html.escape(device.ip),
            "mac": html.escape(mac_display),
            "host": nazwa_do_wyswietlenia_hosta, # Ta wartość jest już gotowa do wyświetlenia
            "porty": porty_html_output,
            "os": html.escape(device.guessed_os),
            "oui": html.escape(device.oui_vendor)
        }

        html_content += "            <tr class='device-row'>\n" # Dodajemy klasę dla JS
        for col_key in kolumny_do_wyswietlenia:
            if col_key in aktywne_kolumny:
                data_to_display = row_data_base.get(col_key, "")
                html_content += f"                <td>{data_to_display}</td>\n"
        html_content += "            </tr>\n"
    html_content += """
        </tbody>
    </table>
"""
    # Dodawanie legend (bez zmian)
    html_content += """
    <div class="legend-section">
        <h2>Legenda Otwartych Portów</h2>
        <ul>
"""
    wszystkie_otwarte_porty_set = set()
    for dev_ports in lista_urzadzen:
        wszystkie_otwarte_porty_set.update(dev_ports.open_ports)

    if wszystkie_otwarte_porty_set:
        posortowane_porty = sorted(list(wszystkie_otwarte_porty_set))
        for port in posortowane_porty:
            opis = opisy_portow_globalne.get(port, "Nieznana usługa")
            html_content += f"            <li><b>Port {html.escape(str(port))}:</b> {html.escape(opis)}</li>\n"
    else:
        html_content += "            <li>Brak wykrytych otwartych portów.</li>\n"
    html_content += """
        </ul>
    </div>
"""
    html_content += """
    <div class="legend-section">
        <h2>Legenda Skrótów Systemów/Urządzeń</h2>
        <ul>
"""
    uzyte_skroty_os_set = {dev.guessed_os for dev in lista_urzadzen if dev.guessed_os}
    if uzyte_skroty_os_set:
        skrot_do_opisu_map: Dict[str, str] = {v["abbr"]: v["desc"] for k, v in OS_DEFINITIONS.items() if v.get("abbr") in uzyte_skroty_os_set}
        for skrot_os in sorted(list(uzyte_skroty_os_set)):
            opis_pelny = skrot_do_opisu_map.get(skrot_os, "Brak opisu w definicjach")
            html_content += f"            <li><b>{html.escape(skrot_os)}:</b> {html.escape(opis_pelny)}</li>\n"
    else:
        html_content += "            <li>Brak zidentyfikowanych typów systemów/urządzeń.</li>\n"
    html_content += """
        </ul>
    </div>

    <script>
        const displayedColumns = """ + kolumny_do_wyswietlenia_json + """;
        let currentSortKey = null;
        let currentSortDirection = 'none'; // 'asc', 'desc', 'none'

        function getCellContentForSort(row, columnKey) {
            const columnIndex = displayedColumns.indexOf(columnKey);
            if (columnIndex === -1 || !row.cells[columnIndex]) {
                return '';
            }
            let cellText = row.cells[columnIndex].textContent || row.cells[columnIndex].innerText || '';
            cellText = cellText.trim();

            if (columnKey === 'host') {
                // Usuwa znaczniki typu (Ty), (Brama), (ARP Only) z końca dla sortowania
                // Dzieli po pierwszym wystąpieniu " (" i bierze pierwszą część
                const parts = cellText.split(" (");
                cellText = parts[0].trim();
            }
            return cellText;
        }

        function compareIpAddresses(ipA, ipB) {
            const partsA = ipA.split('.').map(Number);
            const partsB = ipB.split('.').map(Number);
            for (let i = 0; i < 4; i++) {
                if (isNaN(partsA[i]) && isNaN(partsB[i])) continue;
                if (isNaN(partsA[i])) return 1; // Traktuj NaN jako większe
                if (isNaN(partsB[i])) return -1; // Traktuj NaN jako większe

                if (partsA[i] < partsB[i]) return -1;
                if (partsA[i] > partsB[i]) return 1;
            }
            return 0;
        }

        function compareValues(key, order, rowA, rowB) {
            const valA = getCellContentForSort(rowA, key);
            const valB = getCellContentForSort(rowB, key);

            let comparison = 0;
            if (key === 'ip') {
                comparison = compareIpAddresses(valA, valB);
            } else {
                const specialValues = ["Nieznana", "Błąd", "Nieznany MAC", "Nieznany OS"];
                // Sprawdź, czy wartość ZACZYNA SIĘ od specjalnej wartości (np. "Nieznana (Ty)")
                const isASpecial = specialValues.some(sv => valA.startsWith(sv));
                const isBSpecial = specialValues.some(sv => valB.startsWith(sv));

                if (isASpecial && !isBSpecial) {
                    comparison = 1; 
                } else if (!isASpecial && isBSpecial) {
                    comparison = -1;
                } else {
                    if (valA.toLowerCase() < valB.toLowerCase()) {
                        comparison = -1;
                    }
                    if (valA.toLowerCase() > valB.toLowerCase()) {
                        comparison = 1;
                    }
                }
            }
            return (order === 'desc' ? (comparison * -1) : comparison);
        }

        function updateSortIndicators(clickedThKey, direction) {
            document.querySelectorAll('th.sortable-header .sort-indicator').forEach(span => {
                const th = span.closest('th');
                if (th.dataset.columnKey === clickedThKey) {
                    span.innerHTML = direction === 'asc' ? '&#x25B2;' : (direction === 'desc' ? '&#x25BC;' : '&#x25B2;&#x25BC;');
                    span.classList.add('active');
                } else {
                    span.innerHTML = '&#x25B2;&#x25BC;';
                    span.classList.remove('active');
                }
            });
        }

        function sortTable(columnKey, thElement) {
            if (currentSortKey === columnKey) {
                if (currentSortDirection === 'asc') {
                    currentSortDirection = 'desc';
                } else if (currentSortDirection === 'desc') {
                    // Opcjonalnie: trzecie kliknięcie resetuje sortowanie lub wraca do 'asc'
                    // Tutaj wracamy do 'asc' dla prostoty
                     currentSortDirection = 'asc'; 
                    // currentSortDirection = 'none'; // Jeśli chcesz resetować
                } else { // Było 'none'
                    currentSortDirection = 'asc';
                }
            } else {
                currentSortKey = columnKey;
                currentSortDirection = 'asc';
            }
            
            // if (currentSortDirection === 'none' && currentSortKey === columnKey) {
            //     // Jeśli chcemy resetować, to tutaj odtwarzamy oryginalną kolejność
            //     // To wymagałoby przechowywania oryginalnych danych lub ponownego renderowania
            //     // Na razie pomijamy pełny reset dla uproszczenia
            //     updateSortIndicators(columnKey, 'none');
            //     // return; // Nie sortuj, jeśli reset
            // }


            updateSortIndicators(columnKey, currentSortDirection);

            const tableBody = document.getElementById('devicesTableBody');
            const rows = Array.from(tableBody.querySelectorAll('tr.device-row'));

            rows.sort((a, b) => compareValues(columnKey, currentSortDirection, a, b));

            // Ponowne numerowanie kolumny Lp.
            const lpCellIndex = displayedColumns.indexOf('lp');
            if (lpCellIndex !== -1) {
                rows.forEach((row, index) => {
                    if (row.cells[lpCellIndex]) {
                        row.cells[lpCellIndex].textContent = index + 1;
                    }
                });
            }
            
            tableBody.innerHTML = ''; // Wyczyść istniejące wiersze
            rows.forEach(row => tableBody.appendChild(row));
        }

        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('th.sortable-header').forEach(th => {
                th.addEventListener('click', () => {
                    const columnKey = th.dataset.columnKey;
                    sortTable(columnKey, th);
                });
            });
        });
    </script>
</body>
</html>
"""
    try:
        with open(finalna_nazwa_pliku_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        green_color = Fore.GREEN if COLORAMA_AVAILABLE else ""
        red_color = Fore.RED if COLORAMA_AVAILABLE else ""
        reset_color = Style.RESET_ALL if COLORAMA_AVAILABLE else ""
        
        abs_path_pliku_html = os.path.abspath(finalna_nazwa_pliku_html)
        print(f"{green_color}Pomyślnie zapisano raport do pliku: {abs_path_pliku_html}{reset_color}")
        return abs_path_pliku_html # Zwróć pełną ścieżkę do pliku
    except IOError as e:
        print(f"{red_color}Błąd zapisu do pliku HTML '{finalna_nazwa_pliku_html}': {e}{reset_color}")
        return None # Zwróć None w przypadku błędu
    except Exception as e:
        print(f"{red_color}Nieoczekiwany błąd podczas zapisu pliku HTML: {e}{reset_color}")
        return None # Zwróć None w przypadku błędu
    
def wyswietl_legende_kolorow_urzadzen(line_width: int = DEFAULT_LINE_WIDTH) -> None:
    """
    Wyświetla legendę opisującą znaczenie kolorów używanych
    do wyróżniania urządzeń w tabeli.
    """
    if not COLORAMA_AVAILABLE:
        # Informacja, że legenda kolorów nie ma zastosowania, jeśli colorama jest niedostępne
        # Można to pominąć, jeśli nie chcemy tego komunikatu
        # print(f"\n{Fore.YELLOW}Informacja: Kolorowanie jest wyłączone (brak biblioteki 'colorama'). Legenda kolorów nie ma zastosowania.{Style.RESET_ALL}")
        return

    wyswietl_tekst_w_linii("-", line_width, "Legenda kolorów urządzeń", Fore.LIGHTYELLOW_EX, Fore.LIGHTCYAN_EX, True)
    print(f"  {Fore.MAGENTA}Magenta{Style.RESET_ALL} : Urządzenie znalezione tylko w tabeli ARP (nie odpowiedziało na ping).")
    print(f"  {Fore.CYAN}Cyjan{Style.RESET_ALL}   : IP potwierdzone ping i ARP, Urządzenie z poprawnie rozwiązaną nazwą hosta (DNS/NetBIOS).")
    print(f"  {Fore.GREEN}Zielony{Style.RESET_ALL} : IP potwierdzone ping i ARP. Urządzenie ze znanym producentem (na podstawie adresu MAC - OUI).")
    print(f"  {Fore.RED}Czerwony{Style.RESET_ALL}: Wystąpił błąd podczas pobierania nazwy hosta lub identyfikacji OS.")
    print(f"  {Fore.WHITE}Biały{Style.RESET_ALL}   : IP potwierdzone ping i ARP, ale nieznane nazwa hosta i nieznany producent, brak błędów.")
    # Można dodać linię końcową, jeśli chcesz
    # print("-" * line_width)

def zapytaj_i_otworz_raport_html(sciezka_do_pliku_html: Optional[str]) -> None:
    """
    Pyta użytkownika, czy chce otworzyć wygenerowany raport HTML w przeglądarce.
    Jeśli użytkownik potwierdzi, próbuje otworzyć plik.

    Args:
        sciezka_do_pliku_html: Ścieżka do pliku HTML lub None, jeśli plik nie został zapisany.
    """
    if not sciezka_do_pliku_html:
        return

    try:
        prompt_text = f"Czy chcesz otworzyć raport HTML ({os.path.basename(sciezka_do_pliku_html)}) w przeglądarce? (T/n): "
        odpowiedz_otwarcie = input(prompt_text).lower().strip()
        # Jeśli użytkownik naciśnie Enter (pusta odpowiedź) LUB wpisze 't'/'y'
        if not odpowiedz_otwarcie or odpowiedz_otwarcie.startswith('t') or odpowiedz_otwarcie.startswith('y'):
            file_url = f"file://{sciezka_do_pliku_html}"
            webbrowser.open(file_url)
            print(f"Próba otwarcia pliku {sciezka_do_pliku_html} w domyślnej przeglądarce...")
        else:
            print("Pominięto otwieranie raportu w przeglądarce.")
    except Exception as e:
        print(f"{Fore.RED}Nie udało się automatycznie otworzyć pliku w przeglądarce: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Możesz otworzyć plik ręcznie: {sciezka_do_pliku_html}{Style.RESET_ALL}")


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
        gateway_ip = pobierz_brame_domyslna()
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
        mac_nazwy_niestandardowe = wczytaj_mac_nazwy_z_pliku()

        niestandardowe_porty_serwera_mapa = wczytaj_niestandardowe_porty_serwera() # Zmieniona nazwa zmiennej
        # Skanowanie sieci
        print("\nRozpoczynanie skanowania sieci (ping)...")
        start_arp_time = time.time() # Przesunięto start timera tutaj
        
        hosty_ktore_odpowiedzialy = pinguj_zakres(siec_prefix, DEFAULT_START_IP, DEFAULT_END_IP)
        
        adresy_ip_z_arp = pobierz_ip_z_arp(siec_prefix)
        # polaczona_lista_ip = polacz_listy_ip(adresy_ip_z_arp, hosty_ktore_odpowiedzialy)
        final_ip_list_do_przetworzenia = polacz_listy_ip(adresy_ip_z_arp, hosty_ktore_odpowiedzialy, host_ip, gateway_ip, siec_prefix)
        # --- SKANOWANIE PORTÓW (NOWY KROK) ---
        wyniki_skanowania_portow = skanuj_porty_rownolegle(final_ip_list_do_przetworzenia)
        # --- KONIEC SKANOWANIA PORTÓW ---
        nazwy_hostow_cache = pobierz_nazwy_hostow_rownolegle(final_ip_list_do_przetworzenia)

        os_cache_wyniki = zgadnij_systemy_rownolegle(final_ip_list_do_przetworzenia, wyniki_skanowania_portow)      

        # --- Dodano: Pobieranie i parsowanie ARP ---
        wynik_arp_raw = pobierz_tabele_arp() # Pobierz ARP raz
        arp_map = parsuj_tabele_arp(wynik_arp_raw, siec_prefix) if wynik_arp_raw else {}
        if not wynik_arp_raw:
             print(f"{Fore.YELLOW}Ostrzeżenie: Nie można pobrać tabeli ARP. Adresy MAC mogą być niedostępne.{Style.RESET_ALL}")
        # --- Koniec pobierania ARP ---             

        lista_urzadzen = agreguj_informacje_o_urzadzeniach(
            final_ip_list_do_przetworzenia, # Użyj finalnej listy IP
            arp_map, # Przekaż mapę ARP (powinna być pobrana wcześniej)
            nazwy_hostow_cache,
            wyniki_skanowania_portow,
            os_cache_wyniki, # Teraz ta zmienna istnieje
            baza_oui, # Przekaż bazę OUI
            host_ip,
            host_mac,
            gateway_ip,
            hosty_ktore_odpowiedzialy,
            mac_nazwy_niestandardowe,
            niestandardowe_porty_serwera_mapa
        )

        # --- WYŚWIETL LEGENDĘ KOLORÓW URZĄDZEŃ ---
        wyswietl_legende_kolorow_urzadzen()
        # --- KONIEC WYŚWIETLANIA LEGENDY KOLORÓW ---

        # --- WYŚWIETL LEGENDĘ PORTÓW (NOWY KROK) ---
        wyswietl_legende_portow(wyniki_skanowania_portow)
        # --- KONIEC WYŚWIETLANIA LEGENDY ---

        # --- WYŚWIETL LEGENDĘ SYSTEMÓW ---
        wyswietl_legende_systemow(os_cache_wyniki) # Przekaż wyniki zgadywania OS
        # --- KONIEC WYŚWIETLANIA LEGENDY ---

        # --- Wyświetlanie tabeli ---
        # Przekaż listę obiektów DeviceInfo do funkcji wyświetlającej
        wyswietl_tabele_urzadzen(
            lista_urzadzen, # Lista obiektów
            kolumny_wybrane_przez_uzytkownika # Lista wybranych kolumn
        )

        end_arp_time = time.time() # Koniec timera
        # Wyświetl czas wykonania pod tabelą
        czas_trwania_sekundy = end_arp_time - start_arp_time
        print(f"\nCałkowity czas skanowania (ping + ARP + nazwy + porty): {czas_trwania_sekundy:.2f} sekund. Czyli {przelicz_sekundy_na_minuty_sekundy(round(czas_trwania_sekundy))} min:sek")

        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"",Fore.LIGHTCYAN_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)

        # --- ZAPIS DO PLIKU HTML ---
        sciezka_do_zapisanego_html = zapisz_tabele_urzadzen_do_html(
            lista_urzadzen,
            DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA, # Przekaż domyślne kolumny do wyświetlenia
            # kolumny_wybrane_przez_uzytkownika,
            OPISY_PORTOW, # Przekaż globalny słownik opisów portów
            niestandardowe_porty_serwera_mapa, # Przekaż mapę niestandardowych portów
            siec_prefix=siec_prefix # Przekaż prefiks sieciowy
        )
        # --- KONIEC ZAPISU DO HTML ---

        # --- PYTANIE O OTWARCIE PLIKU HTML (użycie nowej funkcji) ---
        zapytaj_i_otworz_raport_html(sciezka_do_zapisanego_html)
        # --- KONIEC PYTANIA O OTWARCIE PLIKU HTML ---

        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"Skanowanie zakończone. Przewiń wyżej, aby zobaczyć wyniki.",Fore.LIGHTCYAN_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)

        sys.exit(0) # Użyj standardowego wyjścia
