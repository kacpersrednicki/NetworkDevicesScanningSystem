import smtplib
from base64 import b64decode
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.protocols.gmpv208 import AlertCondition, AlertEvent, AlertMethod, ReportFormatType
from gvm.transforms import EtreeTransform
from gvm.xml import pretty_print
from datetime import datetime, timedelta
import time as time
import pytz
from icalendar import Calendar, Event
from icalendar import vRecur


connection = UnixSocketConnection(path='/bso/gvm/gvmd/gvmd.sock')
transform = EtreeTransform()

with Gmp(connection, transform=transform) as gmp:
    gmp.authenticate('admin', 'admin')
    # all IANA assigned TCP and UDP
    port_list_id = '4a4717fe-57d2-11e1-9a26-406186ea4fc5'
    port_list_TEST = '33d0cd82-57c6-11e1-8ed1-406186ea4fc5'
    hosts = ['192.168.0.209']
    target = gmp.create_target(name='test3', hosts=hosts, port_list_id=port_list_TEST)
    target_id = target.attrib.get('id')
    # full and fast config
    config_id = 'daba56c8-73ec-11df-a475-002264764cea'
    config_id_TEST = '8715c877-47a0-438d-98a3-27c7a6ab2196'
    # OpenVAS Default
    scanner_id = '08b69003-5fc2-4037-a479-93b440211c73'

    #schedules
    poland_tz = pytz.timezone('Europe/Warsaw')
    start_time = datetime.now() + timedelta(minutes=5)
    start_time = start_time.astimezone(poland_tz)
    cal = Calendar()
    cal.add('prodid', '-//Foo Bar//')
    cal.add('version', '2.0')
    event = Event()
    event.add('dtstamp', datetime.now(tz=pytz.UTC))
    event.add('dtstart', start_time)
    rrule = vRecur(freq='HOURLY')
    event.add('rrule', rrule)
    cal.add_component(event)

    schedule = gmp.create_schedule(
        name="testPy2",
        icalendar=cal.to_ical(),
        timezone="Europe/Warsaw"
    )
    schedule_id = schedule.attrib.get("id")
    print(schedule_id)

    task = gmp.create_task(name='testTask2', config_id=config_id_TEST, target_id=target_id, scanner_id=scanner_id, schedule_id=schedule_id)
    pretty_print(task)
    task_id = task.attrib.get('id')
    #gmp.start_task(task_id=task_id)
    task_ready = False
    while not task_ready:
        got_task = gmp.get_task(task_id)
        status = got_task.find(".//status").text
        if status == 'Done':
            task_ready = True
        now_time = datetime.now()
        print(f'{now_time.strftime("%H:%M:%S")}: {status}')
        time.sleep(30)
    ready_task = gmp.get_task(task_id)
    report_id = ready_task.find(".//task").find('.//report').attrib.get("id")
    report = gmp.get_report(report_id=report_id, details=True, report_format_id=ReportFormatType.PDF,
                            filter_string="apply_overrides=0 levels=hmlg rows=100 min_qod=70 first=1 sort-reverse=severity")
    report_element = report.find("report")
    content = report_element.find("report_format").tail
    binary_base64_encoded_pdf = content.encode('ascii')
    binary_pdf = b64decode(binary_base64_encoded_pdf)
    pdf_path = Path('report.pdf').expanduser()
    pdf_path.write_bytes(binary_pdf)
    print("PDF report created")


    # Dane do logowania
    email = 'x'
    password = 'x'

    # Tworzenie połączenia z serwerem SMTP Onet
    server = smtplib.SMTP('smtp.poczta.onet.pl', 587)
    server.starttls()

    # Logowanie do serwera
    server.login(email, password)

    # Tworzenie wiadomości
    adresat = 'x'
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = adresat
    msg['Subject'] = 'x'

    # Treść wiadomości
    body = "x"
    msg.attach(MIMEText(body, 'plain'))
    file = "report.pdf"
    # Dodawanie pliku PDF
    with open(file, "rb") as attachment:
        part = MIMEApplication(attachment.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename=file)
        msg.attach(part)

    # Wysyłanie wiadomości
    server.sendmail(email, adresat, msg.as_string())

    # Zamykanie połączenia
    server.quit()

    print("Wiadomość została wysłana pomyślnie.")
