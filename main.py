import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ID del nuovo Google Sheet appartenente a hoopsyquacky@gmail.com
SPREADSHEET_ID = '1P_HNW-r7Lz6ygrQ6rbaCs4TTTawek8y9MtqdSgmbuus'

def load_credentials():
    """Carica le credenziali OAuth 2.0 dall'ambiente GitHub Secrets o da file locale."""
    if 'TOKEN_JSON' in os.environ:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        return Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json')
    else:
        raise FileNotFoundError("Nessun token di autenticazione trovato.")

def get_first_sheet_name(sheets_service):
    """Ottiene automaticamente il nome della prima scheda (es. Sheet1 o Foglio1)."""
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', [])
        if sheets:
            return sheets[0].get('properties', {}).get('title', 'Sheet1')
    except Exception as e:
        print(f"Avviso durante il recupero nome scheda: {e}")
    return 'Sheet1'

def get_drive_pdf_link(drive_service):
    """Recupera il link al primo PDF disponibile nella root del Drive."""
    try:
        results = drive_service.files().list(
            q="mimeType = 'application/pdf' and trashed = false",
            pageSize=5,
            fields="files(id, name, webViewLink)"
        ).execute()
        files = results.get('files', [])

        if files:
            file_info = files[0]
            print(f"File bonus individuato su Drive: {file_info['name']}")
            return file_info.get('webViewLink', 'Nessun link disponibile')
        else:
            print("Nessun PDF trovato su Drive.")
            return "File bonus non trovato"
    except Exception as e:
        print(f"Errore accesso Google Drive API: {e}")
        return "Errore accesso Drive"

def detect_language(text):
    """Rileva la lingua dell'email per la profilazione dei mercati KDP."""
    text_lower = text.lower()
    if any(w in text_lower for w in ['ciao', 'grazie', 'salve', 'libro', 'mistero', 'richiesta']):
        return 'IT'
    elif any(w in text_lower for w in ['hallo', 'danke', 'buch', 'kürbis', 'rätsel']):
        return 'DE'
    elif any(w in text_lower for w in ['bonjour', 'merci', 'livre', 'citrouille']):
        return 'FR'
    elif any(w in text_lower for w in ['hola', 'gracias', 'libro', 'calabaza']):
        return 'ES'
    elif any(w in text_lower for w in ['hej', 'tack', 'bok', 'mysterium']):
        return 'SV'
    else:
        return 'EN'

def append_reader(sheets_service, sheet_name, date, email, name, lang, req_type, status, notes):
    """Registra i dettagli del lettore nel Google Sheet."""
    values = [[date, email, name, lang, req_type, status, notes]]
    body = {'values': values}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    print(f"Nuova richiesta registrata nel database per: {email}")

def process_incoming_emails(gmail_service, drive_service, sheets_service, sheet_name):
    """Elabora le email non lette, recupera i link bonus e aggiorna il foglio."""
    try:
        # Filtra via le notifiche automatiche di GitHub
        results = gmail_service.users().messages().list(userId='me', q='is:unread -from:github.com', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print("Nessuna nuova email da elaborare al momento.")
            return

        print(f"Trovate {len(messages)} nuove email in arrivo.")

        for msg_meta in messages:
            msg = gmail_service.users().messages().get(userId='me', id=msg_meta['id']).execute()
            headers = msg.get('payload', {}).get('headers', [])

            sender = "Sconosciuto"
            subject = "Nessun oggetto"
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for h in headers:
                if h['name'].lower() == 'from':
                    sender = h['value']
                elif h['name'].lower() == 'subject':
                    subject = h['value']

            email = sender
            name = sender
            if '<' in sender and '>' in sender:
                name = sender.split('<')[0].strip(' "\'')
                email = sender.split('<')[1].replace('>', '').strip()

            subj_lower = subject.lower()
            lang = detect_language(subject)
            
            if any(w in subj_lower for w in ['bonus', 'materiale', 'pdf', 'kit', 'download', 'halloween', 'hauntville', 'richiesta', 'request']):
                req_type = 'Richiesta Materiale Bonus'
                drive_link = get_drive_pdf_link(drive_service)
                notes_text = f"Oggetto: {subject} | Link Bonus: {drive_link}"
            else:
                req_type = 'Fan Mail / Generico'
                notes_text = f"Oggetto: {subject}"

            append_reader(sheets_service, sheet_name, date_str, email, name, lang, req_type, 'Nuovo', notes_text)

            try:
                gmail_service.users().messages().batchModify(
                    userId='me',
                    body={'removeLabelIds': ['UNREAD'], 'ids': [msg_meta['id']]}
                ).execute()
            except Exception as e_label:
                print(f"Avviso: Impossibile rimuovere l'etichetta UNREAD: {e_label}")

    except Exception as e:
        print(f"Errore durante l'elaborazione delle email: {e}")

def main():
    print("Inizializzazione Companion Hub Hoopsy & Quacky...")
    creds = load_credentials()

    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    print("Connessione a Gmail, Drive e Sheets completata con successo!")

    sheet_name = get_first_sheet_name(sheets_service)
    print(f"Scheda Google Sheets rilevata: {sheet_name}")

    process_incoming_emails(gmail_service, drive_service, sheets_service, sheet_name)

if __name__ == '__main__':
    main()
