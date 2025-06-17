from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

# Config
SCOPES = ['https://www.googleapis.com/auth/calendar']
TZ = pytz.timezone('America/Sao_Paulo')

# Grade fixa: (dia_da_semana, hora_inicio, hora_fim, codigo)
GRADE = [
    ("segunda", "07:30", "09:20", "SOP129005"),
    ("segunda", "13:30", "15:20", "PRE029006"),
    ("segunda", "18:30", "20:20", "FEN129005"),
    ("terca",   "09:40", "11:30", "SOP129005"),
    ("terca",   "13:30", "15:20", "PRE029006"),
    ("quarta",  "07:30", "09:20", "EMG129005"),
    ("quarta",  "09:40", "11:30", "PSD129005"),
    ("quinta",  "09:40", "11:30", "PSD129005"),
    ("sexta",   "07:30", "09:20", "EMG129005"),
    ("sexta",   "15:40", "17:30", "BCD029008"),
]

# Mapeia para weekday()
DIAS = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6
}

def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('calendar', 'v3', credentials=creds)

def criar_eventos(service, data_inicio, data_fim):
    for dia, hora_ini, hora_fim, codigo in GRADE:
        dt = data_inicio

        codigo_reduzido = codigo[:3]  # Pega apenas os três primeiros caracteres

        # Ajusta o primeiro dia correto da semana
        while dt.weekday() != DIAS[dia]:
            dt += timedelta(days=1)

        while dt <= data_fim:
            inicio = TZ.localize(datetime.strptime(f"{dt.strftime('%Y-%m-%d')} {hora_ini}", "%Y-%m-%d %H:%M"))
            fim = TZ.localize(datetime.strptime(f"{dt.strftime('%Y-%m-%d')} {hora_fim}", "%Y-%m-%d %H:%M"))

            evento = {
                'summary': codigo_reduzido,
                'location': 'IFSC',
                'description': f"Aula {codigo_reduzido}",
                'start': {
                    'dateTime': inicio.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': fim.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
            }

            service.events().insert(calendarId='primary', body=evento).execute()
            print(f"Criado: {codigo_reduzido} em {inicio}")

            dt += timedelta(days=7)

if __name__ == '__main__':
    data_ini_str = input("Digite a data de início (dd/mm/aaaa): ").strip()
    data_fim_str = input("Digite a data de fim    (dd/mm/aaaa): ").strip()

    data_inicio = datetime.strptime(data_ini_str, "%d/%m/%Y")
    data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y")

    print("Conectando ao Google Calendar...")
    service = get_calendar_service()
    print("Criando eventos...")

    criar_eventos(service, data_inicio, data_fim)
