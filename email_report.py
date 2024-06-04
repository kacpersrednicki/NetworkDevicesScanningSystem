import smtplib
from base64 import b64decode
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import json
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.protocols.gmpv208 import ReportFormatType
from gvm.transforms import EtreeTransform
from datetime import datetime
import time

# Dane do logowania i połączenia
email = 'kacper.srednicki@onet.pl'
password = 'QHVI-P0LO-XCO8-1V6N'
connection = UnixSocketConnection(path='/bso/gvm/gvmd/gvmd.sock')
transform = EtreeTransform()

state_file = 'scan_state.json'


def load_state():
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            if 'tasks' not in state:
                state['tasks'] = []
            return state
    except FileNotFoundError:
        return {}


def save_state(state):
    with open(state_file, 'w') as f:
        json.dump(state, f)


def monitor_reports():
    with Gmp(connection, transform=transform) as gmp:
        gmp.authenticate('admin', 'admin')
        while True:
            state = load_state()
            for task_info in state.get('tasks', []):
                task_id = task_info.get('task_id')
                last_status = task_info.get('last_status')
                task = gmp.get_task(task_id)
                scan_name = task_info.get('scan_name')
                current_status = task.find(".//status").text
                print(scan_name+' ' + current_status)
                if current_status == 'Done' and current_status != last_status:
                    report_name = task_info['report_name']
                    try:
                        get_report(gmp, task_id, report_name)
                        send_email_report(receiver=task_info.get('receiver_email'), report_name=report_name)
                    except Exception as e:
                        print(f"Błąd podczas przetwarzania zadania {task_id}: {e}")
                task_info['last_status'] = current_status
                save_state(state)
            time.sleep(30)


def get_report(gmp, task_id, report_name):
    ready_task = gmp.get_task(task_id)
    report_id = ready_task.find(".//task").find('.//report').attrib.get("id")
    report = gmp.get_report(report_id=report_id, details=True, report_format_id=ReportFormatType.PDF,
                            filter_string="apply_overrides=0 levels=hmlg rows=100 min_qod=70 first=1 sort-reverse=severity")
    report_element = report.find("report")
    content = report_element.find("report_format").tail
    binary_base64_encoded_pdf = content.encode('ascii')
    binary_pdf = b64decode(binary_base64_encoded_pdf)
    pdf_path = Path(f'{report_name}.pdf').expanduser()
    pdf_path.write_bytes(binary_pdf)
    print(f"Raport PDF '{report_name}' został utworzony")


def send_email_report(receiver, report_name):
    server = smtplib.SMTP('smtp.poczta.onet.pl', 587)
    server.starttls()
    server.login(email, password)
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = receiver
    msg['Subject'] = f'Raport: {report_name}'
    body = "Raport skanowania"
    msg.attach(MIMEText(body, 'plain'))
    file = f"{report_name}.pdf"
    with open(file, "rb") as attachment:
        part = MIMEApplication(attachment.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename=file)
        msg.attach(part)
    server.sendmail(email, receiver, msg.as_string())
    server.quit()
    print(f"Wiadomość e-mail z raportem '{report_name}' została wysłana pomyślnie.")


def main():
    monitor_reports()


if __name__ == "__main__":
    main()