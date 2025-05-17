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
from typing import List, Tuple, Optional, Dict, Any, Union, Literal
import shlex
import argparse
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

def wyczysc_wskazana_ilosc_linii_konsoli(liczba_linii: int = 1):
    """
    Czyści wskazaną liczbę linii w konsoli, przesuwając kursor w górę
    i czyszcząc każdą linię.

    Args:
        liczba_linii: Liczba linii do wyczyszczenia.
    """
    if liczba_linii <= 0:
        return

    # for _ in range(liczba_linii):
    #     # Przesuń kursor o jedną linię w górę
    #     sys.stdout.write("\033[A\033[K")
    # # Upewnij się, że zmiany są natychmiast widoczne
    # sys.stdout.flush()
    for _ in range(liczba_linii):
        # Przesuń kursor o jedną linię w górę
        sys.stdout.write("\033[A")
        # Wyczyść całą linię od kursora do końca
        sys.stdout.write("\033[K")
    # Upewnij się, że zmiany są natychmiast widoczne
    sys.stdout.flush()    

# Funkcja do obsługi przerwania przez użytkownika (Ctrl+C)
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
        # wyczysc_wskazana_ilosc_linii_konsoli()

    except Exception:
        # Ignoruj błędy podczas czyszczenia, np. jeśli strumień jest zamknięty
        pass
    # Wyświetl ujednolicony komunikat i zakończ
    print(f"\n{Fore.YELLOW}Przerwano przez użytkownika. Zakończono.{Style.RESET_ALL}\n")
    sys.exit(0) # Zakończ skrypt z kodem sukcesu (bo to intencja użytkownika)

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

def sprawdz_i_zainstaluj_biblioteke(
    nazwa_biblioteki: str,
    nazwa_importu: str,
    komunikat_ostrzezenia_specyficzny: str,
    komunikat_sukcesu_instalacji: str,
    komunikat_niepowodzenia_instalacji: str,
    komunikat_pominieto_instalacje: str
) -> bool:
    """
    Sprawdza, czy biblioteka jest dostępna. Jeśli nie, pyta użytkownika o instalację.
    Zwraca True, jeśli biblioteka jest dostępna (lub została pomyślnie zainstalowana i skrypt powinien być zrestartowany),
    False w przeciwnym razie.
    """
    try:
        __import__(nazwa_importu)
        return True # Biblioteka jest dostępna
    except ImportError:
        # Ostrzeżenia o braku biblioteki zostaną wyświetlone później,
        # jeśli użytkownik nie przerwie lub instalacja się nie powiedzie.
        try:
            prompt_text = (
                f"{Fore.YELLOW}Biblioteka '{nazwa_biblioteki}' nie jest zainstalowana. "
                f"Bez niej: {komunikat_ostrzezenia_specyficzny}\n"
                f"Czy chcesz spróbować zainstalować ją teraz? ({Fore.LIGHTMAGENTA_EX}t/N{Style.RESET_ALL}{Fore.YELLOW}{Style.RESET_ALL}"
            )
            odpowiedz = input(prompt_text).lower().strip()
            if odpowiedz.startswith('t') or odpowiedz.startswith('y'): # Tylko 't' lub 'y' inicjuje instalację             
                if zainstaluj_pakiet(nazwa_biblioteki):
                    print(komunikat_sukcesu_instalacji)
                    sys.exit(0) # Zakończ skrypt, aby użytkownik mógł go uruchomić ponownie z załadowaną biblioteką
                else:
                    # Instalacja nie powiodła się. Wyświetl pełny kontekst ostrzeżenia.
                    print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
                    print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka '{nazwa_biblioteki}' nadal nie jest zainstalowana po próbie instalacji.{Style.RESET_ALL}")
                    print(komunikat_ostrzezenia_specyficzny)
                    print(komunikat_niepowodzenia_instalacji)
                    print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
                    return False # Instalacja nie powiodła się
            else:
                # Użytkownik wybrał 'n' lub Enter. Wyświetl pełny kontekst ostrzeżenia.
                print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
                print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka '{nazwa_biblioteki}' nie jest zainstalowana.{Style.RESET_ALL}")
                print(komunikat_ostrzezenia_specyficzny)
                print(komunikat_pominieto_instalacje)
                print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
                return False # Użytkownik pominął instalację
        except (EOFError, KeyboardInterrupt):
            print(f"\n")
            obsluz_przerwanie_uzytkownika() # Wywołaj standardową obsługę przerwania
            return False 

# 1. Sprawdzanie Colorama
try:
    from colorama import Fore, Style, init
    COLORAMA_AVAILABLE = True
    init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    class DummyColorama:
        def __getattr__(self, name): return ""
    Fore = DummyColorama()
    Style = DummyColorama()
    def init(autoreset=True): pass

    # Wywołanie nowej funkcji dla Colorama
    # Ponieważ Fore i Style są już zdefiniowane jako atrapy, komunikaty będą działać
    sprawdz_i_zainstaluj_biblioteke(
        nazwa_biblioteki="colorama",
        nazwa_importu="colorama",
        komunikat_ostrzezenia_specyficzny="Kolorowanie tekstu w konsoli będzie wyłączone.",
        komunikat_sukcesu_instalacji=f"{Fore.CYAN}Instalacja 'colorama' zakończona. Uruchom skrypt ponownie, aby użyć kolorów.{Style.RESET_ALL}",
        komunikat_niepowodzenia_instalacji="Instalacja 'colorama' nie powiodła się. Kontynuowanie bez kolorów.",
        komunikat_pominieto_instalacje="Instalacja 'colorama' pominięta. Kontynuowanie bez kolorów."
    )
    # Jeśli skrypt doszedł tutaj, to znaczy, że colorama nie było i instalacja nie powiodła się lub została pominięta.
    # Atrapy Fore, Style, init są już zdefiniowane.

# 2. Sprawdzanie Psutil
# Wywołanie nowej funkcji dla Psutil
PSUTIL_AVAILABLE = sprawdz_i_zainstaluj_biblioteke(
    nazwa_biblioteki="psutil",
    nazwa_importu="psutil",
    komunikat_ostrzezenia_specyficzny=f"Nie można automatycznie wykryć interfejsów sieciowych i VPN.",
    komunikat_sukcesu_instalacji=f"{Fore.CYAN}Instalacja 'psutil' zakończona. Uruchom skrypt ponownie, aby włączyć funkcje zależne od psutil.{Style.RESET_ALL}",
    komunikat_niepowodzenia_instalacji="Instalacja 'psutil' nie powiodła się. Kontynuowanie z ograniczoną funkcjonalnością.",
    komunikat_pominieto_instalacje="Instalacja 'psutil' pominięta. Kontynuowanie z ograniczoną funkcjonalnością."
)
if PSUTIL_AVAILABLE:
    import psutil # Zaimportuj, jeśli jest dostępne

# 3. Sprawdzanie Requests
REQUESTS_AVAILABLE = sprawdz_i_zainstaluj_biblioteke(
    nazwa_biblioteki="requests",
    nazwa_importu="requests",
    komunikat_ostrzezenia_specyficzny=f"Pobieranie bazy OUI z sieci będzie niemożliwe.",
    komunikat_sukcesu_instalacji=f"{Fore.CYAN}Instalacja 'requests' zakończona. Uruchom skrypt ponownie, aby włączyć pobieranie OUI z sieci.{Style.RESET_ALL}",
    komunikat_niepowodzenia_instalacji="Instalacja 'requests' nie powiodła się. Kontynuowanie bez pobierania OUI z sieci.",
    komunikat_pominieto_instalacje="Instalacja 'requests' pominięta. Kontynuowanie bez pobierania OUI z sieci."
)
if REQUESTS_AVAILABLE:
    import requests
    from requests.adapters import HTTPAdapter
    # Sprawdź, czy Retry jest dostępne przed próbą importu z urllib3
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        class Retry: pass # Definiuj atrapę, jeśli urllib3.util.retry nie jest dostępne
else:
    # Definiuj atrapy, jeśli requests nie jest dostępne
    class Retry: pass
    class HTTPAdapter: pass

# --- Konfiguracja ---

# --- Konfiguracja Aktualizacji Skryptu ---
SKRYPT_AKTUALNA_WERSJA = "0.0.6" # Zmień na aktualną wersję Twojego skryptu
URL_INFORMACJI_O_WERSJI = "https://raw.githubusercontent.com/endiendi/skaner_sieci/main/version_info.json"

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
DOMYSLNA_NAZWA_PLIKU_HTML_BAZOWA: str = "raport_skanowania.html"
CONFIG_FILE = "config.json"
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
        "ports_all": {22, 80, 139, 445, 8000, 8001, 8080, 8096},
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

# --- Funkcje do sprawdzania i aktualizacji wersji skryptu ---
def porownaj_wersje(wersja1_str: str, wersja2_str: str) -> int:
    """
    Porównuje dwie wersje w formacie X.Y.Z.
    Zwraca:
        -1 jeśli wersja1 < wersja2
         0 jeśli wersja1 == wersja2
         1 jeśli wersja1 > wersja2
    """
    w1_parts = list(map(int, wersja1_str.split('.')))
    w2_parts = list(map(int, wersja2_str.split('.')))

    for i in range(max(len(w1_parts), len(w2_parts))):
        v1_part = w1_parts[i] if i < len(w1_parts) else 0
        v2_part = w2_parts[i] if i < len(w2_parts) else 0
        if v1_part < v2_part:
            return -1
        if v1_part > v2_part:
            return 1
    return 0

def pobierz_informacje_o_najnowszej_wersji(url: str) -> Optional[Dict[str, str]]:
    """Pobiera informacje o najnowszej wersji z podanego URL."""
    if not REQUESTS_AVAILABLE:
        print(f"{Fore.YELLOW}Informacja: Biblioteka 'requests' nie jest dostępna. Sprawdzanie aktualizacji niemożliwe.{Style.RESET_ALL}")
        return None
    # Sprawdź, czy urllib3.exceptions są dostępne, jeśli requests jest
    NameResolutionErrorType = getattr(getattr(getattr(requests.packages, 'urllib3', {}), 'exceptions', {}), 'NameResolutionError', None)
    
    try:
        print(f"\n")
        wyswietl_tekst_w_linii("-", DEFAULT_LINE_WIDTH, "Sprawdzanie dostępności nowej wersji skryptu...", Fore.CYAN, Fore.LIGHTCYAN_EX, dodaj_odstepy=False)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # print(f"{Fore.YELLOW}Nie udało się pobrać informacji o wersji: {e}{Style.RESET_ALL}")
                # Dodatkowa, bardziej szczegółowa informacja dla problemów z DNS
        is_name_resolution_error = False        
        if NameResolutionErrorType: # Sprawdź, czy typ błędu jest dostępny
            # Sprawdź, czy przyczyna błędu (często w e.args[0].reason dla ConnectionError) to NameResolutionError
            if e.args and hasattr(e.args[0], 'reason') and isinstance(e.args[0].reason, NameResolutionErrorType):
                is_name_resolution_error = True
            # Dodatkowy, mniej typowy przypadek: NameResolutionError jest bezpośrednio w e.args[0] lub w samym e
            elif e.args and isinstance(e.args[0], NameResolutionErrorType):
                is_name_resolution_error = True
            elif isinstance(e, NameResolutionErrorType):
                is_name_resolution_error = True

        if is_name_resolution_error:
            print(f"{Fore.YELLOW}Nie udało się pobrać informacji o wersji.{Style.RESET_ALL}") # Uproszczony komunikat
            print(f"{Fore.YELLOW}Przyczyna: Problem z tłumaczeniem nazwy hosta (DNS). Sprawdź połączenie internetowe i konfigurację DNS.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Nie udało się pobrać informacji o wersji: {e}{Style.RESET_ALL}") # Ogólny błąd RequestException, jeśli to nie DNS
        return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}Błąd: Nie udało się sparsować informacji o wersji (niepoprawny JSON).{Style.RESET_ALL}")
        return None

def pobierz_i_zapisz_aktualizacje(url_pobierania: str, nazwa_pliku_docelowego: str) -> bool:
    """Pobiera plik z URL i zapisuje go lokalnie."""
    if not REQUESTS_AVAILABLE:
        return False # Już sprawdzane wcześniej, ale dla pewności
    try:
        print(f"{Fore.CYAN}Pobieranie aktualizacji z: {url_pobierania}...{Style.RESET_ALL}")
        response = requests.get(url_pobierania, timeout=30, stream=True)
        response.raise_for_status()
        with open(nazwa_pliku_docelowego, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"{Fore.GREEN}Aktualizacja została pomyślnie pobrana i zapisana jako: {nazwa_pliku_docelowego}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Aby użyć nowej wersji, zastąp stary plik skryptu tym nowo pobranym i uruchom skrypt ponownie.{Style.RESET_ALL}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Błąd podczas pobierania aktualizacji: {e}{Style.RESET_ALL}")
        return False
    except IOError as e:
        print(f"{Fore.RED}Błąd podczas zapisywania aktualizacji do pliku '{nazwa_pliku_docelowego}': {e}{Style.RESET_ALL}")
        return False

def sprawdz_i_zaproponuj_aktualizacje():
    """Główna funkcja sprawdzająca wersję i proponująca aktualizację."""
    info_o_wersji = pobierz_informacje_o_najnowszej_wersji(URL_INFORMACJI_O_WERSJI)

    if info_o_wersji:
        najnowsza_wersja_str = info_o_wersji.get("latest_version")
        url_pobierania = info_o_wersji.get("download_url")
        changelog = info_o_wersji.get("changelog", "Brak informacji o zmianach.")

        if not najnowsza_wersja_str or not url_pobierania:
            print(f"{Fore.YELLOW}Ostrzeżenie: Niekompletne informacje o wersji w pliku online.{Style.RESET_ALL}")
            return

        print(f"Aktualna wersja skryptu: {SKRYPT_AKTUALNA_WERSJA}")
        print(f"Najnowsza dostępna wersja: {najnowsza_wersja_str}")

        if porownaj_wersje(SKRYPT_AKTUALNA_WERSJA, najnowsza_wersja_str) < 0:
            print(f"{Fore.GREEN}Dostępna jest nowa wersja skryptu: {najnowsza_wersja_str}!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Zmiany w nowej wersji: {changelog}{Style.RESET_ALL}")
            try:
                odpowiedz = input(f"Czy chcesz pobrać najnowszą wersję teraz? ({Fore.LIGHTMAGENTA_EX}t/N{Style.RESET_ALL}{Fore.YELLOW}): ").lower().strip()
                if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
                    nazwa_bazowa, rozszerzenie = os.path.splitext(os.path.basename(__file__))
                    nazwa_nowego_pliku = f"{nazwa_bazowa}_v{najnowsza_wersja_str.replace('.', '_')}{rozszerzenie}"
                    if pobierz_i_zapisz_aktualizacje(url_pobierania, nazwa_nowego_pliku):
                        # Można tu dodać sugestię, aby użytkownik zakończył bieżący skrypt
                        print(f"{Fore.CYAN}Możesz teraz zakończyć działanie tego skryptu ({Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL}) i uruchomić nową wersję.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Pobieranie aktualizacji nie powiodło się.{Style.RESET_ALL}")
                else:
                    print("Pobieranie aktualizacji pominięte.")
            except (EOFError, KeyboardInterrupt):
                print("\nPobieranie aktualizacji przerwane przez użytkownika.")
        else:
            print(f"{Fore.GREEN}Używasz najnowszej wersji skryptu ({SKRYPT_AKTUALNA_WERSJA}).{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Nie można było sprawdzić dostępności aktualizacji.{Style.RESET_ALL}")
    wyswietl_tekst_w_linii("-", DEFAULT_LINE_WIDTH, "", Fore.LIGHTCYAN_EX, Fore.LIGHTCYAN_EX, dodaj_odstepy=False)

