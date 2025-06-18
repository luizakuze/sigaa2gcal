from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytesseract
import cv2
import pytz
import re
import os

# Configurações
SCOPES = ['https://www.googleapis.com/auth/calendar']
TZ = pytz.timezone('America/Sao_Paulo')

# Dias da semana em ordem esperada da imagem
DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']

# Converte texto de horário para tupla (inicio, fim)
def converter_horario(txt):
    txt = txt.replace('–', '-').replace('—', '-').strip()
    partes = re.split(r'\s*-\s*', txt)
    return partes if len(partes) == 2 else None

# Autentica e retorna o serviço do Google Calendar
def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('calendar', 'v3', credentials=creds)

# Lê e extrai a grade da imagem
def extrair_grade(path_img):
    if not os.path.exists(path_img):
        print(f"⚠️ Arquivo {path_img} não encontrado!")
        return []

    img = cv2.imread(path_img)
    if img is None:
        print("⚠️ Erro ao ler imagem com OpenCV.")
        return []

    # Pré-processamento para melhorar OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # OCR com Tesseract
    config = r'--psm 6 -l por'
    text = pytesseract.image_to_string(thresh, config=config)

    print("\n=== TEXTO OCR ===\n")
    print(text)
    print("\n=== FIM OCR ===\n")

    linhas = [l.strip() for l in text.splitlines() if l.strip()]
    blocos = []

    for linha in linhas:
        if re.match(r'^\d{2}:\d{2}\s*[-–]\s*\d{2}:\d{2}', linha):
            # divide por "—" ou traços grandes
            partes = [p.strip() for p in re.split(r'[—|–]+', linha) if p.strip()]
            faixa = converter_horario(partes[0]) if partes else None
            if not faixa:
                continue

            colunas = partes[1:]
            for i, val in enumerate(colunas):
                val = val.upper()
                if not val or '---' in val or i >= 7:
                    continue

                codigo = re.sub(r'[^A-Z]', '', val)[:3]  # só letras
                blocos.append((i, faixa[0], faixa[1], codigo))  # i é o dia da semana

    # Agrupa blocos consecutivos da mesma matéria
    blocos.sort()
    agrupados = []
    for bloco in blocos:
        if not agrupados:
            agrupados.append(bloco)
        else:
            d, h_ini, h_fim, cod = bloco
            d2, h2_ini, h2_fim, cod2 = agrupados[-1]
            if d == d2 and cod == cod2 and h_ini == h2_fim:
                agrupados[-1] = (d, h2_ini, h_fim, cod)
            else:
                agrupados.append(bloco)

    return agrupados

# Cria eventos no calendário com repetição semanal
def criar_eventos(service, data_inicio, data_fim, grade):
    for dia, hora_ini, hora_fim, codigo in grade:
        dt = data_inicio
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

# Execução
if __name__ == '__main__':
    data_ini_str = input("Digite a data de início (dd/mm/aaaa): ").strip()
    data_fim_str = input("Digite a data de fim    (dd/mm/aaaa): ").strip()

    data_inicio = datetime.strptime(data_ini_str, "%d/%m/%Y")
    data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y")

    print("Lendo imagem...")
    grade = extrair_grade("horarios.png")

    print(f"{len(grade)} blocos de aula encontrados.")
    print("Conectando ao Google Calendar...")
    service = get_calendar_service()
    print("Criando eventos...")
    criar_eventos(service, data_inicio, data_fim, grade)
