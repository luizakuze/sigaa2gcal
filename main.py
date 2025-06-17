from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytesseract
from PIL import Image
import cv2
import pytz
import re

# Configurações
SCOPES = ['https://www.googleapis.com/auth/calendar']
TZ = pytz.timezone('America/Sao_Paulo')

# Mapeamento de dias da semana (colunas da grade)
COLUNAS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab']
DIAS = {dia: i for i, dia in enumerate(COLUNAS)}

def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('calendar', 'v3', credentials=creds)

def converter_horario(txt):
    """Converte faixa de horário em início e fim (ex: '07:30 - 08:25')"""
    partes = re.split(r'\s*[-–]\s*', txt.strip())
    if len(partes) == 2:
        return partes[0], partes[1]
    return None, None

def extrair_grade(imagem_path):
    img = cv2.imread(imagem_path)
    if img is None:
        raise FileNotFoundError(f"Imagem '{imagem_path}' não encontrada ou inválida.")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    # Substitui hífens estranhos por traço normal
    text = text.replace('–', '-').replace('—', '-')

    linhas = text.splitlines()
    grade = []

    for linha in linhas:
        # Identifica linhas com horário do tipo "07:30 - 08:25"
        match_horario = re.match(r'^(\d{2}:\d{2})\s*[-]\s*(\d{2}:\d{2})', linha)
        if not match_horario:
            continue

        hora_ini, hora_fim = match_horario.groups()

        # Remove o horário inicial da linha e separa por múltiplos espaços
        restante = linha[match_horario.end():].strip()
        colunas = re.split(r'\s{2,}', restante)

        for i, val in enumerate(colunas):
            val = val.strip()
            if not val or val == '---' or i >= len(COLUNAS):
                continue

            dia_semana = DIAS[COLUNAS[i]]
            # Extrai somente as 3 primeiras letras maiúsculas do código
            codigo_match = re.match(r'([A-Z]{3})', val)
            if not codigo_match:
                continue
            codigo = codigo_match.group(1)
            grade.append((dia_semana, hora_ini, hora_fim, codigo))
    return grade


def criar_eventos(service, data_inicio, data_fim, grade):
    for dia, hora_ini, hora_fim, codigo in grade:
        dt = data_inicio

        # Encontra o primeiro dia correto
        while dt.weekday() != dia:
            dt += timedelta(days=1)

        while dt <= data_fim:
            inicio = TZ.localize(datetime.strptime(f"{dt.strftime('%Y-%m-%d')} {hora_ini}", "%Y-%m-%d %H:%M"))
            fim = TZ.localize(datetime.strptime(f"{dt.strftime('%Y-%m-%d')} {hora_fim}", "%Y-%m-%d %H:%M"))

            evento = {
                'summary': codigo,
                'location': 'IFSC',
                'description': f"Aula {codigo}",
                'start': {'dateTime': inicio.isoformat(), 'timeZone': 'America/Sao_Paulo'},
                'end': {'dateTime': fim.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            }

            service.events().insert(calendarId='primary', body=evento).execute()
            print(f"Criado: {codigo} em {inicio}")
            dt += timedelta(days=7)

# Execução principal
if __name__ == '__main__':
    imagem = "horarios.png"  # Certifique-se de que o arquivo está no mesmo diretório

    data_ini_str = input("Digite a data de início (dd/mm/aaaa): ").strip()
    data_fim_str = input("Digite a data de fim    (dd/mm/aaaa): ").strip()

    data_inicio = datetime.strptime(data_ini_str, "%d/%m/%Y")
    data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y")

    print("Lendo imagem...")
    grade = extrair_grade(imagem)

    print(f"{len(grade)} blocos de aula encontrados.")
    print("Conectando ao Google Calendar...")
    service = get_calendar_service()
    print("Criando eventos...")

    criar_eventos(service, data_inicio, data_fim, grade)