# def save_config(last_prefix: str, displayed_columns: list[str], include_in_html: bool):
#     """
#     Zapisuje ostatnio użyty prefiks sieci, wybrane kolumny i flagę HTML do pliku config.json.

#     Args:
#         last_prefix (str): Ostatnio użyty prefiks sieci (np. "192.168.1.").
#         displayed_columns (list[str]): Lista nazw kolumn do wyświetlenia.
#         include_in_html (bool): Czy wybór kolumn ma być uwzględniony w raporcie HTML.

#     """
#     config_data = {
#         "last_prefix": last_prefix,
#         "displayed_columns": displayed_columns,
#         "include_in_html": include_in_html

#     }
#     try:
#         with open(CONFIG_FILE, "w", encoding="utf-8") as f:
#             json.dump(config_data, f, indent=4)
#         print(f"Konfiguracja zapisana do pliku: {CONFIG_FILE}")
#     except IOError as e:
#         print(f"Błąd podczas zapisywania konfiguracji do pliku {CONFIG_FILE}: {e}")

def load_config() -> tuple[Optional[str], Optional[List[str]], Optional[bool]]:
    """
    Odczytuje ostatnio użyty prefiks sieci i wybrane kolumny z pliku config.json.

    Returns:
        tuple[str | None, list[str] | None, bool | None]: Krotka zawierająca
        (last_prefix, displayed_columns, include_in_html).
        Zwraca (None, None, None) jeśli plik nie istnieje lub wystąpił błąd.
    """
    if not os.path.exists(CONFIG_FILE):
        return None, None, None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        last_prefix = config_data.get("last_prefix")
        displayed_columns_loaded = config_data.get("displayed_columns")
        include_in_html_loaded = config_data.get("include_in_html")

        # Podstawowa walidacja typów
        if not isinstance(last_prefix, str) and last_prefix is not None:
            print(f"Ostrzeżenie: Nieprawidłowy format 'last_prefix' w {CONFIG_FILE}. Używanie wartości domyślnej.")
            last_prefix = None
        if not isinstance(displayed_columns_loaded, list) and displayed_columns_loaded is not None:
            print(f"Ostrzeżenie: Nieprawidłowy format 'displayed_columns' w {CONFIG_FILE}. Używanie wartości domyślnej.")
            displayed_columns_loaded = None
        elif displayed_columns_loaded is not None:
            # Upewnij się, że wszystkie elementy listy są stringami
            if not all(isinstance(col, str) for col in displayed_columns_loaded):
                print(f"Ostrzeżenie: Nie wszystkie elementy w 'displayed_columns' w {CONFIG_FILE} są tekstowe. Używanie wartości domyślnej.")
                displayed_columns_loaded = None
        if not isinstance(include_in_html_loaded, bool) and include_in_html_loaded is not None:
             print(f"Ostrzeżenie: Nieprawidłowy format 'include_in_html' w {CONFIG_FILE}. Używanie wartości domyślnej.")
             include_in_html_loaded = None

        return last_prefix, displayed_columns_loaded, include_in_html_loaded
    except json.JSONDecodeError:
        print(f"Błąd podczas odczytu pliku konfiguracyjnego {CONFIG_FILE}. Plik może być uszkodzony.")
        return None, None, None
    except IOError as e:
        print(f"Błąd podczas otwierania pliku konfiguracyjnego {CONFIG_FILE}: {e}")
        return None, None, None
    except Exception as e:
        print(f"Nieoczekiwany błąd podczas ładowania konfiguracji z {CONFIG_FILE}: {e}")
        return None, None, None


def pobierz_prefixy_zdalne_vpn(nazwa_interfejsu_vpn: str) -> List[str]:
    """
    Pobiera listę prefiksów sieciowych (CIDR) routowanych przez podany interfejs VPN.
    """
    system = platform.system().lower()
    prefixes: List[str] = []
    encoding = DEFAULT_ENCODING

    # print(f"{Fore.CYAN}Analiza tablicy routingu dla interfejsu VPN: {nazwa_interfejsu_vpn}...{Style.RESET_ALL}")

    try:
        if system == "linux":
            cmd = ["ip", "-4", "route", "show", "dev", nazwa_interfejsu_vpn]
            encoding = 'utf-8'
            process = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore', check=False) # check=False as it might return non-zero if no routes
            if process.returncode == 0 and process.stdout:
                for line in process.stdout.splitlines():
                    line = line.strip()
                    parts = line.split()
                    if not parts:
                        continue
                    
                    potential_prefix = parts[0]
                    if potential_prefix == "default":
                        prefixes.append("0.0.0.0/0")
                    elif '/' in potential_prefix:
                        try:
                            ipaddress.ip_network(potential_prefix, strict=False)
                            prefixes.append(potential_prefix)
                        except ValueError:
                            pass
            elif process.stderr:
                 print(f"{Fore.YELLOW}Błąd lub brak tras dla interfejsu {nazwa_interfejsu_vpn} (Linux): {process.stderr.strip()}{Style.RESET_ALL}")

        elif system == "windows":
            vpn_interface_ips: List[str] = []
            if PSUTIL_AVAILABLE:
                try:
                    all_addrs = psutil.net_if_addrs()
                    if nazwa_interfejsu_vpn in all_addrs:
                        for snic in all_addrs[nazwa_interfejsu_vpn]:
                            if snic.family == socket.AF_INET:
                                vpn_interface_ips.append(snic.address)
                except Exception as e_psutil:
                    print(f"{Fore.YELLOW}Nie udało się pobrać IP dla interfejsu {nazwa_interfejsu_vpn} używając psutil: {e_psutil}{Style.RESET_ALL}")
            
            if not vpn_interface_ips:
                print(f"{Fore.YELLOW}Nie można ustalić adresu IP dla interfejsu VPN '{nazwa_interfejsu_vpn}' w systemie Windows. Pomijanie analizy tras.{Style.RESET_ALL}")
                return []

            cmd = ["route", "print"]
            encoding = WINDOWS_OEM_ENCODING
            process = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore', check=True)
            
            active_routes_section = False
            for line in process.stdout.splitlines():
                line_lower = line.lower()
                if "active routes:" in line_lower or "trasy aktywne:" in line_lower:
                    active_routes_section = True
                    continue
                if "persistent routes:" in line_lower or "trasy trwałe:" in line_lower:
                    active_routes_section = False 
                    break
                
                if active_routes_section and line.strip() and not line.startswith("="):
                    parts = line.split()
                    if len(parts) >= 4: 
                        network_dest = parts[0]
                        netmask = parts[1]
                        interface_ip_in_route = parts[3]

                        if interface_ip_in_route in vpn_interface_ips:
                            try:
                                network = ipaddress.ip_network(f"{network_dest}/{netmask}", strict=False)
                                prefixes.append(str(network))
                            except ValueError:
                                pass
        
        elif system == "darwin": 
            cmd = ["netstat", "-nr"]
            encoding = 'utf-8'
            process = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='ignore', check=True)
            routing_table_header_found = False
            for line in process.stdout.splitlines():
                line = line.strip()
                if not routing_table_header_found:
                    if "Routing tables" in line or ("Destination" in line and "Gateway" in line and "Netif" in line):
                         routing_table_header_found = True
                    continue
                if not line or "Expire" in line : 
                    continue
                parts = line.split()
                if len(parts) >= 4 and parts[-1] == nazwa_interfejsu_vpn: 
                    destination = parts[0]
                    if destination == "default":
                        prefixes.append("0.0.0.0/0")
                    else:
                        try:
                            network = ipaddress.ip_network(destination, strict=False)
                            prefixes.append(str(network))
                        except ValueError:
                            pass
        else:
            print(f"{Fore.YELLOW}Pobieranie tras dla VPN nie jest jeszcze zaimplementowane dla systemu: {system}{Style.RESET_ALL}")
            return []

    except FileNotFoundError:
        print(f"{Fore.RED}Błąd: Polecenie do wyświetlenia tablicy routingu nie znalezione.{Style.RESET_ALL}")
        return []
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Błąd podczas wykonywania polecenia dla tablicy routingu: {e}{Style.RESET_ALL}")
        return []
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas pobierania tras VPN: {e}{Style.RESET_ALL}")
        return []

    unique_prefixes = sorted(list(set(prefixes)))
    # if unique_prefixes: # ZAKOMENTOWANE
        # print(f"{Fore.GREEN}Wykryte prefiksy sieciowe routowane przez {nazwa_interfejsu_vpn}: {', '.join(unique_prefixes)}{Style.RESET_ALL}") # ZAKOMENTOWANE
    if not unique_prefixes: # Zmieniono warunek, aby wyświetlać tylko jeśli nie znaleziono nic
        print(f"{Fore.YELLOW}Nie znaleziono specyficznych tras dla interfejsu {nazwa_interfejsu_vpn} lub wystąpił błąd.{Style.RESET_ALL}")
    
    return unique_prefixes

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

    # green_color = Fore.GREEN if COLORAMA_AVAILABLE else ""
    # yellow_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
    # red_color = Fore.RED if COLORAMA_AVAILABLE else ""
    # reset_color = Style.RESET_ALL if COLORAMA_AVAILABLE else ""
    # Użyj kolorów bezpośrednio, będą atrapy jeśli colorama niedostępna
    green_color, yellow_color, red_color, reset_color = Fore.GREEN, Fore.YELLOW, Fore.RED, Style.RESET_ALL

    if not os.path.exists(pelna_sciezka_pliku):
        try:
            with open(pelna_sciezka_pliku, "w", encoding="utf-8") as f:
                if przykladowa_tresc:
                    f.write(przykladowa_tresc)
            print(f"{green_color}Plik '{nazwa_pliku}' został pomyślnie utworzony w '{script_dir}'.{reset_color}")
            if przykladowa_tresc:
                print(f"{green_color}Dodano przykładową treść.{reset_color}")
        except IOError as e:
            print(f"{red_color}Nieoczekiwany błąd podczas tworzenia pliku '{nazwa_pliku}': {e}{reset_color}", end="\n")
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


def _przetworz_wybor_menu_z_linii_polecen(
    cmd_menu_choice: Optional[str],
    klucze_kolumn_do_wyboru_rzeczywiste: List[str],
    numer_opcji_html: int
) -> Optional[List[int]]:
    """
    Przetwarza wybór opcji menu podany jako parametr linii poleceń (-m).
    Logika:
    - Jeśli -m 0: Zaznacza wszystkie kolumny (1 do N), opcja HTML jest nieaktywna.
    - Dla innych cyfr w -m:
        - Kolumny: Numery podane w -m są WYKLUCZANE (pozostałe są aktywne).
        - Opcja HTML: Jest AKTYWOWANA, jeśli jej numer jest podany w -m (inaczej nieaktywna).

    Args:
        cmd_menu_choice: String z wyborem z linii poleceń.
        klucze_kolumn_do_wyboru_rzeczywiste: Lista kluczy kolumn dostępnych do wyboru.
        numer_opcji_html: Numer opcji HTML.

    Returns:
        Lista numerów opcji (int), które mają być AKTYWNE, jeśli parsowanie
        się powiodło. Zwraca None, jeśli cmd_menu_choice nie został podany.
        Zwraca pustą listę, jeśli cmd_menu_choice był nieprawidłowy.
    """
    if not cmd_menu_choice:
        return None # Brak parametru -m, menu interaktywne zostanie użyte

    # Specjalna obsługa dla -m 0
    if cmd_menu_choice == "0":
        # print(f"{Fore.CYAN}Parametr -m 0: Zaznaczanie wszystkich dostępnych kolumn (bez opcji HTML).{Style.RESET_ALL}")
        wszystkie_numery_kolumn = list(range(1, len(klucze_kolumn_do_wyboru_rzeczywiste) + 1))
        return sorted(wszystkie_numery_kolumn)

    print(f"{Fore.CYAN}Próba przetworzenia wyboru kolumn z linii poleceń: -m {cmd_menu_choice}{Style.RESET_ALL}")
    
    numery_wskazane_przez_uzytkownika_set: set[int] = set()
    is_input_format_valid = False 

    if cmd_menu_choice.isdigit():
        is_input_format_valid = True 
        for cyfra_str in cmd_menu_choice:
            try:
                numer_wskazany = int(cyfra_str)
                if (1 <= numer_wskazany <= len(klucze_kolumn_do_wyboru_rzeczywiste)) or \
                   (numer_wskazany == numer_opcji_html):
                    numery_wskazane_przez_uzytkownika_set.add(numer_wskazany)
                else:
                    print(f"{Fore.YELLOW}Ostrzeżenie: Numer opcji '{cyfra_str}' w parametrze -m jest poza zakresem. Pomijanie tej cyfry.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.YELLOW}Ostrzeżenie: Nieprawidłowy znak '{cyfra_str}' w parametrze -m. Cały parametr -m zostanie zignorowany.{Style.RESET_ALL}")
                is_input_format_valid = False 
                break 
        
        if not is_input_format_valid:
            print(f"{Fore.YELLOW}Parametr -m '{cmd_menu_choice}' zawierał nieprawidłowe znaki.{Style.RESET_ALL}")
            return [] 

    else: 
        print(f"{Fore.YELLOW}Nieprawidłowy format parametru -m '{cmd_menu_choice}' (oczekiwano tylko cyfr, lub '0').{Style.RESET_ALL}")
        return [] 

    if is_input_format_valid and not numery_wskazane_przez_uzytkownika_set and cmd_menu_choice:
        print(f"{Fore.YELLOW}Parametr -m '{cmd_menu_choice}' nie zawierał żadnych prawidłowych numerów opcji.{Style.RESET_ALL}")
        return [] 

    aktywne_opcje_finalne_set: set[int] = set()

    # Logika dla kolumn: aktywne, jeśli NIE ma ich w parametrze -m
    for i in range(1, len(klucze_kolumn_do_wyboru_rzeczywiste) + 1):
        if i not in numery_wskazane_przez_uzytkownika_set:
            aktywne_opcje_finalne_set.add(i)

    # Logika dla opcji HTML: aktywna, jeśli JEJ numer JEST w parametrze -m
    if numer_opcji_html in numery_wskazane_przez_uzytkownika_set:
        aktywne_opcje_finalne_set.add(numer_opcji_html)
    
    return sorted(list(aktywne_opcje_finalne_set))


