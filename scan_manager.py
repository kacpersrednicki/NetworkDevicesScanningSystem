import json
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event
from icalendar import vRecur
import nmap

# Dane do połączenia
connection = UnixSocketConnection(path='/bso/gvm/gvmd/gvmd.sock')
transform = EtreeTransform()

state_file = 'scan_state.json'


def save_state(state):
    with open(state_file, 'w') as f:
        json.dump(state, f)


def load_state():
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            if 'tasks' not in state:
                state['tasks'] = []
            return state
    except FileNotFoundError:
        return {}


def create_target(gmp, ip_list, target_name):
    port_list_TEST = '33d0cd82-57c6-11e1-8ed1-406186ea4fc5'
    target = gmp.create_target(name=target_name, hosts=ip_list, port_list_id=port_list_TEST)
    target_id = target.attrib.get('id')
    return target_id


def create_scan(gmp, target_id, schedule_id, scan_name):
    config_id_TEST = '8715c877-47a0-438d-98a3-27c7a6ab2196'
    scanner_id = '08b69003-5fc2-4037-a479-93b440211c73'
    task = gmp.create_task(name=scan_name, config_id=config_id_TEST, target_id=target_id, scanner_id=scanner_id,
                           schedule_id=schedule_id)
    task_id = task.attrib.get('id')
    return task_id


def display_scans():
    task_list = load_state()
    task_list = task_list['tasks']
    print("Lista zadań:")
    for idx, task in enumerate(task_list):
        print(f"{idx + 1} Scan_name: {task['scan_name']} (ID: {task['task_id']}) frequency: {task['freq']} Scanned_IP: {task['ip']} Email for report: {task.get('receiver_email')}")


def create_schedule(gmp, freq, schedule_name):
    poland_tz = pytz.timezone('Europe/Warsaw')
    start_time = datetime.now() + timedelta(minutes=5)
    start_time = start_time.astimezone(poland_tz)
    cal = Calendar()
    cal.add('prodid', '-//Foo Bar//')
    cal.add('version', '2.0')
    event = Event()
    event.add('dtstamp', datetime.now(tz=pytz.UTC))
    event.add('dtstart', start_time)
    rrule = vRecur(freq=freq)
    event.add('rrule', rrule)
    cal.add_component(event)
    schedule = gmp.create_schedule(
        name=schedule_name,
        icalendar=cal.to_ical(),
        timezone="Europe/Warsaw"
    )
    schedule_id = schedule.attrib.get("id")
    return schedule_id


def create_new_scan():
    option = input("Wybierz 1 jesli chcesz podac adres ip samemu, 2 jesli chcesz wybrac z hostow w sieci: ")
    if int(option)==1:
        target_ip = input("Podaj adresy IP celu: ").split()
    elif int(option)==2:
        net_ip = input("Podaj adres IP sieci: ")
        target_ip = find_host_in_network(net_ip)
    freq = input("Podaj częstotliwość skanowania (HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY): ")
    receiver_email = input("Podaj adres e-mail do wysyłania raportów: ")
    scan_name = input("Podaj nazwę skanowania: ")
    report_name = f"{scan_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    state = load_state()

    with Gmp(connection, transform=transform) as gmp:
        gmp.authenticate('admin', 'admin')
        target_id = create_target(gmp, target_ip, scan_name)
        schedule_id = create_schedule(gmp, freq,schedule_name=f'{scan_name}_{freq}')
        task_id = create_scan(gmp, target_id, schedule_id, scan_name)

        if 'tasks' not in state:
            state['tasks'] = []
        state['tasks'].append({'task_id': task_id, 'report_name': report_name,'ip':target_ip,'scan_name':scan_name,'freq':freq,'receiver_email':receiver_email})
        save_state(state)


def delete_scan():
    state = load_state()
    if 'tasks' not in state or not state['tasks']:
        print("Brak zadań do usunięcia.")
        return

    task_list = state['tasks']
    print("Lista zadań:")
    for idx, task in enumerate(task_list):
        print(f"{idx + 1}. {task['report_name']} (ID: {task['task_id']})")

    task_idx = int(input("Podaj numer zadania do usunięcia: ")) - 1
    if task_idx < 0 or task_idx >= len(task_list):
        print("Nieprawidłowy numer zadania.")
        return

    task_to_delete = task_list[task_idx]
    with Gmp(connection, transform=transform) as gmp:
        gmp.authenticate('admin', 'admin')
        gmp.delete_task(task_id=task_to_delete['task_id'])

    del task_list[task_idx]
    save_state(state)
    print("Zadanie zostało usunięte.")


def find_host_in_network(network_address):
    nm = nmap.PortScanner()
    print(f"Poszukiwanie hostow w sieci {network_address}. To moze chwile potrwac.")
    nm.scan(hosts=network_address, arguments='-sn',sudo=True)
    active_hosts = [nm[host] for host in nm.all_hosts() if nm[host].hostname()!=""]
    print(active_hosts)
    print(f"Hosty wykryte w sieci {network_address}:")
    for idx, host in enumerate(active_hosts):
        print(f"{idx+1}. {host['hostnames'][0]['name']} {host['addresses']['ipv4']}")
    chosen_host_index = [int(x)-1 for x in input("Podaj indeksy hostow ktore chcesz przeskanowac: ").split()]
    chosen_ip = [active_hosts[i]['addresses']['ipv4'] for i in chosen_host_index]
    return chosen_ip


def main():
    while True:
        print("\nMenu:")
        print("1. Utwórz nowe skanowanie")
        print("2. Usuń istniejące skanowanie")
        print("3. Wyswietl istniejace skanowania")
        print("4. Wyjdź")
        choice = input("Wybierz opcję: ")

        if choice == '1':
            create_new_scan()
        elif choice == '2':
            delete_scan()
        elif choice == '3':
            display_scans()
        elif choice == '4':
            break
        else:
            print("Nieprawidłowy wybór. Spróbuj ponownie.")


if __name__ == "__main__":
    main()
