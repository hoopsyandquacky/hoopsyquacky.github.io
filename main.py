import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ID del Google Sheet appartenente a hoopsyquacky@gmail.com
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
    """Ottiene automaticamente il nome della prima scheda del foglio (es. Sheet1)."""
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', [])
        if sheets:
            return sheets[0].get('properties', {}).get('title', 'Sheet1')
    except Exception as e:
        print(f"Avviso durante il recupero nome scheda: {e}")
    return 'Sheet1'

def scan_drive_for_bonus(drive_service, search_query_text=""):
    """Scansiona Google Drive e restituisce il link del primo file PDF utile con fallback intelligente."""
    try:
        results = drive_service.files().list(
            q="mimeType = 'application/pdf' and trashed = false",
            orderBy="createdTime desc",
            fields="files(id, name, webViewLink)",
            pageSize=10
        ).execute()
        files = results.get('files', [])

        if not files:
            print("Nessun PDF trovato su Google Drive.")
            return "Nessun file bonus trovato"

        query_lower = search_query_text.lower()
        
        # 1. Cerca una corrispondenza mirata basata sul nome del file
        for file in files:
            file_name_lower = file['name'].lower()
            keywords = [w for w in file_name_lower.replace('_', ' ').replace('-', ' ').split() if len(w) > 3]
            if any(kw in query_lower for kw in keywords):
                print(f"Trovata corrispondenza mirata su Drive: {file['name']}")
                return file.get('webViewLink', 'Nessun link disponibile')

        # 2. Fallback intelligente: restituisce il PDF più recente disponibile
        fallback_file = files[0]
        print(f"Nessun match stretto, assegnato l'ultimo PDF caricato: {fallback_file['name']}")
        return fallback_file.get('webViewLink', 'Nessun link disponibile')

    except Exception as e:
        print(f"Errore durante la scansione di Google Drive: {e}")
        return "Errore scansione Drive"

def detect_language(text):
    """Rileva la lingua dell'email per la profilazione nei mercati KDP."""
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
    """Aggiunge la richiesta al database Google Sheets."""
    values = [[date, email, name, lang, req_type, status, notes]]
    body = {'values': values}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{sheet_name}!A1',
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    print(f"Nuova richiesta registrata nel foglio per: {email}")

def process_incoming_emails(gmail_service, drive_service, sheets_service, sheet_name):
    """Elabora le email non lette, scansiona Drive e aggiorna il foglio."""
    try:
        # Esclude le notifiche di sistema da GitHub
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
            
            if any(w in subj_lower for w in ['bonus', 'materiale', 'pdf', 'kit', 'download', 'halloween', 'hauntville', 'richiesta', 'request', 'christmas', 'natale']):
                req_type = 'Richiesta Materiale Bonus'
                drive_link = scan_drive_for_bonus(drive_service, search_query_text=subject)
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