def wybierz_kolumny_do_wyswietlenia_menu(
    wszystkie_kolumny: Dict[str, Dict[str, Any]] = KOLUMNY_TABELI,
    domyslne_kolumny_keys: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA,
    loaded_selected_column_keys: Optional[List[str]] = None,
    loaded_include_in_html: Optional[bool] = None
) -> List[int]: # Funkcja zwraca listę numerów
    """
    Pozwala użytkownikowi interaktywnie wybrać kolumny do wyświetlenia w tabeli
    oraz czy uwzględnić ten wybór w raporcie HTML jako jedną z opcji.
    Zwraca listę numerów (1-based) wszystkich wybranych opcji.
    Używa wczytanej konfiguracji jako stanu początkowego, jeśli jest dostępna.

    Args:
        wszystkie_kolumny: Słownik definicji wszystkich dostępnych kolumn.
        domyslne_kolumny_keys: Lista kluczy kolumn wybranych domyślnie (dla opcji 'd').
        loaded_selected_column_keys: Wczytana lista kluczy wybranych kolumn.
        loaded_include_in_html: Wczytany stan opcji HTML.

    Returns:
        Lista numerów (1-based) wybranych opcji (kolumn oraz opcji HTML).
    """
    # Pobierz klucze w oryginalnej kolejności
    oryginalne_klucze = list(wszystkie_kolumny.keys())
    # Klucze dostępne do wyboru przez użytkownika (bez 'lp')
    klucze_do_wyboru_rzeczywiste = [k for k in oryginalne_klucze if k != 'lp']
    
    # Inicjalizacja stanu na podstawie wczytanej konfiguracji lub domyślnych
    if loaded_selected_column_keys is not None:
        wybrane_numery_kolumn_rzeczywistych = []
        for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
            if key_in_choosable in loaded_selected_column_keys:
                wybrane_numery_kolumn_rzeczywistych.append(i + 1)
    else: # Fallback na domyślne kolumny, jeśli nic nie wczytano
        wybrane_numery_kolumn_rzeczywistych = []
        domyslne_klucze_bez_lp_local = [k for k in domyslne_kolumny_keys if k != 'lp']
        for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
            if key_in_choosable in domyslne_klucze_bez_lp_local:
                wybrane_numery_kolumn_rzeczywistych.append(i + 1)

    if loaded_include_in_html is not None:
        uwzglednij_w_html_selected = loaded_include_in_html
    else: # Domyślny stan dla opcji HTML, jeśli nic nie wczytano
        uwzglednij_w_html_selected = True # Domyślnie zaznaczona
    # Numer opcji HTML będzie następnym numerem po rzeczywistych kolumnach
    numer_opcji_html = len(klucze_do_wyboru_rzeczywiste) + 1
    tekst_opcji_html = "Uwzględnić wybór w raporcie HTML"

    while True:
        print("\n" + "-" * 80)
        print(f"Wybierz kolumny do wyświetlenia i czy uwzględznić wybór w raporcie html")
        print("-" * 80)
        
        # Wyświetlaj rzeczywiste kolumny
        for i, klucz in enumerate(klucze_do_wyboru_rzeczywiste):
            numer_biezacej_kolumny = i + 1
            znacznik = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if numer_biezacej_kolumny in wybrane_numery_kolumn_rzeczywistych else f"{Fore.RED}[ ]{Style.RESET_ALL}"
            naglowek = wszystkie_kolumny[klucz]['naglowek']
            print(f"  {znacznik} {numer_biezacej_kolumny}. {naglowek} ({klucz})")
        
        # Dodaj opcję HTML na końcu listy
        znacznik_html = f"{Fore.GREEN}[X]{Style.RESET_ALL}" if uwzglednij_w_html_selected else f"{Fore.RED}[ ]{Style.RESET_ALL}"
        print("-" * 80)
        print(f"  {znacznik_html} {numer_opcji_html}. {tekst_opcji_html}")
        
        liczba_wyswietlonych_opcji_wszystkich = len(klucze_do_wyboru_rzeczywiste) + 1 # +1 dla opcji HTML
        print("-" * 80)
        print(f"Opcje: Wpisz {Fore.LIGHTMAGENTA_EX}numer(y){Style.RESET_ALL} opcji, aby je przełączyć (np. 2{numer_opcji_html}).")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}a{Style.RESET_ALL}', aby zaznaczyć/odznaczyć wszystkie opcje.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}d{Style.RESET_ALL}', aby przywrócić domyślne ustawienia.")
        print(f"       Wpisz '{Fore.LIGHTMAGENTA_EX}q{Style.RESET_ALL}' lub naciśnij {Fore.LIGHTMAGENTA_EX}Enter{Style.RESET_ALL}, aby zatwierdzić wybór.")
        print("-" * 80)

        try:
            wybor = input("Twój wybór: ").lower().strip()

            if not wybor or wybor == 'q':
                liczba_linii_do_wyczyszczenia = liczba_wyswietlonych_opcji_wszystkich + 11
                wyczysc_wskazana_ilosc_linii_konsoli(liczba_linii_do_wyczyszczenia)

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
                    if key_in_choosable in [k for k in domyslne_kolumny_keys if k != 'lp']: # Użyj przekazanych domyślnych
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

            liczba_linii_do_wyczyszczenia = liczba_wyswietlonych_opcji_wszystkich + 12
            wyczysc_wskazana_ilosc_linii_konsoli(liczba_linii_do_wyczyszczenia)

        except (EOFError, KeyboardInterrupt):
            obsluz_przerwanie_uzytkownika()
        except Exception as e:
             print(f"\n{Fore.RED}Błąd podczas przetwarzania wyboru: {e}{Style.RESET_ALL}")
             # W razie błędu, bezpieczniej wrócić do domyślnych
             print("Przywracanie domyślnych ustawień.")
             wybrane_numery_kolumn_rzeczywistych.clear()
             for i, key_in_choosable in enumerate(klucze_do_wyboru_rzeczywiste):
                 if key_in_choosable in [k for k in domyslne_kolumny_keys if k != 'lp']:
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
    domyslne_kolumny_dla_menu: List[str] = DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA,
    cmd_menu_choice: Optional[str] = None,
    loaded_selected_column_keys: Optional[List[str]] = None,
    loaded_include_in_html: Optional[bool] = None
) -> Tuple[List[str], bool]:
    """
    Wyświetla menu wyboru kolumn i opcji HTML, a następnie tłumaczy
    numeryczny wybór użytkownika na listę kluczy kolumn i flagę HTML.

    Args:
        wszystkie_kolumny_map: Słownik definicji wszystkich dostępnych kolumn.
        domyslne_kolumny_dla_menu: Lista kluczy kolumn, które będą domyślnie
                                   zaznaczone w menu.
        cmd_menu_choice: Opcjonalny string z wyborem z linii poleceń (np. "17").
        loaded_selected_column_keys: Wczytana lista kluczy wybranych kolumn.
        loaded_include_in_html: Wczytany stan opcji HTML.


    Returns:
        Krotka: (Lista kluczy wybranych kolumn do wyświetlenia,
                   wartość boolowska dla opcji "Uwzględnić wybór w raporcie HTML").
    """
    # Usunięto pierwsze, niepotrzebne wywołanie wybierz_kolumny_do_wyswietlenia_menu
    oryginalne_klucze_wszystkich_kolumn = list(wszystkie_kolumny_map.keys())
    klucze_kolumn_do_wyboru_rzeczywiste = [k for k in oryginalne_klucze_wszystkich_kolumn if k != 'lp']

    numer_opcji_html = len(klucze_kolumn_do_wyboru_rzeczywiste) + 1

    wybrane_numery_opcji_z_cmd = _przetworz_wybor_menu_z_linii_polecen(
        cmd_menu_choice,
        klucze_kolumn_do_wyboru_rzeczywiste,
        numer_opcji_html
    )

    wybrane_numery_opcji: List[int] # Inicjalizacja typu dla pewności, zostanie nadpisana poniżej

    if wybrane_numery_opcji_z_cmd: # Jeśli lista nie jest pusta (wybór z linii poleceń był poprawny)
        print(f"{Fore.GREEN}Zastosowano wybór kolumn z linii poleceń. Wybrane numery opcji: {wybrane_numery_opcji_z_cmd}{Style.RESET_ALL}\n")
        wybrane_numery_opcji = wybrane_numery_opcji_z_cmd
    else: # Wybór z linii poleceń nie był użyty, był niepoprawny lub pusty
        if cmd_menu_choice is not None and not wybrane_numery_opcji_z_cmd:
            # Komunikat, jeśli -m było podane, ale nie dało prawidłowych opcji
            print(f"{Fore.YELLOW}Parametr -m '{cmd_menu_choice}' nie zawierał prawidłowych opcji lub był nieprawidłowy. Uruchamianie interaktywnego menu wyboru kolumn...{Style.RESET_ALL}")
        # W przeciwnym razie (cmd_menu_choice był None), menu po prostu się pojawi
        # Użyj wczytanej konfiguracji (jeśli jest) jako stanu początkowego menu
        wybrane_numery_opcji = wybierz_kolumny_do_wyswietlenia_menu(
            wszystkie_kolumny_map,
            domyslne_kolumny_dla_menu, # Domyślne dla opcji 'd'
            loaded_selected_column_keys, # Wczytane do inicjalizacji
            loaded_include_in_html       # Wczytane do inicjalizacji
        )

    finalnie_wybrane_klucze_kolumn_temp: List[str] = []
    uwzglednij_w_html_wybrane = False

    # Upewnijmy się, że iterujemy po liście, nawet jeśli jest pusta
    iterowalne_numery_opcji = wybrane_numery_opcji if wybrane_numery_opcji is not None else []

    for numer_opcji in iterowalne_numery_opcji:
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

def czy_aktywny_vpn_lub_podobny() -> Optional[str]: # Zmieniono typ zwracany na Optional[str]
    """
    Sprawdza, czy istnieje interfejs VPN, który jest UP i zwraca jego nazwę.
    Priorytetyzuje:
    1. Interfejsy UP z adresem IP w zakresie CGNAT (100.64.0.0/10).
    2. Interfejsy UP z nazwami 'tun', 'tap', 'wg', 'open' ORAZ posiadające adres IPv4.
    3. Interfejsy UP z nazwą 'tailscale' ORAZ posiadające adres IPv4.
    Zwraca nazwę interfejsu jeśli znaleziono AKTYWNY VPN, lub nazwę z dopiskiem (potencjalny)
    jeśli interfejs pasuje z nazwy ale nie ma "ważnego" IP. Zwraca None jeśli nic nie znaleziono.
    Wymaga biblioteki psutil.
    """
    if not PSUTIL_AVAILABLE:
        return None # Zmieniono z False na None

    tailscale_network = ipaddress.ip_network('100.64.0.0/10')
    primary_vpn_prefixes: List[str] = ['tun', 'tap', 'wg', 'open']
    tailscale_prefix: str = 'tailscale'

    try:
        interfaces_addrs = psutil.net_if_addrs()
        interfaces_stats = psutil.net_if_stats()

        # Kandydaci, posortowani wg priorytetu
        found_by_ip: Optional[str] = None
        found_by_primary_name_with_ip: Optional[str] = None
        found_by_tailscale_name_with_ip: Optional[str] = None
        found_by_primary_name_only: Optional[str] = None
        found_by_tailscale_name_only: Optional[str] = None

        for if_name, stats in interfaces_stats.items():
            if stats.isup:
                if_name_lower = if_name.lower()
                has_valid_ipv4 = False # Czy interfejs ma jakikolwiek "sensowny" adres IPv4

                if if_name in interfaces_addrs:
                    snic_list = interfaces_addrs[if_name]
                    for snic in snic_list:
                        if snic.family == socket.AF_INET:
                            try:
                                ip_addr_obj = ipaddress.ip_address(snic.address)
                                # 1. Priorytet: Adres IP w zakresie CGNAT (często używane przez VPNy jak Tailscale)
                                if ip_addr_obj in tailscale_network: # Poprawiono 'ip_addr' na 'ip_addr_obj'
                                    found_by_ip = if_name # Najwyższy priorytet
                                    has_valid_ipv4 = True
                                    break # Mamy kandydata z tego interfejsu
                                # Sprawdź, czy to nie loopback/link-local, aby uznać za "ważny" IP
                                if not ip_addr_obj.is_loopback and not ip_addr_obj.is_link_local:
                                    has_valid_ipv4 = True
                            except ValueError:
                                continue # Niepoprawny adres IP, ignoruj
                    if found_by_ip: continue # Jeśli znaleziono przez IP, przejdź do następnego interfejsu

                # 2. Priorytet: Nazwy typowe dla VPN (tun, tap, wg, open) Z adresem IP
                name_matches_primary = any(if_name_lower.startswith(p) for p in primary_vpn_prefixes)
                if name_matches_primary:
                    if has_valid_ipv4:
                        if not found_by_primary_name_with_ip: found_by_primary_name_with_ip = if_name
                    else: # Bez "ważnego" IP
                        if not found_by_primary_name_only: found_by_primary_name_only = if_name
                    # Jeśli to nie Tailscale, a pasuje do primary, to już go obsłużyliśmy
                    if not if_name_lower.startswith(tailscale_prefix):
                        continue

                # 3. Priorytet: Nazwa 'tailscale' Z adresem IP
                if if_name_lower.startswith(tailscale_prefix):
                    if has_valid_ipv4:
                         if not found_by_tailscale_name_with_ip:
                             found_by_tailscale_name_with_ip = if_name
                    else:
                         if not found_by_tailscale_name_only:
                             found_by_tailscale_name_only = if_name
        # Decyzja na podstawie zebranych kandydatów i priorytetów
        if found_by_ip:
            # wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN (CGNAT) wg adresu IP: {found_by_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            return found_by_ip
        elif found_by_primary_name_with_ip:
            # wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN wg nazwy (główny z IP): {found_by_primary_name_with_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            return found_by_primary_name_with_ip
        elif found_by_tailscale_name_with_ip:
            # wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto AKTYWNY interfejs VPN wg nazwy (Tailscale z IP): {found_by_tailscale_name_with_ip}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            return found_by_tailscale_name_with_ip
        elif found_by_primary_name_only:
            # wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto potencjalny interfejs VPN wg nazwy (główny, może nie być połączony): {found_by_primary_name_only}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            return f"{found_by_primary_name_only} (potencjalny)" # Zwróć nazwę z adnotacją
        elif found_by_tailscale_name_only:
            # wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto potencjalny interfejs VPN (Tailscale, może nie być połączony): {found_by_tailscale_name_only}",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            return f"{found_by_tailscale_name_only} (potencjalny)" # Zwróć nazwę z adnotacją
        else:
            return None

    except Exception as e:
        print(f"{Fore.YELLOW}Ostrzeżenie: Wystąpił błąd podczas sprawdzania interfejsów sieciowych dla VPN: {e}{Style.RESET_ALL}")
        return None



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

