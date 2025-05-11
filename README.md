# Skaner Sieci Lokalnej (LAN Scanner)

Prosty skrypt w Pythonie do skanowania sieci lokalnej (LAN) w poszukiwaniu aktywnych urządzeń. Wyświetla adresy IP, adresy MAC, nazwy hostów, producentów kart sieciowych (OUI), otwarte niestandardowe porty TCP, a także próbuje zgadnąć system operacyjny. Wyniki mogą być wyświetlane w konsoli oraz zapisywane do interaktywnego raportu HTML.

W ramach nauki programowania — bardziej kopiuj-wklej i research w sieci oraz niezastąpione narzędzia AI, ale coś się udało.

## Funkcje

*   **Automatyczne wykrywanie prefiksu sieciowego:** Próbuje automatycznie wykryć prefiks sieci lokalnej (np. `192.168.1.`).
*   **Skanowanie zakresu IP:** Wykonuje polecenie `ping` dla domyślnego zakresu adresów w wykrytej podsieci (zwykle od `.1` do `.254`), aby "obudzić" urządzenia i zaktualizować tabelę ARP systemu.
*   **Odczyt tabeli ARP:** Pobiera i parsuje systemową tabelę ARP w celu znalezienia powiązań adresów IP i MAC.
*   **Rozwiązywanie nazw hostów:** Próbuje uzyskać nazwy hostów dla znalezionych adresów IP (z wykorzystaniem wątków dla przyspieszenia).
*   **Identyfikacja producenta (OUI):** Pobiera (i buforuje lokalnie) bazę danych IEEE OUI, aby zidentyfikować producenta karty sieciowej na podstawie adresu MAC.
*   **Wykrywanie hosta lokalnego i bramy:** Oznacza w wynikach komputer, na którym uruchomiono skrypt, oraz domyślną bramę sieciową.
*   **Kolorowanie wyników:** Używa biblioteki `colorama` (jeśli dostępna) do czytelniejszego prezentowania wyników w konsoli.
*   **Generowanie raportu HTML:** Tworzy plik `raport_skanowania.html` z interaktywną tabelą wyników (sortowanie kolumn) i pyta o jego automatyczne otwarcie.
*   **Skanowanie niestandardowych portów TCP:** Sprawdza, czy na znalezionych urządzeniach są otwarte porty zdefiniowane przez użytkownika w pliku `port_serwer.txt`.
*   **Zgadywanie systemu operacyjnego:** Próbuje oszacować system operacyjny na podstawie wartości TTL odpowiedzi na ping.
*   **Własne nazwy urządzeń:** Możliwość przypisania niestandardowych nazw urządzeniom na podstawie ich adresów MAC za pomocą pliku `mac_nazwy.txt`.
*   **Konfigurowalne porty i opisy:** Użytkownik może zdefiniować własne porty do skanowania wraz z ich opisami w pliku `port_serwer.txt`.
*   **Legendy w konsoli:** Wyświetla legendy wyjaśniające znaczenie kolorów urządzeń, wyniki skanowania portów oraz prawdopodobne systemy operacyjne.
*   **Wykrywanie VPN/Tailscale:** Ostrzega użytkownika, jeśli wykryje potencjalnie aktywny interfejs VPN (wymaga `psutil`), który może zakłócać rozpoznawanie nazw hostów w LAN.
*   **Automatyczna instalacja zależności:** Próbuje automatycznie zainstalować brakujące biblioteki (`colorama`, `psutil`, `requests`) za pomocą `pip`.
*   **Wsparcie dla wielu platform:** Działa w systemach Windows, Linux i macOS (wykorzystując odpowiednie polecenia systemowe).
*   **Argumenty linii poleceń:** Umożliwia modyfikację zachowania skryptu, np. podanie prefiksu sieci, pominięcie pingowania, rozwiązywania nazw hostów, skanowania portów czy zgadywania OS.
*   **Zapisywanie konfiguracji użytkownika:** Zapamiętuje ostatnio użyty prefiks sieci oraz wybrane kolumny do wyświetlenia w konsoli w pliku `config.json`.
*   **Interaktywny wybór kolumn:** Pozwala użytkownikowi wybrać, które kolumny mają być wyświetlane w tabeli w konsoli.
*   **Wyświetlanie czasu skanowania:** Informuje o całkowitym czasie trwania skanowania.

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
    ```bash
    python skaner_sieci.py -p 192.168.0.
    ```
    ```bash
    python skaner_sieci.py -p 192.168.0. -m 17
    ```
    
    python skaner_sieci.py --prefix 192.168.0.      prefix sieci do skanowania

    python skaner_sieci.py -m 17    pominie pierwszą kolumne i uwsględni w raporcie html

    python skaner_sieci.py --menu-choice 17     pominie pierwszą kolumne i uwsględni w raporcie html

    python skaner_sieci.py --menu-choice 1     pominie pierwszą kolumne w raporcie html będą wszystkie kolumny

    python skaner_sieci.py --prefix 192.168.0. --menu-choice 17

    -m 123456 kolumny które mają się nie wyświetlań 7 uwzględnić w raporcie html
    
    -m 7 lub 0 wyświetli wszystkie kolumny.
     
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

