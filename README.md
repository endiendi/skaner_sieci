# Skaner Sieci Lokalnej (LAN Scanner)

Prosty skrypt w Pythonie do skanowania sieci lokalnej (LAN) w poszukiwaniu aktywnych urządzeń. Wyświetla adresy IP, adresy MAC, nazwy hostów (jeśli możliwe do rozwiązania) oraz producentów kart sieciowych na podstawie bazy danych OUI (Organizationally Unique Identifier).

W ramach nauki programowania — bardziej kopiuj-wklej i research w sieci, ale coś się udało.

## Funkcje

*   **Automatyczne wykrywanie prefiksu sieciowego:** Próbuje automatycznie wykryć prefiks sieci lokalnej (np. `192.168.1.`).
*   **Skanowanie zakresu IP:** Wykonuje polecenie `ping` dla domyślnego zakresu adresów w wykrytej podsieci (zwykle od `.1` do `.254`), aby "obudzić" urządzenia i zaktualizować tabelę ARP systemu.
*   **Odczyt tabeli ARP:** Pobiera i parsuje systemową tabelę ARP w celu znalezienia powiązań adresów IP i MAC.
*   **Rozwiązywanie nazw hostów:** Próbuje uzyskać nazwy hostów dla znalezionych adresów IP (z wykorzystaniem wątków dla przyspieszenia).
*   **Identyfikacja producenta (OUI):** Pobiera (i buforuje lokalnie) bazę danych IEEE OUI, aby zidentyfikować producenta karty sieciowej na podstawie adresu MAC.
*   **Wykrywanie hosta lokalnego i bramy:** Oznacza w wynikach komputer, na którym uruchomiono skrypt, oraz domyślną bramę sieciową.
*   **Kolorowanie wyników:** Używa biblioteki `colorama` (jeśli dostępna) do czytelniejszego prezentowania wyników w konsoli.
*   **Wykrywanie VPN/Tailscale:** Ostrzega użytkownika, jeśli wykryje potencjalnie aktywny interfejs VPN (wymaga `psutil`), który może zakłócać rozpoznawanie nazw hostów w LAN.
*   **Automatyczna instalacja zależności:** Próbuje automatycznie zainstalować brakujące biblioteki (`colorama`, `psutil`, `requests`) za pomocą `pip`.
*   **Wsparcie dla wielu platform:** Działa w systemach Windows, Linux i macOS (wykorzystując odpowiednie polecenia systemowe).

## Wymagania

*   **Python 3.6+**
*   **Biblioteki Python:**
    *   `requests` (do pobierania bazy OUI)
    *   `psutil` (do wykrywania interfejsów VPN/Tailscale i potencjalnie innych funkcji sieciowych)
    *   `colorama` (do kolorowania tekstu w konsoli)

    *Uwaga:* Skrypt spróbuje automatycznie zainstalować brakujące biblioteki przy pierwszym uruchomieniu, jeśli użytkownik wyrazi na to zgodę.

## Instalacja

1.  **Pobierz skrypt:** Zapisz plik `skaner_sieci.py` na swoim komputerze.
2.  **Zainstaluj zależności (opcjonalnie, jeśli automatyczna instalacja zawiedzie):**
    Otwórz terminal lub wiersz polecenia i uruchom:
    ```bash
    pip install requests psutil colorama
    ```
    *Wskazówka:* Zaleca się używanie wirtualnego środowiska Python (`venv`).

## Użycie

1.  Otwórz terminal lub wiersz polecenia.
2.  Przejdź do katalogu, w którym zapisałeś plik `skaner_sieci.py`.
3.  Uruchom skrypt za pomocą Pythona:
    ```bash
    python skaner_sieci.py
    ```
4.  Skrypt spróbuje wykryć prefiks sieciowy. Zostaniesz zapytany, czy jest on poprawny. Możesz nacisnąć Enter, aby go zaakceptować, podać inny prefiks (np. `10.0.0.`) lub przerwać działanie (Ctrl+C).
5.  Skrypt rozpocznie pingowanie zakresu adresów, a następnie wyświetli tabelę znalezionych urządzeń.

## Jak to działa?

