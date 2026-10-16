import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def load_credentials():
    # Se eseguito su GitHub Actions, usa i Secrets
    if 'TOKEN_JSON' in os.environ:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        return Credentials.from_authorized_user_info(token_info)
    # Se eseguito in locale, legge il file token.json
    elif os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json')
    else:
        raise FileNotFoundError("Nessun token trovato. Esegui prima auth.py in locale.")

def main():
    print("Inizializzazione Companion Hub Hoopsy & Quacky...")
    creds = load_credentials()

    # Inizializzazione servizi Google
    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    print("Connessione a Gmail, Drive e Sheets completata con successo!")

if __name__ == '__main__':
    main()
