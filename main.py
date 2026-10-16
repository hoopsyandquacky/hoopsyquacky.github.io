import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = '1XMnpCzQgvyiXFOYcD_dFlMnedQnHUaquH44_UtJg7jQ'

def load_credentials():
    if 'TOKEN_JSON' in os.environ:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        return Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json')
    else:
        raise FileNotFoundError("Nessun token trovato.")

def get_readers_data(sheets_service):
    """Legge la lista dei lettori dal foglio Google."""
    range_name = 'Foglio1!A2:G'
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=range_name
    ).execute()
    rows = result.get('values', [])
    print(f"Righe trovate nel database lettori: {len(rows)}")
    return rows

def append_reader(sheets_service, date, email, name, lang, req_type, status, notes):
    """Aggiunge una nuova voce/richiesta al database lettori."""
    values = [[date, email, name, lang, req_type, status, notes]]
    body = {'values': values}
    result = sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Foglio1!A1',
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    print("Nuovo lettore/richiesta registrata con successo nel database.")

def main():
    print("Inizializzazione Companion Hub Hoopsy & Quacky...")
    creds = load_credentials()

    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    print("Connessione a Gmail, Drive e Sheets completata con successo!")
    
    # Verifica lettura database lettori
    get_readers_data(sheets_service)

if __name__ == '__main__':
    main()