1.  **Sprawdzenie zależności:** Skrypt sprawdza, czy wymagane biblioteki są zainstalowane i oferuje ich instalację.
2.  **Wykrywanie VPN:** Jeśli `psutil` jest dostępny, sprawdza obecność aktywnych interfejsów VPN/Tailscale i wyświetla ostrzeżenie.
3.  **Wykrywanie IP/MAC hosta:** Ustala lokalny adres IP i MAC komputera.
4.  **Wykrywanie prefiksu sieci:** Określa prefiks sieciowy (np. `192.168.1.`) na podstawie lokalnego IP lub pyta użytkownika.
5.  **Pobieranie/ładowanie bazy OUI:** Sprawdza lokalny plik `oui.txt`. Jeśli go nie ma, jest przestarzały lub uszkodzony, próbuje pobrać aktualną wersję z IEEE (wymaga `requests`).
6.  **Pingowanie:** Wysyła pakiety ICMP (ping) do wszystkich adresów w zakresie `prefiks.1` - `prefiks.254`, aby upewnić się, że aktywne urządzenia odpowiedzą i pojawią się w tabeli ARP.
7.  **Pobieranie i parsowanie tabeli ARP:** Wykonuje systemowe polecenie (`arp -a`, `ip neighbor` lub `arp -an`) i wyodrębnia pary IP-MAC dla urządzeń w docelowej podsieci.
8.  **Rozwiązywanie nazw hostów:** Dla każdego znalezionego adresu IP (z wyjątkiem broadcast) próbuje uzyskać nazwę hosta za pomocą `socket.gethostbyaddr` lub `socket.getnameinfo` (z timeoutem i równolegle w wielu wątkach).
9.  **Wyświetlanie wyników:** Prezentuje sformatowaną tabelę zawierającą numer porządkowy, adres IP, adres MAC, nazwę hosta i nazwę producenta (na podstawie OUI). Oznacza hosta lokalnego i bramę domyślną.

## Konfiguracja (w kodzie źródłowym)

Niektóre parametry można dostosować bezpośrednio w pliku `.py`:

*   `MULTICAST_PREFIXES`: Lista prefiksów adresów multicast do wykluczenia.
*   `DEFAULT_START_IP`, `DEFAULT_END_IP`: Zakres hostów do pingowania.
*   `OUI_URL`, `OUI_LOCAL_FILE`, `OUI_UPDATE_INTERVAL`: Ustawienia bazy OUI.
*   `REQUESTS_TIMEOUT`, `PING_TIMEOUT_MS`, `PING_TIMEOUT_SEC`, `HOSTNAME_LOOKUP_TIMEOUT`: Timeouty dla operacji sieciowych.
*   `VPN_INTERFACE_PREFIXES`: Prefiksy nazw interfejsów uznawanych za VPN.
*   `MAX_HOSTNAME_WORKERS`: Maksymalna liczba wątków do równoległego rozwiązywania nazw hostów.

## Wsparcie dla platform

Skrypt został przetestowany i powinien działać na:

*   **Windows:** Używa `route print`, `arp -a`, `ping -n 1 -w`, `getmac`, `ipconfig`.
*   **Linux:** Używa `ip route`, `ip neighbor`, `ping -c 1 -W`, `ip addr`, `ip link`.
*   **macOS:** Używa `netstat -nr`, `arp -an`, `ping -c 1 -W`, `ifconfig`.

## Rozwiązywanie problemów

*   **Brakujące nazwy hostów ("Nieznana"):**
    *   Upewnij się, że serwer DNS w Twojej sieci działa poprawnie i potrafi rozwiązywać lokalne nazwy.
    *   Jeśli używasz VPN, może on zakłócać lokalne zapytania DNS. Spróbuj skonfigurować VPN (np. split tunneling) lub tymczasowo go wyłączyć.
    *   Firewall na skanowanych urządzeniach może blokować odpowiedzi na zapytania o nazwę.
*   **Brakujące urządzenia:**
    *   Upewnij się, że urządzenia są włączone i podłączone do tej samej sieci.
    *   Firewall na urządzeniu może blokować odpowiedzi na ping (ICMP Echo Request). Skrypt nadal może znaleźć urządzenie, jeśli pojawi się ono w tabeli ARP po innej komunikacji.
*   **Błędy przy pobieraniu OUI:** Sprawdź połączenie internetowe. Skrypt spróbuje użyć lokalnie zapisanej wersji bazy, jeśli jest dostępna.
*   **Błędy uprawnień:** W niektórych systemach (szczególnie Linux/macOS) niektóre polecenia sieciowe mogą wymagać uprawnień administratora (root/sudo), chociaż skrypt stara się używać poleceń dostępnych dla zwykłego użytkownika.

## Licencja

Brak
