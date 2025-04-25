# -*- coding: utf-8 -*-
import socket
import subprocess
import re
import platform
import time
import os
import locale
import ipaddress
import sys
import concurrent.futures
from typing import List, Tuple, Optional, Dict

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

# --- Sprawdzanie i importowanie bibliotek zewnętrznych ---

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

    print("\n" + "-" * 70)
    print("\nOstrzeżenie: Biblioteka 'colorama' nie jest zainstalowana.")
    print("Kolorowanie tekstu w konsoli będzie wyłączone.")
    try:
        odpowiedz = input("Czy chcesz spróbować zainstalować ją teraz? (t/n): ").lower().strip()
        if odpowiedz.startswith('t') or odpowiedz.startswith('y'):
            if zainstaluj_pakiet("colorama"):
                print(f"{Fore.CYAN}Instalacja zakończona. Uruchom skrypt ponownie, aby użyć kolorów.{Style.RESET_ALL}")
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
    print("\n" + f"{Style.BRIGHT}-{Style.RESET_ALL}" * 70)
    print(f"\n{Fore.YELLOW}Ostrzeżenie: Biblioteka 'psutil' nie jest zainstalowana.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Nie można automatycznie wykryć oprogramowania typu Tailscale.{Style.RESET_ALL}")
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
# URL bazy OUI i konfiguracja cache
OUI_URL: str = "http://standards-oui.ieee.org/oui/oui.txt"
OUI_LOCAL_FILE: str = "oui.txt"
OUI_UPDATE_INTERVAL: int = 86400 # Co ile sekund aktualizować plik (domyślnie 24h)
# Timeout dla operacji sieciowych
REQUESTS_TIMEOUT: int = 15 # Timeout dla pobierania OUI
PING_TIMEOUT_MS: int = 200 # Timeout dla ping w ms (Windows)
PING_TIMEOUT_SEC: float = 0.2 # Timeout dla ping w s (Linux/macOS)
HOSTNAME_LOOKUP_TIMEOUT: float = 0.5 # Timeout dla socket.gethostbyaddr/getnameinfo
VPN_INTERFACE_PREFIXES: List[str] = ['tun', 'tap', 'open', 'wg', 'tailscale'] # Dodano 'tailscale' dla pewności
# Wykrywanie domyślnego kodowania konsoli (szczególnie dla Windows)
DEFAULT_ENCODING = locale.getpreferredencoding(False)
WINDOWS_OEM_ENCODING = 'cp852' # Częste kodowanie OEM w Polsce, można dostosować
MAX_HOSTNAME_WORKERS: int = 10 # Liczba wątków do równoległego pobierania nazw hostów



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
            print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN (CGNAT) wg adresu IP: {found_by_ip}{Style.RESET_ALL}")
            return True
        elif found_by_primary_name_with_ip:
            print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN wg nazwy (główny z IP): {found_by_primary_name_with_ip}{Style.RESET_ALL}")
            return True
        elif found_by_tailscale_name_with_ip:
             print(f"\n{Fore.CYAN}Info: Wykryto AKTYWNY interfejs VPN wg nazwy (Tailscale z IP): {found_by_tailscale_name_with_ip}{Style.RESET_ALL}")
             return True
        # --- ZMIANA KOMUNIKATÓW TUTAJ ---
        elif found_by_primary_name_only:
            # Zmieniono "AKTYWNY" na "potencjalny" i dodano "(może nie być połączony)"
            print(f"\n{Fore.CYAN}Info: Wykryto potencjalny interfejs VPN wg nazwy (główny, może nie być połączony): {found_by_primary_name_only}{Style.RESET_ALL}")
            return False # Zwracama False
        elif found_by_tailscale_name_only:
            # Zmieniono "AKTYWNY" na "potencjalny" i dodano "(może nie być połączony)"
            print(f"\n{Fore.CYAN}Info: Wykryto potencjalny interfejs VPN (może nie być połączony){Style.RESET_ALL}")
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