def zintegruj_niestandardowe_porty_z_opisami(
    standardowe_opisy: Dict[int, str],
    niestandardowe_mapa: Dict[str, Dict[int, Optional[str]]]
) -> None:
    """
    Integruje niestandardowe porty z pliku port_serwer.txt z globalnym słownikiem OPISY_PORTOW.
    Jeśli port niestandardowy nie istnieje w OPISY_PORTOW, zostanie dodany z domyślnym opisem.
    Nie nadpisuje istniejących opisów dla portów standardowych.

    Args:
        standardowe_opisy: Globalny słownik OPISY_PORTOW (modyfikowany w miejscu).
        niestandardowe_mapa: Słownik wczytany z pliku port_serwer.txt.
    """
    liczba_nowo_dodanych_portow = 0
    liczba_nadpisanych_opisow = 0

    for typ_protokolu, porty_z_opisami in niestandardowe_mapa.items():
        for port, opis_z_pliku in porty_z_opisami.items():
            if opis_z_pliku:  # Jeśli plik dostarcza opis
                # Sprawdź, czy port istnieje i czy opis jest inny, aby policzyć nadpisania
                if port in standardowe_opisy and standardowe_opisy[port] != opis_z_pliku:
                    liczba_nadpisanych_opisow += 1
                elif port not in standardowe_opisy: # Jeśli portu nie było, to jest nowy
                    liczba_nowo_dodanych_portow += 1
                standardowe_opisy[port] = opis_z_pliku  # Nadpisz lub dodaj z opisem z pliku
            else:  # Jeśli plik NIE dostarcza opisu (opis_z_pliku is None)
                if port not in standardowe_opisy:  # A portu nie ma w standardowych

                    standardowe_opisy[port] = f"Niestandardowy {typ_protokolu.upper()} (z pliku port_serwer.txt)"
                    liczba_nowo_dodanych_portow += 1
                # Jeśli port jest w standardowych, a plik nie ma opisu, nic nie rób - zachowaj standardowy opis
    
    if liczba_nowo_dodanych_portow > 0:
        print(f"{Fore.CYAN}Dodano {liczba_nowo_dodanych_portow} nowych portów do globalnej listy skanowania (z pliku port_serwer.txt).{Style.RESET_ALL}")
    if liczba_nadpisanych_opisow > 0:
        print(f"{Fore.GREEN}Nadpisano opisy dla {liczba_nadpisanych_opisow} istniejących portów na podstawie pliku port_serwer.txt.{Style.RESET_ALL}")
    
    # Opcjonalny komunikat, jeśli plik został przetworzony, ale nic się nie zmieniło
    if liczba_nowo_dodanych_portow == 0 and liczba_nadpisanych_opisow == 0 and any(niestandardowe_mapa.values()):
        print(f"{Fore.CYAN}Przetworzono plik port_serwer.txt, ale nie dodano nowych portów ani nie nadpisano istniejących opisów (mogą być już zgodne).{Style.RESET_ALL}")
    # OPISY_PORTOW są modyfikowane w miejscu, więc nie trzeba nic zwracać.


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

    print(f"\nSkanowanie wybranych portów dla {len(ips_do_skanowania)} aktywnych hostów (w tym niestandardowych z pliku)...")
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

def is_valid_prefix_format(prefix_str: str) -> bool:
    """Sprawdza, czy ciąg jest poprawnym prefiksem sieciowym (np. 192.168.0.)."""
    if re.match(r"^(\d{1,3}\.){3}$", prefix_str):
        parts = prefix_str.split('.')[:-1] # Pobierz trzy oktety
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    return False

def is_full_ip_address(ip_str: str) -> bool:
    """Sprawdza, czy ciąg jest pełnym, poprawnym adresem IPv4."""
    try:
        ipaddress.ip_address(ip_str) # Podstawowa walidacja przez ipaddress
        # Pełny adres IP powinien mieć 3 kropki i nie kończyć się kropką
        return ip_str.count('.') == 3 and not ip_str.endswith('.')
    except ValueError:
        return False

def get_prefix_from_ip(ip_str: str) -> Optional[str]:
    """Wyodrębnia prefiks sieciowy (np. 192.168.0.) z pełnego adresu IP."""
    try:
        if is_full_ip_address(ip_str): # Upewnij się, że to pełny IP
            return ".".join(ip_str.split('.')[:3]) + "."
    except ValueError: # ip_str.split może zawieść jeśli ip_str nie jest stringiem
        pass
    return None

def pobierz_i_zweryfikuj_prefiks(cmd_prefix: Optional[str] = None) -> Optional[str]:
    """
    Pobiera prefiks sieciowy. Jeśli zostanie wykryty automatycznie,
    prosi użytkownika o potwierdzenie lub podanie innego.
    W przeciwnym razie prosi o ręczne wprowadzenie.
    Czyści linię promptu po poprawnym wyborze.
    
    Args:
        cmd_prefix: Opcjonalny prefiks sieciowy podany z linii poleceń.
    """

    potwierdzony_prefiks: Optional[str] = None

    # --- 1. Obsługa prefiksu z linii poleceń ---
    if cmd_prefix:
        cmd_prefix_stripped = cmd_prefix.strip()

        # Scenariusz 1.1: cmd_prefix to pełny adres IP (np. 192.168.0.142)
        if is_full_ip_address(cmd_prefix_stripped):
            extracted_prefix = get_prefix_from_ip(cmd_prefix_stripped)
            if extracted_prefix:
                print(f"{Fore.CYAN}Podano pełny adres IP '{cmd_prefix_stripped}' jako argument -p.{Style.RESET_ALL}")
                try:
                    prompt_text = f"Czy chcesz skanować sieć z prefiksem '{extracted_prefix}'? ({Fore.LIGHTMAGENTA_EX}T/n{Style.RESET_ALL}): "
                    odp = input(prompt_text).lower().strip()
                    wyczysc_wskazana_ilosc_linii_konsoli()
                    if not odp or odp.startswith('t') or odp.startswith('y'):
                        potwierdzony_prefiks = extracted_prefix
                        print(f"{Fore.GREEN}Używany prefiks sieciowy: {potwierdzony_prefiks}{Style.RESET_ALL}")
                        return potwierdzony_prefiks
                    else:
                        print(f"{Fore.YELLOW}Skanowanie z prefiksem '{extracted_prefix}' odrzucone. Przechodzenie do trybu interaktywnego.{Style.RESET_ALL}")
                        cmd_prefix = None # Wymuś tryb interaktywny
                except (EOFError, KeyboardInterrupt):
                    obsluz_przerwanie_uzytkownika() # Obsługuje wyjście
            else: # Nie powinno się zdarzyć, jeśli is_full_ip_address było prawdziwe
                print(f"{Fore.YELLOW}Ostrzeżenie: Nie udało się wyekstrahować prefiksu z '{cmd_prefix_stripped}'. Przechodzenie do trybu interaktywnego.{Style.RESET_ALL}")
                cmd_prefix = None
        
        # Scenariusz 1.2: cmd_prefix to już prefiks (np. 192.168.0.) lub jest nieprawidłowy
        elif cmd_prefix: # Sprawdź ponownie, bo mogło zostać ustawione na None powyżej
            prefiks_do_walidacji_cmd = cmd_prefix_stripped
            if not prefiks_do_walidacji_cmd.endswith("."):
                prefiks_do_walidacji_cmd += "."
            
            if is_valid_prefix_format(prefiks_do_walidacji_cmd):
                potwierdzony_prefiks = prefiks_do_walidacji_cmd
                print(f"{Fore.GREEN}Używany prefiks sieciowy z linii poleceń: {potwierdzony_prefiks}{Style.RESET_ALL}")
                return potwierdzony_prefiks
            else:
                print(f"{Fore.YELLOW}Ostrzeżenie: Prefiks z linii poleceń '{cmd_prefix}' ma niepoprawny format. Przechodzenie do trybu interaktywnego.{Style.RESET_ALL}")
                cmd_prefix = None # Upewnij się, że przechodzimy do trybu interaktywnego, jeśli cmd_prefix był nieprawidłowy

    # --- 2. Automatyczne wykrywanie i/lub tryb interaktywny ---
    # Ta część uruchamia się, jeśli cmd_prefix nie został podany, był nieprawidłowy,
    # lub użytkownik odrzucił wyekstrahowany prefiks z pełnego IP podanego w cmd_prefix

    siec_prefix_automatyczny = pobierz_prefiks_sieciowy()

    if siec_prefix_automatyczny:
        print(f"Wykryty automatycznie prefiks sieciowy: '{siec_prefix_automatyczny}'.")
        while potwierdzony_prefiks is None:
            try:
                prompt_text = f"Potwierdź {Fore.LIGHTMAGENTA_EX}[Enter]{Style.RESET_ALL}, podaj inny prefiks/IP lub {Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL} aby zakończyć: "
                odpowiedz_uzytkownika = input(prompt_text).strip()
                wyczysc_wskazana_ilosc_linii_konsoli()
                if not odpowiedz_uzytkownika: # Użytkownik nacisnął Enter
                    potwierdzony_prefiks = siec_prefix_automatyczny
                    print(f"{Fore.GREEN}Używany prefiks sieciowy: {potwierdzony_prefiks}{Style.RESET_ALL}")
                    break
                
                # Sprawdź, czy użytkownik podał pełny adres IP
                if is_full_ip_address(odpowiedz_uzytkownika):
                    extracted_prefix = get_prefix_from_ip(odpowiedz_uzytkownika)
                    if extracted_prefix:
                        print(f"{Fore.CYAN}Podano pełny adres IP '{odpowiedz_uzytkownika}'.{Style.RESET_ALL}")
                        try:
                            prompt_confirm_ip = f"Czy chcesz skanować sieć z prefiksem '{extracted_prefix}'? ({Fore.LIGHTMAGENTA_EX}T/n{Style.RESET_ALL}): "
                            odp_confirm = input(prompt_confirm_ip).lower().strip()
                            wyczysc_wskazana_ilosc_linii_konsoli()
                            if not odp_confirm or odp_confirm.startswith('t') or odp_confirm.startswith('y'):
                                potwierdzony_prefiks = extracted_prefix
                                print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                                break
                            else:
                                print(f"{Fore.YELLOW}Skanowanie z prefiksem '{extracted_prefix}' odrzucone. Spróbuj ponownie podać prefiks lub IP.{Style.RESET_ALL}")
                                continue # Wróć do promptu
                        except (EOFError, KeyboardInterrupt):
                            obsluz_przerwanie_uzytkownika()
                    else:
                        print(f"{Fore.YELLOW}Nie udało się wyekstrahować prefiksu z '{odpowiedz_uzytkownika}'. Spróbuj ponownie.{Style.RESET_ALL}")
                        continue
                else: # Użytkownik podał coś innego, spróbuj zwalidować jako prefiks
                    nowy_prefiks_test = odpowiedz_uzytkownika
                    if not nowy_prefiks_test.endswith("."):
                        nowy_prefiks_test += "."                  
                    if is_valid_prefix_format(nowy_prefiks_test):
                        potwierdzony_prefiks = nowy_prefiks_test
                        print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                        break
                    else:
                        print(f"{Fore.YELLOW}Niepoprawny format podanego prefiksu/IP (oczekiwano np. 192.168.1. lub 192.168.1.100). Spróbuj ponownie.{Style.RESET_ALL}")
                        continue
            except (EOFError, KeyboardInterrupt):
                obsluz_przerwanie_uzytkownika()
            except Exception as e:
                 print(f"\n{Fore.RED}Błąd podczas pobierania odpowiedzi: {e}{Style.RESET_ALL}")
                 print(f"Używam automatycznie wykrytego prefiksu: {siec_prefix_automatyczny}")
                 potwierdzony_prefiks = siec_prefix_automatyczny
                 break

    else: # Automatyczne wykrywanie nie powiodło się
        print(f"{Fore.YELLOW}Nie udało się automatycznie wykryć prefiksu sieciowego.{Style.RESET_ALL}")
        while potwierdzony_prefiks is None:
            try:
                prompt_text = f"Podaj prefiks sieciowy (np. 192.168.1.), pełny adres IP (np. 192.168.1.100) lub {Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL} aby zakończyć: "
                odpowiedz_uzytkownika = input(prompt_text).strip()
                wyczysc_wskazana_ilosc_linii_konsoli()
                if not odpowiedz_uzytkownika:
                    print(f"{Fore.YELLOW}Prefiks/IP nie może być pusty. Spróbuj ponownie.{Style.RESET_ALL}")
                    continue

                if is_full_ip_address(odpowiedz_uzytkownika):
                    extracted_prefix = get_prefix_from_ip(odpowiedz_uzytkownika)
                    if extracted_prefix:
                        print(f"{Fore.CYAN}Podano pełny adres IP '{odpowiedz_uzytkownika}'.{Style.RESET_ALL}")
                        try:
                            prompt_confirm_ip = f"Czy chcesz skanować sieć z prefiksem '{extracted_prefix}'? ({Fore.LIGHTMAGENTA_EX}T/n{Style.RESET_ALL}): "
                            odp_confirm = input(prompt_confirm_ip).lower().strip()
                            wyczysc_wskazana_ilosc_linii_konsoli()
                            if not odp_confirm or odp_confirm.startswith('t') or odp_confirm.startswith('y'):
                                potwierdzony_prefiks = extracted_prefix
                                print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                                break
                            else:
                                print(f"{Fore.YELLOW}Skanowanie z prefiksem '{extracted_prefix}' odrzucone. Spróbuj ponownie podać prefiks lub IP.{Style.RESET_ALL}")
                                continue
                        except (EOFError, KeyboardInterrupt):
                            obsluz_przerwanie_uzytkownika()
                    else:
                        print(f"{Fore.YELLOW}Nie udało się wyekstrahować prefiksu z '{odpowiedz_uzytkownika}'. Spróbuj ponownie.{Style.RESET_ALL}")
                        continue
                else: # Waliduj jako prefiks
                    nowy_prefiks_test = odpowiedz_uzytkownika
                    if not nowy_prefiks_test.endswith("."):
                        nowy_prefiks_test += "."
                    
                    if is_valid_prefix_format(nowy_prefiks_test):
                        potwierdzony_prefiks = nowy_prefiks_test
                        print(f"Używany prefiks sieciowy: {potwierdzony_prefiks}")
                        break
                    else:
                        print(f"{Fore.YELLOW}Niepoprawny format podanego prefiksu/IP. Spróbuj ponownie.{Style.RESET_ALL}")
                        continue
            except KeyboardInterrupt:
                obsluz_przerwanie_uzytkownika() # Ta funkcja obsługuje wyjście
            except Exception as e:
                 sys.stdout.write("\r\033[K")
                 sys.stdout.flush()
                 print(f"\n{Fore.RED}Błąd podczas pobierania odpowiedzi: {e}{Style.RESET_ALL}")
                 return None # Zwróć None, aby główna część mogła zareagować

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
    configured_custom_server_ports_map: Dict[str, Dict[int, Optional[str]]]
) -> Union[List[DeviceInfo], Literal[False]]:
    """Agreguje zebrane informacje o urządzeniach w listę obiektów DeviceInfo."""
    lista_urzadzen: List[DeviceInfo] = [] # type: ignore
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
            for proto_ports_with_desc in configured_custom_server_ports_map.values(): # type: ignore
                all_configured_custom_ports_set.update(proto_ports_with_desc.keys()) # type: ignore

        
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
    if not lista_urzadzen:
        return False
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