## Konfiguracja
Skrypt oferuje kilka sposobów konfiguracji:

### Parametry w kodzie źródłowym
Niektóre globalne parametry działania skryptu można dostosować bezpośrednio w pliku `skaner_sieci.py`:

*   `MULTICAST_PREFIXES`: Lista prefiksów adresów multicast do wykluczenia.
*   `DEFAULT_START_IP`, `DEFAULT_END_IP`: Zakres hostów do pingowania.
*   `OUI_URL`, `OUI_LOCAL_FILE`, `OUI_UPDATE_INTERVAL`: Ustawienia bazy OUI.
*   `REQUESTS_TIMEOUT`, `PING_TIMEOUT_MS`, `PING_TIMEOUT_SEC`, `HOSTNAME_LOOKUP_TIMEOUT`: Timeouty dla operacji sieciowych.
*   `TCP_CONNECT_TIMEOUT`: Timeout dla skanowania portów TCP.
*   `MAX_PING_WORKERS`: Maksymalna liczba równoległych pingów im więcej tym mniejsza dokładność
*   `VPN_INTERFACE_PREFIXES`: Prefiksy nazw interfejsów uznawanych za VPN.
*   `MAX_HOSTNAME_WORKERS`: Maksymalna liczba wątków do równoległego rozwiązywania nazw hostów.
*   `TTL_OS_GUESSES`: Słownik mapujący zakresy TTL na prawdopodobne systemy operacyjne.

### Pliki konfiguracyjne
Skrypt wykorzystuje również zewnętrzne pliki tekstowe (umieszczone w tym samym katalogu co `skaner_sieci.py`) do dalszej personalizacji:

*   **`mac_nazwy.txt`**: Pozwala na przypisanie niestandardowych, przyjaznych nazw urządzeniom na podstawie ich adresów MAC. Każda linia w pliku powinna mieć format:
    `AA:BB:CC:DD:EE:FF Moja niestandardowa nazwa urządzenia`
    Przykład: `00:1A:2B:3C:4D:5E Serwer Plików`
*   **`port_serwer.txt`**: Umożliwia zdefiniowanie niestandardowych portów TCP, które pozwalają rozpoznać czy urządzenie ma uruchomiony serwer WWW. Każda linia w pliku powinna mieć format:
    `[https]`
    `443`
    `[http]`
    `80`

*   **`oui.txt`**: Lokalna kopia bazy danych OUI (Organizationally Unique Identifier), pobierana i aktualizowana automatycznie przez skrypt.

## Wsparcie dla platform

Unchanged lines
    *   Upewnij się, że urządzenia są włączone i podłączone do tej samej sieci.
    *   Firewall na urządzeniu może blokować odpowiedzi na ping (ICMP Echo Request). Skrypt nadal może znaleźć urządzenie, jeśli pojawi się ono w tabeli ARP po innej komunikacji.
*   **Błędy przy pobieraniu OUI:** Sprawdź połączenie internetowe. Skrypt spróbuje użyć lokalnie zapisanej wersji bazy, jeśli jest dostępna.
*   **Niedokładne zgadywanie OS:** Zgadywanie systemu operacyjnego na podstawie TTL jest metodą heurystyczną i nie zawsze jest w 100% dokładne. Różne systemy i konfiguracje sieciowe mogą wpływać na wartości TTL.
*   **Niestandardowe porty zamknięte:** Jeśli skanowanie niestandardowych portów pokazuje je jako zamknięte, upewnij się, że:
    *   Usługa faktycznie nasłuchuje na danym porcie na urządzeniu docelowym.
    *   Firewall na urządzeniu docelowym lub w sieci nie blokuje połączeń przychodzących na ten port.
*   **Błędy uprawnień:** W niektórych systemach (szczególnie Linux/macOS) niektóre polecenia sieciowe mogą wymagać uprawnień administratora (root/sudo), chociaż skrypt stara się używać poleceń dostępnych dla zwykłego użytkownika.

## Licencja

Brak