def parsuj_tabele_arp(wynik_arp: Optional[str], siec_prefix: str) -> List[Tuple[str, str]]:
    """
    Parsuje tabelę ARP i wyodrębnia adresy IP i MAC.

    Args:
        wynik_arp: Wyjście polecenia arp.
        siec_prefix: Prefiks sieciowy do filtrowania.

    Returns:
        Lista krotek (ip, mac).
    """
    urzadzenia: List[Tuple[str, str]] = []
    if wynik_arp is None:
        return urzadzenia

    # Wzorce Regex skompilowane dla wydajności (jeśli używasz, upewnij się, że są zdefiniowane)
    # Jeśli nie, można je zostawić w pętli lub przenieść tutaj
    ip_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
    mac_pattern = re.compile(r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})")

    linie = wynik_arp.strip().splitlines()
    for linia in linie:
        # Ignoruj linie nagłówkowe lub puste (można dodać więcej warunków w razie potrzeby)
        if not linia or linia.lower().startswith("interface") or linia.lower().startswith("internet address"):
            continue

        ip_match = ip_pattern.search(linia)
        mac_match = mac_pattern.search(linia)

        if ip_match and mac_match:
            ip = ip_match.group(1)
            mac = mac_match.group(1).upper().replace("-", ":") # Ujednolicenie formatu MAC

            # --- POPRAWKA TUTAJ ---
            # Użyj MULTICAST_PREFIXES (wielkie litery) zamiast multicast_prefixes
            if ip.startswith(siec_prefix) and not any(ip.startswith(mp) for mp in MULTICAST_PREFIXES):
                # Unikaj duplikatów
                if (ip, mac) not in urzadzenia:
                    urzadzenia.append((ip, mac))
    return urzadzenia