def wykonaj_skanowanie_i_agreguj_informacje(
    siec_prefix: str,
    host_ip: Optional[str],
    host_mac: Optional[str],
    gateway_ip: Optional[str],
    baza_oui: Dict[str, str],
    mac_nazwy_niestandardowe: Dict[str, str],
    niestandardowe_porty_serwera_mapa: Dict[str, Dict[int, Optional[str]]]
) -> Union[Tuple[List[DeviceInfo], Dict[str, List[int]], Dict[str, str], float], Literal[False]]:
    """
    Wykonuje kroki skanowania sieci (ping, arp, porty, nazwy hostów, system operacyjny)
    i agreguje wyniki do listy obiektów DeviceInfo.

    Args:
        siec_prefix: Prefiks sieci do przeskanowania.
        host_ip: Adres IP lokalnego hosta
        host_mac: Adres MAC lokalnego hosta.
        gateway_ip: Adres IP bramy sieciowej.
        baza_oui: Baza danych OUI.
        mac_nazwy_niestandardowe: Niestandardowe nazwy MAC z pliku.
        niestandardowe_porty_serwera_mapa: Niestandardowe porty serwerów z pliku.

    Returns:
        Krotka zawierająca:
        - List[DeviceInfo]: Zagregowane informacje o urządzeniach.
        - Dict[str, List[int]]: RWyniki skanowania portów {ip: [porty]}.
        - Dict[str, str]: Wyniki zgadywania systemu operacyjnego {ip: skrót_os}.
        - float: Całkowity czas trwania skanowania i agregacji.
        Zwraca False, jeśli nie znaleziono urządzeń lub wystąpił błąd podczas agregacji.
    """
    print("\nRozpoczynanie skanowania sieci (ping)...")
    start_time = time.time() # Start timer for scan phase

    # --- PINGOWANIE ---
    hosty_ktore_odpowiedzialy = pinguj_zakres(siec_prefix, DEFAULT_START_IP, DEFAULT_END_IP)
    # --- KONIEC PINGOWANIA ---

    # --- POBIERANIE IP Z ARP ---
    adresy_ip_z_arp = pobierz_ip_z_arp(siec_prefix)
    # --- KONIEC POBIERANIA IP Z ARP ---

    # --- ŁĄCZENIE LIST IP ---
    final_ip_list_do_przetworzenia = polacz_listy_ip(
        adresy_ip_z_arp,
        hosty_ktore_odpowiedzialy,
        host_ip,
        gateway_ip,
        siec_prefix
    )
    # --- KONIEC ŁĄCZENIA LIST IP ---

    # --- SKANOWANIE PORTÓW ---
    wyniki_skanowania_portow = skanuj_porty_rownolegle(final_ip_list_do_przetworzenia)
    # --- KONIEC SKANOWANIA PORTÓW ---

    # --- POBIERANIE NAZW HOSTÓW ---
    nazwy_hostow_cache = pobierz_nazwy_hostow_rownolegle(final_ip_list_do_przetworzenia)
    # --- KONIEC POBIERANIA NAZW HOSTÓW ---

    # --- ZGADYWANIE OS ---
    os_cache_wyniki = zgadnij_systemy_rownolegle(final_ip_list_do_przetworzenia, wyniki_skanowania_portow)
    # --- KONIEC ZGADYWANIA OS ---

    # --- POBIERANIE I PARSOWANIE ARP (dla MACów) ---
    # Potrzebujemy pełnej mapy ARP tutaj do agregacji MACów
    wynik_arp_raw = pobierz_tabele_arp()
    arp_map = parsuj_tabele_arp(wynik_arp_raw, siec_prefix) if wynik_arp_raw else {}
    if not wynik_arp_raw:
         print(f"{Fore.YELLOW}Ostrzeżenie: Nie można pobrać tabeli ARP. Adresy MAC mogą być niedostępne.{Style.RESET_ALL}")
    # --- KONIEC POBIERANIA ARP ---

    # --- AGREGACJA ---
    # Pass the map with descriptions to aggregation
    wynik_agregacji = agreguj_informacje_o_urzadzeniach(
        final_ip_list_do_przetworzenia,
        arp_map,
        nazwy_hostow_cache,
        wyniki_skanowania_portow,
        os_cache_wyniki,
        baza_oui,
        host_ip,
        host_mac,
        gateway_ip,
        hosty_ktore_odpowiedzialy,
        mac_nazwy_niestandardowe,
        niestandardowe_porty_serwera_mapa # Pass the map with descriptions
    )
    # --- KONIEC AGREGACJI ---

    end_time = time.time() # End timer for scan and aggregation phase
    czas_trwania_sekundy = end_time - start_time

    # Return all results needed for output and HTML generation
    return (wynik_agregacji, wyniki_skanowania_portow, os_cache_wyniki, czas_trwania_sekundy) if wynik_agregacji is not False else False

