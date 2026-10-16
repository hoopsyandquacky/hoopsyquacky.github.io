import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = '1P_HNW-r7Lz6ygrQ6rbaCs4TTTawek8y9MtqdSgmbuus'

def load_credentials():
    if 'TOKEN_JSON' in os.environ:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        return Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json')
    else:
        raise FileNotFoundError("Nessun token trovato.")

def get_first_sheet_name(sheets_service):
    """Ottiene automaticamente il nome della prima scheda del foglio."""
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    if sheets:
        return sheets[0].get('properties', {}).get('title', 'Sheet1')
    return 'Sheet1'

def get_latest_drive_pdf(drive_service):
    """Recupera automaticamente il link dell'ultimo file PDF disponibile su Google Drive."""
    try:
        results = drive_service.files().list(
            q="mimeType = 'application/pdf' and trashed = false",
            orderBy="createdTime desc",
            pageSize=1,
            fields="files(id, name, webViewLink)"
        ).execute()
        files = results.get('files', [])

        if files:
            file_info = files[0]
            print(f"File bonus prelevato da Drive: {file_info['name']}")
            return file_info.get('webViewLink', 'Nessun link disponibile')
        else:
            return "Nessun PDF trovato su Drive"
    except Exception as e:
        print(f"Errore accesso Google Drive: {e}")
        return "Errore accesso Drive"

def append_reader(sheets_service, sheet_name, date, email, name, lang, req_type, status, notes):
    """Aggiunge una nuova voce/richiesta al database lettori."""
    values = [[date, email, name, lang, req_type, status, notes]]
    body = {'values': values}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    print(f"Registrata richiesta da: {email}")

def process_incoming_emails(gmail_service, drive_service, sheets_service, sheet_name):
    """Cerca nuove email non lette reali, escludendo notifiche di sistema."""
    try:
        # Filtra via le notifiche di GitHub o di sistema
        results = gmail_service.users().messages().list(userId='me', q='is:unread -from:github.com', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print("Nessuna nuova email da parte dei lettori trovata.")
            return

        print(f"Trovate {len(messages)} nuove email da elaborare.")

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
            lang = 'IT' if any(w in subj_lower for w in ['ciao', 'grazie', 'libro', 'salve', 'mistero', 'hauntville', 'richiesta']) else 'EN'
            
            if any(w in subj_lower for w in ['bonus', 'materiale', 'pdf', 'kit', 'download', 'halloween', 'hauntville', 'richiesta']):
                req_type = 'Richiesta Materiale Bonus'
                drive_link = get_latest_drive_pdf(drive_service)
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
                print(f"Avviso: Impossibile segnare come letta l'email: {e_label}")

    except Exception as e:
        print(f"Errore durante l'elaborazione: {e}")

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