def pinguj_zakres(siec_prefix: str, start_ip: int, end_ip: int) -> None:
    """
    Pinguj zakres adresów IP w danej podsieci.

    Args:
        siec_prefix: Prefiks sieciowy (np. "192.168.0.").
        start_ip: Początkowy numer hosta.
        end_ip: Końcowy numer hosta.
    """
    print(f"Pingowanie zakresu adresów {siec_prefix}{start_ip} - {siec_prefix}{end_ip}...")
    system = platform.system().lower()

    for i in range(start_ip, end_ip + 1):
        ip = f"{siec_prefix}{i}"
        try:
            if system == "windows":
                # -n 1: wyślij 1 pakiet, -w PING_TIMEOUT_MS: timeout
                polecenie = ["ping", "-n", "1", f"-w {PING_TIMEOUT_MS}", ip]
                # Użycie subprocess.run bez shell=True jest bezpieczniejsze
                # stdout i stderr są przekierowane, aby ukryć output
                subprocess.run(polecenie, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else: # Linux/macOS
                # -c 1: wyślij 1 pakiet, -W PING_TIMEOUT_SEC: timeout
                polecenie = ["ping", "-c", "1", f"-W {PING_TIMEOUT_SEC}", ip]
                subprocess.run(polecenie, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # print(f"Ping: {ip} - Odpowiada") # Odkomentuj do debugowania
        except subprocess.CalledProcessError:
            # print(f"Ping: {ip} - Brak odpowiedzi") # Odkomentuj do debugowania
            pass # Ignoruj błędy pingowania (brak odpowiedzi)
        except FileNotFoundError:
            print(f"Błąd: Polecenie 'ping' nie znalezione. Upewnij się, że jest w ścieżce systemowej.")
            break # Przerwij pętlę, jeśli ping nie działa
        except Exception as e:
            print(f"Błąd podczas pingowania {ip}: {e}")

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


def pokaz_arp_z_nazwami(siec_prefix: str, baza_oui: Dict[str, str]) -> None:
    """
    Wyświetla listę urządzeń z Lp., adresami IP, MAC, nazwami hostów i producentami OUI,
    kolorując wiersze i oznaczając hosta lokalnego oraz bramę domyślną.
    Używa wątków do przyspieszenia pobierania nazw hostów.

    Args:
        siec_prefix: Prefiks sieciowy do filtrowania.
        baza_oui: Słownik zawierający prefiksy OUI i nazwy producentów.
    """
    wynik_arp = pobierz_tabele_arp()
    if wynik_arp is None:
        print(f"{Fore.RED}Nie można pobrać tabeli ARP.{Style.RESET_ALL}")
        return

    urzadzenia = parsuj_tabele_arp(wynik_arp, siec_prefix)
    host_ip = pobierz_ip_interfejsu()
    host_mac = pobierz_mac_adres(host_ip) if host_ip else None
    gateway_ip = pobierz_brame_domyslna()

    # Dodaj hosta do listy, jeśli nie został znaleziony w tabeli ARP
    if host_ip and host_ip.startswith(siec_prefix):
        znaleziono_hosta = any(ip == host_ip for ip, _ in urzadzenia)
        if not znaleziono_hosta:
            urzadzenia.append((host_ip, host_mac if host_mac else "Nieznany MAC"))

    # Sortuj urządzenia po adresach IP
    try:
        urzadzenia.sort(key=lambda x: list(map(int, x[0].split('.'))))
    except ValueError:
        print(f"{Fore.YELLOW}Ostrzeżenie: Nie można posortować adresów IP (niepoprawny format?).{Style.RESET_ALL}")
        urzadzenia.sort(key=lambda x: x[0])

    # --- Przyspieszenie pobierania nazw hostów ---
    ips_to_lookup = [ip for ip, mac in urzadzenia if not ip.endswith(".255")] # Zbierz IP do sprawdzenia
    hostname_cache: Dict[str, str] = {} # Słownik do przechowywania wyników

    print(f"Pobieranie nazw hostów dla {len(ips_to_lookup)} adresów (max {MAX_HOSTNAME_WORKERS} wątków)...")
    start_lookup_time = time.time()

    # Użyj ThreadPoolExecutor do równoległego wywołania pobierz_nazwe_hosta
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_HOSTNAME_WORKERS) as executor:
        # map zachowuje kolejność i zwraca wyniki w tej samej kolejności co wejściowe IP
        # zip łączy oryginalne IP z wynikami zapytań
        hostname_results = executor.map(pobierz_nazwe_hosta, ips_to_lookup)
        hostname_cache = dict(zip(ips_to_lookup, hostname_results))

    end_lookup_time = time.time()
    print(f"Pobieranie nazw hostów zakończone w {end_lookup_time - start_lookup_time:.2f} sekund.")
    # --- Koniec przyspieszenia ---

    # Oblicz szerokość kolumny Lp.
    lp_width = len(str(len(urzadzenia))) + 1
    total_width = lp_width + 16 + 20 + 35 + 30 + (4 * 1)
    separator_line = "-" * total_width

    print("\nZnalezione urządzenia w sieci lokalnej:")
    print(separator_line)
    print(f"{Fore.LIGHTYELLOW_EX}{'Lp.':<{lp_width}} {'Adres IP':<16} {'Adres MAC':<20} {'Nazwa Hostu':<30} {'Producent (OUI)':<30}{Style.RESET_ALL}")
    print(separator_line)

    for idx, (ip, mac) in enumerate(urzadzenia, start=1):
        if ip.endswith(".255"):
            continue

        # Pobierz nazwę hosta z cache (słownika) zamiast wywoływać funkcję ponownie
        nazwa_wyswietlana = hostname_cache.get(ip, "Nieznana") # Użyj .get() dla bezpieczeństwa

        producent_oui = "Nieznany"
        if mac != "Nieznany MAC" and len(mac) >= 8:
            oui_prefix_do_lookupu = mac[:8].upper().replace(":", "-")
            producent = baza_oui.get(oui_prefix_do_lookupu)
            if producent:
                 producent_oui = re.sub(r'\s*\(.*\)\s*$', '', producent).strip()

        # Oznaczanie hosta lokalnego
        is_local_host = (ip == host_ip)
        if is_local_host:
            # Sprawdź, czy nazwa już nie zawiera "(Ty)" (na wypadek gdyby cache zwrócił ją)
            if nazwa_wyswietlana != "Nieznana" and "(Ty)" not in nazwa_wyswietlana:
                nazwa_wyswietlana += " (Ty)"
            elif nazwa_wyswietlana == "Nieznana":
                nazwa_wyswietlana = f"{ip} (Ty)"

        # Oznaczanie bramy domyślnej
        if ip == gateway_ip:
            # Sprawdź, czy nazwa już nie zawiera "(Brama)"
            if nazwa_wyswietlana != "Nieznana" and "(Brama)" not in nazwa_wyswietlana and not is_local_host:
                nazwa_wyswietlana += " (Brama)"
            elif is_local_host and "(Brama)" not in nazwa_wyswietlana: # Jeśli to jednocześnie host i brama
                 nazwa_wyswietlana += " (Brama)"
            elif nazwa_wyswietlana == "Nieznana":
                nazwa_wyswietlana = f"{ip} (Brama)"

        # Przygotuj sformatowaną linię
        line_format = f"{str(idx):<{lp_width}} {ip:<16} {mac:<20} {nazwa_wyswietlana:<30.30} {producent_oui:<30.35}"

        # Zastosuj kolor
        if nazwa_wyswietlana != "Nieznana" and not nazwa_wyswietlana.startswith(ip):
            print(f"{Fore.LIGHTGREEN_EX}{line_format}{Style.RESET_ALL}")
        elif producent_oui != "Nieznany":
            print(f"{Fore.GREEN}{line_format}{Style.RESET_ALL}")
        else:
            print(line_format)

    print(separator_line)



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
        # Konfiguracja ponowień (Retry) i sesji (Session) - wymaga importów w bloku try dla requests
        retry_strategy = Retry(
            total=3, # Mniejsza liczba ponowień
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)

        response = http.get(url, timeout=timeout)
        response.raise_for_status() # Rzuci wyjątek dla błędów HTTP
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
        print(f"{Fore.RED}Błąd podczas pobierania bazy OUI z sieci: {e}{Style.RESET_ALL}")
        print("Sprawdź połączenie internetowe.")
        # Jeśli pobieranie się nie powiodło, spróbuj użyć starej wersji z pliku
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

# --- Główna część skryptu ---
if __name__ == "__main__":

    # Sprawdź obecność VPN lub inne i wyświetl ostrzeżenie tylko jeśli psutil jest dostępny
    if PSUTIL_AVAILABLE:
        # Użyj nowej nazwy funkcji
        if czy_aktywny_vpn_lub_podobny():
            print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 100)
            # Zaktualizuj komunikat, aby był bardziej ogólny
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}  OSTRZEŻENIE: Wykryto aktywny interfejs VPN lub podobny (np. Tailscale).{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Może to zakłócać rozpoznawanie nazw hostów w Twojej sieci lokalnej (LAN).{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Jeśli nazwy hostów lokalnych nie są wyświetlane poprawnie (pokazuje 'Nieznana'), spróbuj:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    1. Skonfigurować VPN, aby używał lokalnych serwerów DNS (jeśli to możliwe, np. Split DNS).{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    2. Tymczasowo wyłączyć VPN na czas działania skryptu.{Style.RESET_ALL}\n")
            print(f"{Style.BRIGHT}-{Style.RESET_ALL}" * 100)

    # print("\nSkanowanie zakończone.")

    print(f"\n{Fore.LIGHTCYAN_EX}  ---- Skaner Sieci Lokalnej ----\n{Style.RESET_ALL}")

    # Wyświetl adres IP i MAC komputera

    host_ip =pobierz_ip_interfejsu()
    # host_ip =pobierz_ip_przez_psutil()
    host_mac = pobierz_mac_adres(host_ip) #if host_ip else "Nieznany"
    print(f"Adres IP komputera: {host_ip if host_ip else 'Nieznany'}")
    print(f"Adres MAC komputera: {host_mac if host_mac else 'Nieznany'}")

    # Pobierz i zweryfikuj prefiks sieciowy
    siec_prefix = pobierz_prefiks_sieciowy() # Użyj poprawionej funkcji
    if siec_prefix:
        try:
            odpowiedz = input(f"Wykryty prefiks sieciowy: '{siec_prefix}'. Czy jest prawidłowy? {Fore.LIGHTMAGENTA_EX} [Enter=Tak / Podaj inny / Ctrl+C=zakończ]: {Style.RESET_ALL}")
            if odpowiedz.strip(): # Jeśli użytkownik coś wpisał
                siec_prefix = odpowiedz.strip()
                if not siec_prefix.endswith("."):
                    siec_prefix += "."
                # Prosta walidacja formatu prefiksu
                if not re.match(r"^(\d{1,3}\.){3}$", siec_prefix):
                    print("Niepoprawny format prefiksu. Używam wykrytego.")
                    siec_prefix = pobierz_prefiks_sieciowy() # Przywróć wykryty
                    if not siec_prefix: # Jeśli nawet wykryty był zły
                         print("Nie można ustalić prefiksu. Przerywam.")
                         exit(1)
        except EOFError:
             print("Używam automatycznie wykrytego prefiksu.")
        except KeyboardInterrupt:
            print("\nPrzerwano przez użytkownika.")
            exit(0)
    else:
        while not siec_prefix:
            try:
                siec_prefix = input("Nie udało się wykryć prefiksu. Podaj prefiks sieciowy (np. 192.168.1.): ").strip()
                if siec_prefix and not siec_prefix.endswith("."):
                    siec_prefix += "."
                if not re.match(r"^(\d{1,3}\.){3}$", siec_prefix):
                    print("Niepoprawny format prefiksu. Spróbuj ponownie.")
                    siec_prefix = None
            except EOFError:
                print("Nie można pobrać prefiksu od użytkownika. Przerywam.")
                exit(1)
            except KeyboardInterrupt:
                print("\nPrzerwano przez użytkownika.")
                exit(0)

    print(f"Używany prefiks sieciowy: {siec_prefix}")

    # Pobierz bazę OUI (użyj poprawionej funkcji z cache)
    print("Pobieranie/ładowanie bazy OUI...")
    baza_oui = pobierz_baze_oui(url=OUI_URL, plik_lokalny=OUI_LOCAL_FILE, timeout=REQUESTS_TIMEOUT, aktualizacja_co=OUI_UPDATE_INTERVAL)
    if not baza_oui:
        print("OSTRZEŻENIE: Nie udało się załadować bazy OUI. Nazwy producentów nie będą dostępne.")
        baza_oui = {} # Użyj pustego słownika

    # Skanowanie sieci
    print("\nRozpoczynanie skanowania sieci (ping)...")
    start_time = time.time()
    # Użyj poprawionej funkcji pinguj_zakres (bez shell=True)
    pinguj_zakres(siec_prefix, DEFAULT_START_IP, DEFAULT_END_IP)
    end_time = time.time()
    print(f"Pingowanie zakończone w {end_time - start_time:.2f} sekund.")

    # Wyświetlanie wyników z tabeli ARP
    start_arp_time = time.time()
    pokaz_arp_z_nazwami(siec_prefix, baza_oui)
    end_arp_time = time.time()
    # Wyświetl czas wykonania pod tabelą
    print(f"Wyświetlanie tabeli ARP zakończone w {end_arp_time - start_arp_time:.2f} sekund.")

    print("\nSkanowanie zakończone.\n")