def wczytaj_mac_nazwy_z_pliku(nazwa_pliku: str = NAZWY_MAC_PLIK) -> Dict[str, str]:
    """
    Wczytuje niestandardowe nazwy urządzeń przypisane do adresów MAC z pliku.
    Plik powinien znajdować się w tej samej lokalizacji co skrypt.
    Format linii w pliku: MAC_ADRES NAZWA_URZADZENIA (separatorem może być spacja, przecinek, średnik, tabulator).
    Linie zaczynające się od '#' są ignorowane jako komentarze.
    """
    mac_nazwy_map: Dict[str, str] = {}
        # Domyślna treść dla pliku mac_nazwy.txt
    # Uzyskaj ścieżkę do katalogu, w którym znajduje się bieżący skrypt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plik_path = os.path.join(script_dir, nazwa_pliku)

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

    # if not os.path.exists(plik_path):
    #     print(f"{Fore.YELLOW}Informacja: Plik '{nazwa_pliku}' nie został znaleziony w lokalizacji skryptu. Nazwy niestandardowe nie zostaną wczytane.{Style.RESET_ALL}")
    #     return mac_nazwy_map

    # print(f"Próba wczytania niestandardowych nazw urządzeń z pliku: '{plik_path}'...")
    # Plik jest sprawdzany i tworzony przez sprawdz_i_utworz_plik. Jeśli nie istnieje po tej funkcji, to jest błąd.

    print(f"Próba wczytania niestandardowych nazw urządzeń z pliku: '{plik_path}'...", end="\n") # Dodano end="\n"
   
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
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Znaleziono MAC '{normalized_mac}', ale brak nazwy.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
                else:
                    print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nie udało się sparsować MAC adresu. Linia: '{line}'{Style.RESET_ALL}", end="\n") # Dodano end="\n"
        
        if mac_nazwy_map:
            print(f"{Fore.GREEN}Pomyślnie wczytano {len(mac_nazwy_map)} niestandardowych nazw urządzeń.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
        else:
            print(f"{Fore.YELLOW}Nie wczytano żadnych niestandardowych nazw urządzeń z pliku '{nazwa_pliku}' (plik może być pusty lub zawierać tylko komentarze).{Style.RESET_ALL}")

    except IOError as e:
        print(f"{Fore.RED}Błąd odczytu pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Nieoczekiwany błąd podczas przetwarzania pliku '{nazwa_pliku}': {e}{Style.RESET_ALL}")

    return mac_nazwy_map

def wczytaj_niestandardowe_porty_serwera(nazwa_pliku: str = NIESTANDARDOWE_PORTY_SERWERA_PLIK) -> Dict[str, Dict[int, Optional[str]]]:
    """ # Corrected docstring
    Wczytuje listę niestandardowych portów serwera (HTTP/HTTPS) z pliku,
    wraz z ich opcjonalnymi opisami. Zwraca słownik mapujący typ protokołu
    na słownik {numer_portu: opis_portu_lub_None}.

    Plik powinien znajdować się w tej samej lokalizacji co skrypt.
    niestandardowe_porty_map: Dict[str, Dict[int, Optional[str]]] = {"http": {}, "https": {}}
    Linie zaczynające się od '#' są ignorowane jako komentarze.

    """

    niestandardowe_porty_map: Dict[str, Dict[int, Optional[str]]] = {"http": {}, "https": {}}
    # Uzyskaj ścieżkę do katalogu, w którym znajduje się bieżący skrypt
    script_dir = os.path.dirname(os.path.abspath(__file__)) # <--- DODANO DEFINICJĘ script_dir
    plik_path = os.path.join(script_dir, nazwa_pliku)

    # Domyślna treść dla pliku port_serwer.txt
    domyslna_tresc_port_serwer = """# Przykładowy plik z niestandardowymi portami dla serwerów HTTP/HTTPS.
# Linie zaczynające się od '#' są ignorowane.
# Format: NUMER_PORTU [OPIS PORTU]
[http]
80 Serwer HTTP
8080 Alternatywny serwer HTTP
[https]
443 Serwer HTTPS
8443 Alternatywny serwer HTTPS"""

    # Najpierw sprawdź/utwórz plik z domyślną treścią, jeśli nie istnieje
    sprawdz_i_utworz_plik(nazwa_pliku, domyslna_tresc_port_serwer)

    # Plik jest sprawdzany i tworzony przez sprawdz_i_utworz_plik. Jeśli nie istnieje po tej funkcji, to jest błąd.

    print(f"Próba wczytania niestandardowych portów serwera z pliku: '{plik_path}'...", end="\n") # Dodano end="\n"

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
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nieznana sekcja '{current_section}'. Oczekiwano [http] lub [https]. Pomijanie sekcji.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
                        current_section = None # Ignoruj porty do czasu znalezienia prawidłowej sekcji (dodano end="\n")
                    continue

                if current_section:
                    try:
                        parts = line.split(maxsplit=1)
                        port_str = parts[0]
                        opis_portu = parts[1].strip() if len(parts) > 1 else None

                        port = int(port_str)
                        if 1 <= port <= 65535:
                            if port not in niestandardowe_porty_map[current_section]:
                                niestandardowe_porty_map[current_section][port] = opis_portu
                            elif niestandardowe_porty_map[current_section][port] is None and opis_portu:
                                # Jeśli port już istnieje bez opisu, a teraz mamy opis, zaktualizuj
                                niestandardowe_porty_map[current_section][port] = opis_portu
                                print(f"{Fore.CYAN}Info w '{nazwa_pliku}' (linia {line_num}): Zaktualizowano opis dla portu {port} w sekcji '{current_section}'.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
                        else:
                            print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Port '{port}' jest poza prawidłowym zakresem (1-65535) w sekcji '{current_section}'. Pomijanie.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
                    except ValueError:
                        print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Nie udało się sparsować numeru portu z '{line.split()[0]}' w sekcji '{current_section}'. Pomijanie.{Style.RESET_ALL}", end="\n") # Dodano end="\n"
                else:
                    print(f"{Fore.YELLOW}Ostrzeżenie w '{nazwa_pliku}' (linia {line_num}): Port '{line}' znaleziony poza sekcją [http] lub [https]. Pomijanie.{Style.RESET_ALL}", end="\n") # Dodano end="\n"

        total_ports_loaded = sum(len(ports_dict) for ports_dict in niestandardowe_porty_map.values())
        if total_ports_loaded > 0:
            print(f"{Fore.GREEN}Pomyślnie wczytano {total_ports_loaded} niestandardowych portów serwera.{Style.RESET_ALL}")
            if niestandardowe_porty_map["http"]:
                http_ports_str = ", ".join(map(str, sorted(niestandardowe_porty_map["http"].keys()))) # Sort keys for display
                print(f"  HTTP porty: {http_ports_str}") # Display sorted ports
            if niestandardowe_porty_map["https"]:
                https_ports_str = ", ".join(map(str, sorted(niestandardowe_porty_map["https"].keys())))
                print(f"  HTTPS porty: {https_ports_str}")
        else:
            print(f"{Fore.YELLOW}Nie wczytano żadnych niestandardowych portów serwera z pliku '{nazwa_pliku}'.{Style.RESET_ALL}", end="\n") # Dodano end="\n"

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


def ustal_finalna_nazwe_pliku_html(
    nazwa_pliku_bazowa_html: str,
    siec_prefix: Optional[str] = None,
    default_start_ip_dla_nazwy: int = DEFAULT_START_IP  # Użyj globalnej stałej jako domyślnej
) -> str:
    """
    Ustala finalną nazwę pliku HTML, opcjonalnie dodając prefiks sieci i startowy IP.

    Args:
        nazwa_pliku_bazowa_html: Bazowa nazwa pliku HTML (np. "raport_skanowania.html").
        siec_prefix: Opcjonalny prefiks sieciowy (np. "192.168.0.").
        default_start_ip_dla_nazwy: Domyślny startowy adres IP używany w nazwie pliku.

    Returns:
        Finalna nazwa pliku HTML z rozszerzeniem.
    """
    nazwa_bazowa_pliku, rozszerzenie_pliku = rozdziel_nazwe_pliku(nazwa_pliku_bazowa_html)

    if siec_prefix:
        # Usuń ostatnią kropkę z prefiksu i zamień pozostałe kropki na podkreślniki
        prefix_dla_nazwy = siec_prefix.rstrip('.').replace('.', '_')
        # Dodaj startowy IP do prefiksu dla nazwy pliku
        prefix_with_start_ip = f"{prefix_dla_nazwy}_{default_start_ip_dla_nazwy}"
        finalna_nazwa_pliku = f"{nazwa_bazowa_pliku}_{prefix_with_start_ip}{rozszerzenie_pliku}"
    else:
        finalna_nazwa_pliku = nazwa_pliku_bazowa_html
    
    return finalna_nazwa_pliku



def zapisz_tabele_urzadzen_do_html(
    lista_urzadzen: List[DeviceInfo],
    kolumny_do_wyswietlenia: List[str],
    opisy_portow_globalne: Dict[int, str],
    configured_custom_server_ports_map: Dict[str, Dict[int, Optional[str]]],
    nazwa_pliku_html: str = DOMYSLNA_NAZWA_PLIKU_HTML_BAZOWA, # Użyj globalnej stałej
    siec_prefix: Optional[str] = None # Opcjonalny prefiks sieci do dodania do nazwy pliku
) -> Optional[str]: # Zmieniono typ zwracany na Optional[str]
    """
    Zapisuje tabelę urządzeń do pliku HTML z interaktywnym sortowaniem.
    (Reszta opisu bez zmian)
    """
    finalna_nazwa_pliku_html = ustal_finalna_nazwe_pliku_html(
        nazwa_pliku_bazowa_html=nazwa_pliku_html,
        siec_prefix=siec_prefix
        # DEFAULT_START_IP jest używane domyślnie w nowej funkcji
    )

    aktywne_kolumny = {k: v for k, v in KOLUMNY_TABELI.items() if k in kolumny_do_wyswietlenia}
    
    # Konwertuj listę kolumn do formatu JSON dla JavaScript
    kolumny_do_wyswietlenia_json = json.dumps(kolumny_do_wyswietlenia)

    # PRZENIESIONO DEFINICJĘ script_name_for_wol NA POCZĄTEK,
    # ABY BYŁA DOSTĘPNA PODCZAS TWORZENIA F-STRINGA html_content.
    script_name_for_wol = html.escape(os.path.basename(__file__))


#    # --- ROZSZERZONE DEBUGOWANIE DLA F-STRING ---
#     print(f"{Fore.MAGENTA}DEBUG EXTRA: Typ zmiennej script_name_for_wol: {type(script_name_for_wol)}{Style.RESET_ALL}")
#     print(f"{Fore.MAGENTA}DEBUG EXTRA: Wartość script_name_for_wol: '{script_name_for_wol}'{Style.RESET_ALL}")
#     print(f"{Fore.MAGENTA}DEBUG EXTRA: Reprezentacja (repr) script_name_for_wol: {repr(script_name_for_wol)}{Style.RESET_ALL}")

#     test_placeholder = "{script_name_for_wol}"
#     print(f"{Fore.MAGENTA}DEBUG EXTRA: Testowy placeholder: '{test_placeholder}'{Style.RESET_ALL}")

#     # Testowy, bardzo prosty f-string
#     minimal_fstring_output = f"TEST_SCRIPT_NAME = \"{script_name_for_wol}\""
#     print(f"{Fore.MAGENTA}DEBUG EXTRA: Wynik minimalnego f-stringa: '{minimal_fstring_output}'{Style.RESET_ALL}")

#     if test_placeholder in minimal_fstring_output:
#         print(f"{Fore.RED}DEBUG EXTRA: ALARM! Minimalny f-string również zawiera placeholder '{test_placeholder}' zamiast wartości!{Style.RESET_ALL}")
#     elif script_name_for_wol in minimal_fstring_output:
#         print(f"{Fore.GREEN}DEBUG EXTRA: OK! Minimalny f-string poprawnie wstawił wartość '{script_name_for_wol}'.{Style.RESET_ALL}")
#     else:
#         print(f"{Fore.YELLOW}DEBUG EXTRA: Coś dziwnego z minimalnym f-stringiem - ani placeholder, ani wartość nie zostały znalezione w oczekiwany sposób.{Style.RESET_ALL}")
#     # --- KONIEC ROZSZERZONEGO DEBUGOWANIA ---

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
        }}
        .sort-indicator.active {{
            color: white; /* Kolor aktywnego wskaźnika */
        }}

        /* Style dla modala WoL */
        .wol-modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4); }}
        .wol-modal-content {{ background-color: #fefefe; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 90%; max-width: 600px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2),0 6px 20px 0 rgba(0,0,0,0.19); border-radius: 5px; text-align: left; }}
        .wol-modal-close {{ color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
        .wol-modal-close:hover, .wol-modal-close:focus {{ color: black; text-decoration: none; cursor: pointer; }}
        #wolCommandInput {{ width: calc(100% - 90px); padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; }}
        .wol-modal-content button {{ padding: 8px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        .wol-modal-content button:hover {{ background-color: #45a049; }}
        #copyWolStatus {{ font-size: 0.9em; color: green; margin-top: 5px; }}
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
            if col_key not in ["lp"]: # Kolumna Lp nie jest sortowalna
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
                    protocol = "http" # Default to http
                    if configured_custom_server_ports_map.get("https") and port_num in configured_custom_server_ports_map["https"]:
                        protocol = "https"
                    elif configured_custom_server_ports_map.get("http") and port_num in configured_custom_server_ports_map["http"]:
                        protocol = "http"
                                            
                    opis_portu = opisy_portow_globalne.get(port_num)
                    title_text = f"Otwórz aplikację webową na porcie {port_num}." # Domyślny tekst
                    if opis_portu:
                        title_text = f"Otwórz aplikację webową (Usługa: {html.escape(opis_portu)})"
                    link_href = f"{protocol}://{html.escape(device.ip)}:{port_num}"
                    port_display_str = f'<a href="{link_href}" target="_blank" title="{title_text}" >{port_num}</a>'
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
        # Przygotowanie zawartości komórki MAC z linkiem WoL
        mac_display_val = device.mac if device.mac else "Nieznany MAC"
        mac_html_content = html.escape(mac_display_val)
        if device.mac and device.mac != "Nieznany MAC": # Tylko jeśli MAC jest znany i nie jest to placeholder
            # Użyj device.mac (oryginalny, nieoczyszczony MAC, jeśli taki byłby problem)
            # ale mac_display_val powinien być już poprawnym MACem, jeśli device.mac istnieje
            mac_html_content = f'<a href="javascript:void(0);" onclick="showWolCommand(\'{html.escape(device.mac)}\')" title="Wyślij pakiet Wake-on-LAN">{html.escape(mac_display_val)}</a>'


        row_data_base = {
            "lp": str(idx),
            "ip": html.escape(device.ip),
            "mac": mac_html_content, # Użyj przygotowanej zawartości HTML dla MAC
            "host": nazwa_do_wyswietlenia_hosta, # Ta wartość jest już gotowa do wyświetlenia
            "porty": porty_html_output,
            "os": html.escape(device.guessed_os), "oui": html.escape(device.oui_vendor)
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
    # Sekcja informacyjna o plikach konfiguracyjnych - zostanie dodana później
    informacje_o_plikach_html = f"""
    <div class="legend-section">
        <h2>Informacje o plikach konfiguracyjnych</h2>
        <p>Możesz dostosować działanie skanera i wygląd raportu poprzez edycję plików tekstowych znajdujących się w tym samym katalogu co skrypt:</p>
        <ul>
            <li>
                <strong>{html.escape(NAZWY_MAC_PLIK)}:</strong> Służy do przypisywania niestandardowych, przyjaznych nazw urządzeniom na podstawie ich adresów MAC.
                Przydaje się to do łatwiejszej identyfikacji urządzeń, które nie mają nazwy DNS lub których nazwa DNS jest nieczytelna.
                <br>Format każdej linii: <code>MAC_ADRES Nazwa Urządzenia</code> (np. <code>AA:BB:CC:DD:EE:FF Mój Serwer Domowy</code>).
                <br>Adres MAC może być zapisany z dwukropkami, myślnikami lub bez separatorów. Nazwa urządzenia to reszta linii. Linie zaczynające się od '#' są ignorowane.
            </li>
            <li>
                <strong>{html.escape(NIESTANDARDOWE_PORTY_SERWERA_PLIK)}:</strong> Pozwala na zdefiniowanie dodatkowych portów HTTP/HTTPS, które skrypt ma traktować jako potencjalne serwery webowe (tworząc klikalne linki w raporcie HTML) oraz na dodanie własnych opisów dla tych portów.
                <br>Format pliku:
                <br><code>[http]</code>
                <br><code>NUMER_PORTU_HTTP Opis portu HTTP (opcjonalny)</code>
                <br><code>[https]</code>
                <br><code>NUMER_PORTU_HTTPS Opis portu HTTPS (opcjonalny)</code>
                <br>Przykład:
                <br><code>[http]</code>
                <br><code>8081 Mój alternatywny serwer HTTP</code>
            </li>
        </ul>
        <p>Po dokonaniu zmian w tych plikach, uruchom skrypt ponownie, aby zobaczyć efekty.</p>
    </div>
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
            html_content += f"            <li><b>{html.escape(str(port))}:</b> {html.escape(opis)}</li>\n"
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
"""    
    # Dodaj sekcję informacyjną o plikach konfiguracyjnych PO legendach
    html_content += informacje_o_plikach_html
    """
    <div id="wolModal" class="wol-modal">
        <div class="wol-modal-content">
            <span class="wol-modal-close" onclick="closeWolModal()">&times;</span>
            <h2>Wyślij Pakiet Wake-on-LAN</h2>
            <p>Aby wysłać pakiet Wake-on-LAN (WoL) do urządzenia z adresem MAC <strong id="wolMacAddress"></strong>, możesz użyć poniższego polecenia w terminalu, będąc w katalogu, w którym znajduje się skrypt:</p>
            <input type="text" id="wolCommandInput" readonly>
            <button onclick="copyWolCommand()">Kopiuj</button>
            <p id="copyWolStatus"></p>
            <p style="font-size:0.8em; color:#555;">Upewnij się, że urządzenie docelowe oraz jego karta sieciowa są skonfigurowane do odbierania pakietów WoL, a zapory sieciowe nie blokują portu (domyślnie 9 UDP).</p>
        </div>
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
            //     // To wymagałoby przechowywania oryginalnych danychlub ponownego renderowania
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

        // Funkcje dla modala WoL
        const SCRIPT_NAME_WOL = "%%PLACEHOLDER_SCRIPT_NAME_WOL%%"; // Zmieniono na placeholder

        const wolModal = document.getElementById('wolModal'); // Get modal element once


        function showWolCommand(macAddress) { 
            const modal = document.getElementById('wolModal');
            const commandInput = document.getElementById('wolCommandInput');
            const macDisplay = document.getElementById('wolMacAddress');
            const copyStatus = document.getElementById('copyWolStatus');

            macDisplay.textContent = macAddress;
            commandInput.value = 'python ' + SCRIPT_NAME_WOL + ' -wol ' + macAddress; // SCRIPT_NAME_WOL jest już wartością
            modal.style.display = 'block';
            copyStatus.textContent = ''; // Wyczyść status kopiowania
        } 
        
        function closeWolModal() {
            const modal = wolModal; // Use the cached element
            modal.style.display = 'none';
        } 
        function copyWolCommand() {
            const commandInput = document.getElementById('wolCommandInput');
            commandInput.select(); // Zaznacz tekst w polu
            navigator.clipboard.writeText(commandInput.value).then(() => {
                const copyStatus = document.getElementById('copyWolStatus'); // Get status element once
                copyStatus.textContent = 'Skopiowano do schowka!';
                // Opcjonalnie: ukryj status po kilku sekundach
                setTimeout(() => { 
                    copyStatus.textContent = '';
                }, 3000); // Ukryj po 3 sekundach
            }, (err) => {
                const copyStatus = document.getElementById('copyWolStatus'); // Get status element once
                copyStatus.textContent = 'Błąd kopiowania!';
                console.error('Błąd kopiowania WoL: ', err);
                // Opcjonalnie: ukryj status błędu po kilku sekundach
            }); 
        } 
    </script>
</body>
</html>
"""
    # --- Obejście problemu z interpolacją f-stringa dla SCRIPT_NAME_WOL ---
    # Tworzymy wartość, która ma być wstawiona do JavaScript (z cudzysłowami)
    rzeczywista_wartosc_js_script_name = f'"{script_name_for_wol}"'
    # Zamieniamy placeholder w html_content na rzeczywistą wartość
    html_content = html_content.replace('"%%PLACEHOLDER_SCRIPT_NAME_WOL%%"', rzeczywista_wartosc_js_script_name)
    # --- Koniec obejścia ---
    


    # ... definicja html_content ...
    # script_name_for_wol = html.escape(os.path.basename(__file__)) # Upewnij się, że to jest zdefiniowane

    # # --- POCZĄTEK DEBUGOWANIA ---
    # print(f"{Fore.MAGENTA}DEBUG: Wartość dla script_name_for_wol: '{script_name_for_wol}'{Style.RESET_ALL}")
    # # Wypisz fragment kodu HTML tuż przed miejscem, gdzie jest placeholder {0}
    # # ZMIANA: Usunięto stary blok debugowania, ponieważ .format() nie jest już używane w ten sposób.
    # # Można dodać nowy, jeśli potrzebne, np. sprawdzający obecność {script_name_for_wol}
    # script_name_placeholder_in_fstring = f'"{script_name_for_wol}"' # Tak powinno wyglądać w f-stringu
    # placeholder_index_new = html_content.find(script_name_placeholder_in_fstring)
    # if placeholder_index_new != -1:
    #     print(f"{Fore.CYAN}DEBUG: Znaleziono wstawioną nazwę skryptu '{script_name_placeholder_in_fstring}' w html_content (co jest oczekiwane).{Style.RESET_ALL}")
    #     # start_index = max(0, placeholder_index_new - 100)
    #     # end_index = min(len(html_content), placeholder_index_new + len(script_name_placeholder_in_fstring) + 100)
    #     # print(f"{Fore.CYAN}DEBUG: Fragment html_content wokół wstawionej nazwy skryptu:\n"
    #     #       f"...{html_content[start_index:placeholder_index_new]}"
    #     #       f"{Fore.YELLOW}{html_content[placeholder_index_new : placeholder_index_new + len(script_name_placeholder_in_fstring)]}{Fore.CYAN}"
    #     #       f"{html_content[placeholder_names[0] + len(script_name_placeholder_in_fstring) : end_index]}...{Style.RESET_ALL}")
    # else:
    #     print(f"{Fore.RED}DEBUG: Nie znaleziono wstawionej nazwy skryptu '{script_name_placeholder_in_fstring}' w html_content!{Style.RESET_ALL}")
    
    # # --- KONIEC DEBUGOWANIA ---

    try:
        # Zdefiniuj kolory tutaj, aby były dostępne
        green_color = Fore.GREEN if COLORAMA_AVAILABLE else ""
        red_color = Fore.RED if COLORAMA_AVAILABLE else ""
        reset_color = Style.RESET_ALL if COLORAMA_AVAILABLE else ""

        with open(finalna_nazwa_pliku_html, "w", encoding="utf-8") as f:
            f.write(html_content) # ZMIANA: Usunięto .format()

        abs_path_pliku_html = os.path.abspath(finalna_nazwa_pliku_html)
        print(f"{green_color}Pomyślnie zapisano raport do pliku: {abs_path_pliku_html}{reset_color}")
        return abs_path_pliku_html # Zwróć pełną ścieżkę do pliku
    except IOError as e:
        print(f"{red_color}Błąd zapisu do pliku HTML '{finalna_nazwa_pliku_html}': {e}{reset_color}")
        return None # Zwróć None w przypadku błędu
    except Exception as e:
        print(f"{red_color}Nieoczekiwany błąd podczas zapisu pliku HTML: {e}{reset_color}")
        return None # Zwróć None w przypadku błędu

# def zapisz_konfiguracje_na_koniec_skryptu(
#     siec_prefix: Optional[str],
#     kolumny_dla_terminalu: List[str],
#     uzyc_wybranych_w_html: bool,
#     cmd_menu_choice_to_use: Optional[str]
# ) -> None:
#     """
#     Zapisuje konfigurację na koniec działania skryptu.
#     Jeśli użyto parametru -m, zapisuje tylko ostatni prefiks sieci.
#     W przeciwnym razie zapisuje pełną konfigurację (prefiks, kolumny, opcja HTML).
#     """
#     if not siec_prefix: # Zapisuj tylko, jeśli prefiks został pomyślnie ustalony
#         return

#     if cmd_menu_choice_to_use is not None:
#         # Parametr -m był użyty. Chcemy zaktualizować tylko 'last_prefix'.
#         config_data_to_save: Dict[str, Any] = {}
#         if os.path.exists(CONFIG_FILE):
#             try:
#                 with open(CONFIG_FILE, "r", encoding="utf-8") as f:
#                     config_data_to_save = json.load(f)
#             except (json.JSONDecodeError, IOError) as e:
#                 print(f"{Fore.YELLOW}Ostrzeżenie: Nie udało się odczytać istniejącego pliku {CONFIG_FILE} przed zapisem (błąd: {e}). Zostanie utworzony nowy z tylko prefiksem.{Style.RESET_ALL}")
#                 config_data_to_save = {}

#         config_data_to_save["last_prefix"] = siec_prefix
        
#         try:
#             with open(CONFIG_FILE, "w", encoding="utf-8") as f:
#                 json.dump(config_data_to_save, f, indent=4)
#             print(f"{Fore.CYAN}Parametr -m był użyty. Zaktualizowano prefiks sieci w {CONFIG_FILE}. Konfiguracja kolumn/HTML pozostała bez zmian.{Style.RESET_ALL}")
#         except IOError as e:
#             print(f"Błąd podczas zapisywania konfiguracji (tylko prefiks) do pliku {CONFIG_FILE}: {e}")
#     else:
#         # Parametr -m NIE był użyty, zapisz normalnie wyniki z interaktywnego menu
#         save_config(siec_prefix, kolumny_dla_terminalu, uzyc_wybranych_w_html)

def obsluz_generowanie_raportu_html(
    lista_urzadzen_do_wyswietlenia: List[DeviceInfo],
    uzyc_wybranych_w_html: bool,
    kolumny_dla_terminalu: List[str],
    domyslne_kolumny_do_wyswietlenia_html: List[str],
    domyslna_nazwa_pliku_html_bazowa: str,
    siec_prefix: Optional[str],
    opisy_portow_globalne: Dict[int, str],
    niestandardowe_porty_serwera_mapa: Dict[str, Dict[int, Optional[str]]]
) -> None:
    """
    Obsługuje logikę pytania użytkownika o zapis raportu HTML,
    ustalenia kolumn do raportu, zapisania go i ewentualnego otwarcia.
    """
    kolumny_dla_html_reportu: List[str]
    if uzyc_wybranych_w_html:
        kolumny_dla_html_reportu = kolumny_dla_terminalu
    else:
        kolumny_dla_html_reportu = domyslne_kolumny_do_wyswietlenia_html

    if lista_urzadzen_do_wyswietlenia:
        chce_zapisac, nazwa_bazowa_od_uzytkownika_lub_none = zapytaj_czy_zapisac_raport_html(
            domyslna_nazwa_bazowa_konfiguracyjna=domyslna_nazwa_pliku_html_bazowa,
            siec_prefix_do_wyswietlenia=siec_prefix
        )

        if chce_zapisac:
            nazwa_pliku_bazowa_do_zapisu = domyslna_nazwa_pliku_html_bazowa
            if nazwa_bazowa_od_uzytkownika_lub_none:
                nazwa_pliku_bazowa_do_zapisu = nazwa_bazowa_od_uzytkownika_lub_none
            
            sciezka_do_zapisanego_html = zapisz_tabele_urzadzen_do_html(
                lista_urzadzen_do_wyswietlenia,
                kolumny_dla_html_reportu,
                opisy_portow_globalne,
                niestandardowe_porty_serwera_mapa,
                nazwa_pliku_html=nazwa_pliku_bazowa_do_zapisu,
                siec_prefix=siec_prefix
            )
            if sciezka_do_zapisanego_html:
                zapytaj_i_otworz_raport_html(sciezka_do_zapisanego_html)
    else:
        print(f"{Fore.YELLOW}Pominięto generowanie raportu HTML, ponieważ nie znaleziono żadnych urządzeń.{Style.RESET_ALL}")

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

def _save_to_config_file(config_data: Dict[str, Any], operation_description: str):
    """Pomocnicza funkcja do zapisu danych konfiguracyjnych do pliku."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print(f"Konfiguracja ({operation_description}) zapisana do pliku: {CONFIG_FILE}")
    except IOError as e:
        print(f"Błąd podczas zapisywania konfiguracji ({operation_description}) do pliku {CONFIG_FILE}: {e}")

def save_menu_config_state(displayed_columns: List[str], include_in_html: bool):
    """Zapisuje stan konfiguracji menu (kolumny i opcja HTML) do pliku config.json, zachowując inne wartości."""
    config_data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Fore.YELLOW}Ostrzeżenie: Nie udało się odczytać {CONFIG_FILE} ({e}) przed zapisem stanu menu. Zostanie utworzony nowy plik.{Style.RESET_ALL}")
            config_data = {}

    config_data["displayed_columns"] = displayed_columns
    config_data["include_in_html"] = include_in_html
    _save_to_config_file(config_data, "stan menu")

def save_prefix_config_state(last_prefix: Optional[str]):
    """Zapisuje ostatnio użyty prefiks sieci do pliku config.json, zachowując inne wartości."""
    if last_prefix is None:
        return

    config_data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Fore.YELLOW}Ostrzeżenie: Nie udało się odczytać {CONFIG_FILE} ({e}) przed zapisem prefiksu. Zostanie utworzony nowy plik.{Style.RESET_ALL}")
            config_data = {}
    
    config_data["last_prefix"] = last_prefix
    _save_to_config_file(config_data, "prefiks sieci")

def zapytaj_czy_zapisac_raport_html(
    domyslna_nazwa_bazowa_konfiguracyjna: str,
    siec_prefix_do_wyswietlenia: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Pyta użytkownika, czy chce zapisać raport HTML i jaką nazwę pliku użyć.

    Args:
        domyslna_nazwa_bazowa_konfiguracyjna: Domyślna bazowa nazwa pliku (np. "raport.html").
        siec_prefix_do_wyswietlenia: Opcjonalny prefiks sieci, który zostanie użyty
                                     do skonstruowania proponowanej pełnej nazwy pliku.

    Returns:
        Krotka (czy_zapisac: bool, nazwa_pliku_bazowa_do_uzycia: Optional[str]):
        - czy_zapisac: True, jeśli użytkownik chce zapisać.
        - nazwa_pliku_bazowa_do_uzycia:
            - Jeśli użytkownik wybrał domyślną nazwę (lub proponowaną): None (sygnalizuje użycie domyslna_nazwa_bazowa_konfiguracyjna).
            - Jeśli użytkownik podał własną nazwę: string z tą nazwą (z dodanym rozszerzeniem, jeśli brak).
            - Jeśli czy_zapisac jest False: None.
    """
    try:
        proponowana_pelna_nazwa = ustal_finalna_nazwe_pliku_html(
            nazwa_pliku_bazowa_html=domyslna_nazwa_bazowa_konfiguracyjna,
            siec_prefix=siec_prefix_do_wyswietlenia
        )
        
        prompt_text = (
            f"Czy chcesz zapisać raport HTML? Proponowana nazwa to: {Fore.CYAN}{proponowana_pelna_nazwa}{Style.RESET_ALL} ({Fore.LIGHTMAGENTA_EX}T/n{Style.RESET_ALL}) lub podaj własną bazową nazwę: "
            # f"({Fore.LIGHTMAGENTA_EX}T/Enter{Style.RESET_ALL}=użyj proponowanej | "
            # f"{Fore.LIGHTMAGENTA_EX}N{Style.RESET_ALL}=nie zapisuj | "
            # f"{Fore.LIGHTMAGENTA_EX}inna nazwa{Style.RESET_ALL}=podaj własną bazową nazwę): "
        )
        odpowiedz = input(prompt_text).strip()

        if not odpowiedz or odpowiedz.lower() == 't' or odpowiedz.lower() == 'y':
            # print(f"Zapisywanie raportu jako: {proponowana_pelna_nazwa}")
            return True, None # Sygnalizuje użycie domyślnej nazwy bazowej (tej z argumentu funkcji)
        # elif odpowiedz.lower().startswith('n'):
        elif odpowiedz.lower() == 'n':
            print("Pominięto zapisywanie raportu HTML.")
            return False, None
        else:
            # Użytkownik podał własną nazwę bazową
            custom_name_input = odpowiedz
            _ , domyslne_rozszerzenie_z_konfiguracji = rozdziel_nazwe_pliku(domyslna_nazwa_bazowa_konfiguracyjna)
            custom_name_base_part, custom_name_ext_part = rozdziel_nazwe_pliku(custom_name_input)

            final_custom_base_name_with_ext: str
            if not custom_name_ext_part: # Jeśli użytkownik nie podał rozszerzenia w swojej nazwie
                final_custom_base_name_with_ext = custom_name_base_part + domyslne_rozszerzenie_z_konfiguracji
                # print(f"Do podanej nazwy '{custom_name_base_part}' dodano domyślne rozszerzenie: '{domyslne_rozszerzenie_z_konfiguracji}'.")
            else:
                final_custom_base_name_with_ext = custom_name_input
            
            # Ta nazwa (final_custom_base_name_with_ext) będzie teraz *bazą* dla funkcji
            # ustal_finalna_nazwe_pliku_html wywoływanej wewnątrz zapisz_tabele_urzadzen_do_html.
            # Funkcja ta doda prefiks sieciowy, jeśli jest dostępny.
            # print(f"Użyto niestandardowej nazwy bazowej: {Fore.CYAN}{final_custom_base_name_with_ext}{Style.RESET_ALL}")
            return True, final_custom_base_name_with_ext

    except (EOFError, KeyboardInterrupt):
        obsluz_przerwanie_uzytkownika()
        return False, None # Chociaż skrypt się zakończy, zwracamy spójny typ
    except Exception as e:
        print(f"{Fore.RED}Wystąpił błąd podczas pytania o zapis raportu: {e}{Style.RESET_ALL}")
        return False, None


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
        prompt_text = f"Czy chcesz otworzyć raport HTML ({os.path.basename(sciezka_do_pliku_html)}) w przeglądarce? ({Fore.LIGHTMAGENTA_EX}T/n{Style.RESET_ALL}): "
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

def wyslij_wol_packet(mac_address_str: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> bool:
    """
    Wysyła pakiet Magic (Wake-on-LAN) na podany adres MAC.

    Args:
        mac_address_str: Adres MAC urządzenia docelowego w formacie string
                         (np. "00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E", "001A2B3C4D5E").
        broadcast_ip: Adres IP broadcast, na który ma zostać wysłany pakiet Magic.
                      Domyślnie "255.255.255.255", co jest ogólnym adresem broadcast
                      i zazwyczaj działa poprawnie w lokalnych podsieciach (np. /24).
                      W razie problemów, można podać specyficzny adres
                      broadcast podsieci, np. "192.168.1.255" dla sieci 192.168.1.0/24.
        port: Port docelowy dla pakietu WoL. Domyślnie 9. Czasem używany jest też port 7.

    Returns:
        bool: True jeśli pakiet został wysłany pomyślnie, False w przeciwnym razie.
    """
    # 1. Walidacja i normalizacja adresu MAC
    # Usuń popularne separatory i przekształć na ciąg 12 znaków heksadecymalnych
    mac_clean = re.sub(r'[^0-9a-fA-F]', '', mac_address_str)
    if len(mac_clean) != 12:
        print(f"{Fore.RED}Błąd: Nieprawidłowy format adresu MAC '{mac_address_str}'. Oczekiwano 12 znaków heksadecymalnych.{Style.RESET_ALL}")
        return False
    
    try:
        mac_bytes = bytes.fromhex(mac_clean)
    except ValueError:
        print(f"{Fore.RED}Błąd: Adres MAC '{mac_address_str}' zawiera nieprawidłowe znaki heksadecymalne.{Style.RESET_ALL}")
        return False

    # 2. Konstrukcja pakietu Magic
    # Składa się z 6 bajtów 0xFF, a następnie 16-krotnego powtórzenia adresu MAC (6 bajtów)
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    # 3. Wysłanie pakietu używając gniazda UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Umożliwienie wysyłania pakietów broadcast
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.sendto(magic_packet, (broadcast_ip, port))
            print(f"{Fore.GREEN}Pakiet Magic (WoL) został pomyślnie wysłany do {mac_address_str.upper()} na adres {broadcast_ip}:{port}.{Style.RESET_ALL}")
            return True
        except socket.gaierror: # Błąd związany z adresem (np. nieprawidłowy broadcast_ip)
            print(f"{Fore.RED}Błąd: Nieprawidłowy adres broadcast '{broadcast_ip}' lub problem z rozpoznaniem nazwy.{Style.RESET_ALL}")
            return False
        except OSError as e: # Inne błędy systemowe gniazda (np. sieć niedostępna)
            print(f"{Fore.RED}Błąd systemowy podczas wysyłania pakietu WoL: {e}{Style.RESET_ALL}")
            return False
        except Exception as e: # Inne nieoczekiwane błędy
            print(f"{Fore.RED}Nieoczekiwany błąd podczas wysyłania pakietu WoL: {e}{Style.RESET_ALL}")
            return False
        
def is_valid_mac(mac_address_str: str) -> bool:
    """Sprawdza, czy ciąg znaków ma format adresu MAC (12 znaków heksadecymalnych)."""
    mac_clean = re.sub(r'[^0-9a-fA-F]', '', mac_address_str)
    return len(mac_clean) == 12

def is_valid_ipv4(ip_str: str) -> bool:
    """Sprawdza, czy ciąg znaków jest poprawnym adresem IPv4."""
    try:
        socket.inet_aton(ip_str)
        return True
    except socket.error:
        return False

def is_valid_port(port_str: str) -> bool:
    """Sprawdza, czy ciąg znaków jest poprawnym numerem portu (1-65535)."""
    try:
        port = int(port_str)
        return 1 <= port <= 65535
    except ValueError:
        return False

def waliduj_i_przetworz_parametry_wol(wol_args_input: List[str]) -> Optional[Tuple[str, str, int]]:
    """
    Waliduje i przetwarza argumenty dla funkcji WoL.
    W przypadku błędu, wyświetla instrukcję i pozwala na ponowne wprowadzenie.

    Args:
        wol_args_input: Lista argumentów podanych dla opcji -wol.
                        Oczekiwane formaty:
                        - [mac]
                        - [mac, port]
                        - [mac, ip_broadcast]
                        - [mac, ip_broadcast, port]

    Returns:
        Krotka (mac_address, broadcast_ip, port) jeśli walidacja się powiodła,
        None jeśli użytkownik przerwał lub nie udało się sparsować.
    """
    # Utwórz kopię listy, aby uniknąć modyfikacji oryginalnej listy z argparse
    wol_args = list(wol_args_input)

    while True:
        mac_to_return: Optional[str] = None
        ip_to_return: str = "255.255.255.255"  # Domyślny IP broadcast
        port_to_return: int = 9               # Domyślny port
        valid_parse = False
      
        if not wol_args or len(wol_args) == 0:
            print(f"{Fore.RED}Błąd: Brak adresu MAC dla opcji -wol.{Style.RESET_ALL}")

        elif len(wol_args) > 3:
            print(f"{Fore.YELLOW}Ostrzeżenie: Podano zbyt wiele argumentów dla -wol. Użyte zostaną pierwsze trzy.{Style.RESET_ALL}")
            wol_args = wol_args[:3] # Rozważ tylko pierwsze trzy

        if wol_args: # Sprawdź ponownie po potencjalnym przycięciu
            mac_address_candidate = wol_args[0]
            if not is_valid_mac(mac_address_candidate):
                print(f"{Fore.RED}Błąd: Nieprawidłowy format adresu MAC '{mac_address_candidate}'. Oczekiwano 12 znaków heksadecymalnych.{Style.RESET_ALL}")
                # mac_to_return pozostaje None
            else:
                mac_to_return = mac_address_candidate # MAC jest wstępnie poprawny

                if len(wol_args) == 1: # Tylko MAC
                    valid_parse = True
                
                elif len(wol_args) == 2:
                    second_arg = wol_args[1]
                    if is_valid_port(second_arg): # Przypadek: MAC PORT
                        port_to_return = int(second_arg)
                        # ip_to_return pozostaje domyślny
                        valid_parse = True
                    elif is_valid_ipv4(second_arg): # Przypadek: MAC IP_BROADCAST
                        ip_to_return = second_arg
                        # port_to_return pozostaje domyślny
                        valid_parse = True
                    else:
                        print(f"{Fore.RED}Błąd: Drugi argument '{second_arg}' nie jest ani prawidłowym adresem IP broadcast, ani numerem portu.{Style.RESET_ALL}")
                        mac_to_return = None # Unieważnij, bo parsowanie niekompletne

                elif len(wol_args) == 3: # Przypadek: MAC IP_BROADCAST PORT
                    ip_candidate = wol_args[1]
                    port_candidate = wol_args[2]
                    
                    ip_ok = is_valid_ipv4(ip_candidate)
                    port_ok = is_valid_port(port_candidate)

                    if ip_ok and port_ok:
                        ip_to_return = ip_candidate
                        port_to_return = int(port_candidate)
                        valid_parse = True
                    else:
                        if not ip_ok:
                            print(f"{Fore.RED}Błąd: Nieprawidłowy format adresu IP broadcast '{ip_candidate}'.{Style.RESET_ALL}")
                        if not port_ok:
                            print(f"{Fore.RED}Błąd: Nieprawidłowy format numeru portu '{port_candidate}'.{Style.RESET_ALL}")
                        mac_to_return = None # Unieważnij
        
        if valid_parse and mac_to_return:
            return mac_to_return, ip_to_return, port_to_return

        # Jeśli doszliśmy tutaj, parsowanie się nie powiodło lub brakowało argumentów
        print(f"\n{Fore.YELLOW}Instrukcja użycia opcji -wol:{Style.RESET_ALL}")
        script_name = os.path.basename(__file__)
        print(f"  {Style.BRIGHT}python {script_name} -wol <MAC_ADDRESS> [BROADCAST_IP] [PORT]{Style.RESET_ALL}")
        print(f"  {Style.BRIGHT}python {script_name} -wol <MAC_ADDRESS> [PORT]{Style.RESET_ALL} (użyje domyślnego IP broadcast: {ip_to_return})")
        print(f"  Przykład 1: {Style.BRIGHT}python {script_name} -wol 00:1A:2B:3C:4D:5E{Style.RESET_ALL}")
        print(f"  Przykład 2: {Style.BRIGHT}python {script_name} -wol 001A2B3C4D5E 7{Style.RESET_ALL} (MAC i port, domyślny IP)")
        print(f"  Przykład 3: {Style.BRIGHT}python {script_name} -wol 00-1A-2B-3C-4D-5E 192.168.1.255 7{Style.RESET_ALL} (MAC, IP, port)")
        print(f"  Adres MAC jest wymagany. Domyślny IP broadcast: {ip_to_return}, domyślny port: {port_to_return}.")
        
        try:
            nowe_args_str = input(f"Podaj poprawne parametry WoL (MAC [IP PORT] lub MAC [PORT]) lub ({Fore.LIGHTMAGENTA_EX}Ctrl+C{Style.RESET_ALL}) aby wyjść: ")
            wol_args = shlex.split(nowe_args_str) # Podziel string na listę argumentów
        except (KeyboardInterrupt, EOFError):
            obsluz_przerwanie_uzytkownika() 
            return None # Nie powinno być osiągnięte, bo obsluz_przerwanie_uzytkownika kończy skrypt

def obsluz_argumenty_linii_polecen() -> Tuple[Optional[str], Optional[str]]:
    """Obsługuje argumenty linii poleceń, w tym specjalny tryb Wake-on-LAN."""
    parser = argparse.ArgumentParser(
        description="Skaner sieci lokalnej.",
        # Zmieniamy epilog, aby nie pokazywał domyślnego błędu, gdy argument jest bez wartości
        # Można też użyć add_help=False i własnej obsługi -h, ale to bardziej skomplikowane.
        # Na razie standardowy help wystarczy.
    )
    # Definiujemy unikalne wartości sentinelowe do wykrycia, czy flaga była podana bez argumentu
    SENTINEL_NO_VALUE_PREFIX = object()
    SENTINEL_NO_VALUE_MENU = object()

    parser.add_argument(
        "-p", "--prefix",
        nargs='?',  # Argument jest opcjonalny
        const=SENTINEL_NO_VALUE_PREFIX,  # Wartość, jeśli -p jest podane bez argumentu
        default=None,  # Wartość, jeśli -p nie ma w ogóle
        type=str,      # Nadal oczekujemy stringa, jeśli argument jest podany
        help="Prefiks sieciowy do skanowania (np. 192.168.1.). Pomija interaktywne pytanie."
    )
    parser.add_argument(
        "-m", "--menu-choice",
        nargs='?',  # Argument jest opcjonalny
        const=SENTINEL_NO_VALUE_MENU,  # Wartość, jeśli -m jest podane bez argumentu
        default=None,  # Wartość, jeśli -m nie ma w ogóle
        type=str,      # Nadal oczekujemy stringa, jeśli argument jest podany
        help="Wybór opcji menu dla kolumn i raportu HTML (np. '17'). Pomija interaktywne menu."
    )
    parser.add_argument(
        "-wol", "--wake-on-lan",
        nargs='+', # Akceptuje jeden lub więcej argumentów: MAC [BROADCAST_IP] [PORT]
        metavar='MAC_ADDRESS', # Zmieniono metavar na pojedynczy string, aby pasował do nargs='+'
        help="Wyślij pakiet Wake-on-LAN. Wymagany MAC_ADDRESS. Opcjonalnie: [BROADCAST_IP PORT] lub [PORT] (użyje domyślnego IP). Domyślne IP: 255.255.255.255, Port: 9."
    )
    args = parser.parse_args()

            # --- Obsługa -wol ---
    if args.wake_on_lan:
        parametry_wol = waliduj_i_przetworz_parametry_wol(args.wake_on_lan)
        if parametry_wol:
            mac, broadcast, port_num = parametry_wol
            wyslij_wol_packet(mac, broadcast, port_num)
            # Komunikaty o sukcesie/błędzie są już w wyslij_wol_packet i waliduj_i_przetworz_parametry_wol
        sys.exit(0) # Zakończ skrypt po próbie WoL, niezależnie od wyniku

    # Przetwarzanie argumentów -p i -m, jeśli -wol nie został użyty
    cmd_prefix_to_use = args.prefix
    if args.prefix is SENTINEL_NO_VALUE_PREFIX:
        print(f"{Fore.YELLOW}Ostrzeżenie: Parametr -p został podany bez wartości. Prefiks zostanie pobrany interaktywnie.{Style.RESET_ALL}")
        cmd_prefix_to_use = None

    # Zamiast bezpośredniego wywołania sys.exit(0) w zainstaluj_pakiet,
    # można by zwrócić flagę i obsłużyć wyjście tutaj, jeśli to konieczne.

    # --- Sprawdzenie aktualizacji na początku ---
    # Sprawdź, czy argumenty zostały podane bez wartości i potraktuj je jako None
    cmd_menu_choice_to_use = args.menu_choice
    if args.menu_choice is SENTINEL_NO_VALUE_MENU:
        print(f"{Fore.YELLOW}Ostrzeżenie: Parametr -m został podany bez wartości. Menu wyboru kolumn zostanie wyświetlone.{Style.RESET_ALL}")
        cmd_menu_choice_to_use = None

    return cmd_prefix_to_use, cmd_menu_choice_to_use


# --- Główna część skryptu ---
if __name__ == "__main__":
    try:
        # 1. Obsługa argumentów linii poleceń (w tym -wol, który może zakończyć skrypt)
        cmd_prefix_to_use, cmd_menu_choice_to_use = obsluz_argumenty_linii_polecen()

        # 2. Sprawdzenie aktualizacji
        sprawdz_i_zaproponuj_aktualizacje()
        # --- Koniec sprawdzania aktualizacji ---
        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"Skaner sieci Lokalnej z maską /24",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
        wszystkie_ip, glowny_ip = pobierz_wszystkie_aktywne_ip()
        
        nazwa_aktywnego_vpn: Optional[str] = None

        wynik_vpn_check = czy_aktywny_vpn_lub_podobny() 
        if wynik_vpn_check:
            if "(potencjalny)" in wynik_vpn_check:
                interface_name_potencjalny = wynik_vpn_check.replace(' (potencjalny)','')
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,f"Info: Wykryto potencjalny interfejs VPN: {interface_name_potencjalny}, ale może nie być aktywny/połączony.",Fore.CYAN,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
            else:
                nazwa_aktywnego_vpn = wynik_vpn_check 
                wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,f"OSTRZEŻENIE: Wykryto aktywny interfejs VPN: {nazwa_aktywnego_vpn}.",Fore.LIGHTYELLOW_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"Może to zakłócać rozpoznawanie nazw hostów w Twojej sieci lokalnej (LAN).",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"Jeśli nazwy hostów lokalnych nie są wyświetlane poprawnie (pokazuje 'Nieznana'), spróbuj:",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"1. Skonfigurować VPN, aby używał lokalnych serwerów DNS (jeśli to możliwe, np. Split DNS).",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                wyswietl_tekst_w_linii(" ",DEFAULT_LINE_WIDTH,"2. Tymczasowo wyłączyć VPN na czas działania skryptu.",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=False)
                    
                prefixy_zdalne_wszystkie = pobierz_prefixy_zdalne_vpn(nazwa_aktywnego_vpn)
                 # Filtruj, aby pokazać tylko całe podsieci (nie pojedyncze hosty /32)
                prefixy_zdalne_podsieci = [p for p in prefixy_zdalne_wszystkie if not p.endswith('/32')]

                if prefixy_zdalne_podsieci:
                    wyswietl_tekst_w_linii(" ", DEFAULT_LINE_WIDTH, f"Zdalne podsieci dostępne przez VPN ({nazwa_aktywnego_vpn}): {', '.join(prefixy_zdalne_podsieci)}", Fore.CYAN, Fore.LIGHTCYAN_EX, dodaj_odstepy=False)
                elif prefixy_zdalne_wszystkie: # Jeśli były jakieś /32, ale nie ma /24 itp.
                    wyswietl_tekst_w_linii(" ", DEFAULT_LINE_WIDTH, f"Przez VPN ({nazwa_aktywnego_vpn}) dostępne są tylko pojedyncze hosty (nie całe podsieci).", Fore.CYAN, Fore.LIGHTCYAN_EX, dodaj_odstepy=False)
                else:
                    wyswietl_tekst_w_linii(" ", DEFAULT_LINE_WIDTH, f"Nie udało się ustalić konkretnych sieci zdalnych dla VPN ({nazwa_aktywnego_vpn}).", Fore.YELLOW, Fore.LIGHTCYAN_EX, dodaj_odstepy=False)
                wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"",Fore.YELLOW,Fore.LIGHTCYAN_EX,dodaj_odstepy=True) 


        host_ip = glowny_ip 
        host_mac = pobierz_mac_adres(host_ip) 
        gateway_ip = pobierz_brame_domyslna()

        print(f"Adres IP komputera: {host_ip if host_ip else 'Nieznany'}")
        print(f"Adres MAC komputera: {host_mac if host_mac else 'Nieznany'}") 

        # Wczytaj konfigurację na początku, aby mieć dostęp do wczytanych wartości
        last_prefix_loaded, displayed_columns_loaded, include_in_html_loaded = load_config()

        # --- Ustalanie prefiksu sieciowego ---
        siec_prefix: Optional[str] = None
        if cmd_prefix_to_use: # Jeśli podano argument -p
            siec_prefix = pobierz_i_zweryfikuj_prefiks(cmd_prefix=cmd_prefix_to_use)

        else: # Brak argumentu -p, sprawdź konfigurację i/lub tryb interaktywny
            suggestion_from_config: Optional[str] = None
            if last_prefix_loaded: # Użyj last_prefix_loaded zamiast last_prefix_loaded_from_config dla spójności
                temp_loaded = last_prefix_loaded
                if not temp_loaded.endswith("."): temp_loaded += "."
                if is_valid_prefix_format(temp_loaded):
                    print(f"{Fore.CYAN}Ostatnio skanowany prefiks był: {temp_loaded}{Style.RESET_ALL}")
                    suggestion_from_config = temp_loaded
                else:
                    print(f"{Fore.YELLOW}Ostatnio wczytany prefiks '{last_prefix_loaded}' jest niepoprawny. Próba auto-detekcji.{Style.RESET_ALL}")
            siec_prefix = pobierz_i_zweryfikuj_prefiks(cmd_prefix=cmd_prefix_to_use)


        # Przekaż wczytaną konfigurację menu do funkcji wyboru kolumn
        kolumny_dla_terminalu, uzyc_wybranych_w_html = wybierz_kolumny_do_wyswietlenia(
            wszystkie_kolumny_map=KOLUMNY_TABELI,
            domyslne_kolumny_dla_menu=DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA,
            cmd_menu_choice=cmd_menu_choice_to_use,
            loaded_selected_column_keys=displayed_columns_loaded,
            loaded_include_in_html=include_in_html_loaded
        )

        if cmd_menu_choice_to_use is None: # Menu było interaktywne, zapisz jego stan
            save_menu_config_state(kolumny_dla_terminalu, uzyc_wybranych_w_html)

        if siec_prefix is None:
            print(f"{Fore.RED}Nie udało się ustalić prefiksu sieciowego. Zakończono.{Style.RESET_ALL}")
            sys.exit(1) 

        print("Pobieranie/ładowanie bazy OUI...")
        baza_oui = pobierz_baze_oui(url=OUI_URL, plik_lokalny=OUI_LOCAL_FILE, timeout=REQUESTS_TIMEOUT, aktualizacja_co=OUI_UPDATE_INTERVAL)
        if not baza_oui:
            print(f"{Fore.YELLOW}OSTRZEŻENIE: Nie udało się załadować bazy OUI. Nazwy producentów nie będą dostępne.{Style.RESET_ALL}")
            baza_oui = {} 
        mac_nazwy_niestandardowe = wczytaj_mac_nazwy_z_pliku()
        niestandardowe_porty_serwera_mapa = wczytaj_niestandardowe_porty_serwera()
        
        zintegruj_niestandardowe_porty_z_opisami(OPISY_PORTOW, niestandardowe_porty_serwera_mapa)
        
        wynik_skanowania_i_agregacji = wykonaj_skanowanie_i_agreguj_informacje(
            siec_prefix,
            host_ip,
            host_mac,
            gateway_ip,
            baza_oui,
            mac_nazwy_niestandardowe,
            niestandardowe_porty_serwera_mapa
        )


        lista_urzadzen_do_wyswietlenia: List[DeviceInfo] = []
        wyniki_skanowania_portow_do_legendy: Dict[str, List[int]] = {}
        os_cache_wyniki_do_legendy: Dict[str, str] = {}
        czas_trwania_sekundy_skanowania: float = 0.0

        if wynik_skanowania_i_agregacji is False:
            print(f"{Fore.YELLOW}Nie zebrano informacji o żadnych urządzeniach lub wystąpił błąd podczas skanowania.{Style.RESET_ALL}")
            lista_urzadzen_do_wyswietlenia = []
            wyniki_skanowania_portow_do_legendy = {}
            os_cache_wyniki_do_legendy = {}
            czas_trwania_sekundy_skanowania = 0.0
        else:
            lista_urzadzen_do_wyswietlenia, wyniki_skanowania_portow_do_legendy, os_cache_wyniki_do_legendy, czas_trwania_sekundy_skanowania = wynik_skanowania_i_agregacji

        wyswietl_legende_kolorow_urzadzen()
        wyswietl_legende_portow(wyniki_skanowania_portow_do_legendy)
        wyswietl_legende_systemow(os_cache_wyniki_do_legendy) 
        
        wyswietl_tabele_urzadzen(
            lista_urzadzen_do_wyswietlenia, 
            kolumny_dla_terminalu
        )

        print(f"\nCałkowity czas skanowania i agregacji: {czas_trwania_sekundy_skanowania:.2f} sekund. Czyli {przelicz_sekundy_na_minuty_sekundy(round(czas_trwania_sekundy_skanowania))} min:sek")
        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"",Fore.LIGHTCYAN_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)

        # Obsługa generowania raportu HTML
        obsluz_generowanie_raportu_html(
            lista_urzadzen_do_wyswietlenia=lista_urzadzen_do_wyswietlenia,
            uzyc_wybranych_w_html=uzyc_wybranych_w_html,
            kolumny_dla_terminalu=kolumny_dla_terminalu,
            domyslne_kolumny_do_wyswietlenia_html=DOMYSLNE_KOLUMNY_DO_WYSWIETLENIA,
            domyslna_nazwa_pliku_html_bazowa=DOMYSLNA_NAZWA_PLIKU_HTML_BAZOWA,
            siec_prefix=siec_prefix,
            opisy_portow_globalne=OPISY_PORTOW,
            niestandardowe_porty_serwera_mapa=niestandardowe_porty_serwera_mapa
        )

        # Zapisz prefiks na sam koniec
        if siec_prefix:
            save_prefix_config_state(siec_prefix)


        wyswietl_tekst_w_linii("-",DEFAULT_LINE_WIDTH,"Skanowanie zakończone. Przewiń wyżej, aby zobaczyć wszystkie informacje.",Fore.LIGHTCYAN_EX,Fore.LIGHTCYAN_EX,dodaj_odstepy=True)
    except KeyboardInterrupt:
        obsluz_przerwanie_uzytkownika()
        sys.exit(0)
