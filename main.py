import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

# ID del Google Sheet appartenente a hoopsyquacky@gmail.com
SPREADSHEET_ID = '1P_HNW-r7Lz6ygrQ6rbaCs4TTTawek8y9MtqdSgmbuus'

# Mappa ufficiale dei materiali bonus condivisi su Google Drive
BONUS_MATERIALS = {
    'halloween': 'https://drive.google.com/file/d/1p_LuF491q_P2f8qUQor30G1X2Fpk2ylt/view?usp=sharing',
    'christmas': 'https://drive.google.com/file/d/1lDWwQqzpFI45kRq0SlWK23TasL-PQbLX/view?usp=sharing',
    'default': 'https://drive.google.com/file/d/1p_LuF491q_P2f8qUQor30G1X2Fpk2ylt/view?usp=sharing'
}

# Messaggi di risposta multilingua
EMAIL_TEMPLATES = {
    'IT': {
        'subject': 'Il tuo materiale bonus di Hoopsy & Quacky!',
        'body': "Ciao!\n\nGrazie mille per aver scaricato il nostro libro! Ecco il link per accedere subito al tuo materiale bonus:\n\n{link}\n\nBuon divertimento da Hoopsy, Quacky e tutto il team!\n\n---\nHoopsy & Quacky Companion Hub"
    },
    'EN': {
        'subject': 'Your Hoopsy & Quacky Bonus Material!',
        'body': "Hello!\n\nThank you so much for downloading our book! Here is the link to access your bonus material right away:\n\n{link}\n\nHave fun from Hoopsy, Quacky and the team!\n\n---\nHoopsy & Quacky Companion Hub"
    },
    'DE': {
        'subject': 'Dein Hoopsy & Quacky Bonusmaterial!',
        'body': "Hallo!\n\nVielen Dank, dass du unser Buch heruntergeladen hast! Hier ist der Link zu deinem Bonusmaterial:\n\n{link}\n\nViel Spaß wünschen Hoopsy, Quacky und das Team!\n\n---\nHoopsy & Quacky Companion Hub"
    },
    'FR': {
        'subject': 'Votre matériel bonus Hoopsy & Quacky !',
        'body': "Bonjour !\n\nMerci beaucoup d'avoir téléchargé notre livre ! Voici le lien pour accéder à votre matériel bonus :\n\n{link}\n\nBon amusement avec Hoopsy, Quacky et toute l'équipe !\n\n---\nHoopsy & Quacky Companion Hub"
    },
    'ES': {
        'subject': '¡Tu material bonus de Hoopsy & Quacky!',
        'body': "¡Hola!\n\n¡Muchas gracias por descargar nuestro libro! Aquí tienes el enlace para acceder a tu material bonus:\n\n{link}\n\n¡Que te diviertas de parte de Hoopsy, Quacky y el equipo!\n\n---\nHoopsy & Quacky Companion Hub"
    },
    'SV': {
        'subject': 'Ditt bonusmaterial från Hoopsy & Quacky!',
        'body': "Hej!\n\nTack så mycket för att du laddade ner vår bok! Här är länken för att komma åt ditt bonusmaterial:\n\n{link}\n\nHa så kul önskar Hoopsy, Quacky och teamet!\n\n---\nHoopsy & Quacky Companion Hub"
    }
}

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

def get_bonus_link(subject_text):
    """Seleziona il link bonus in base alle parole chiave presenti nell'oggetto."""
    subject_lower = subject_text.lower()
    if 'christmas' in subject_lower or 'natale' in subject_lower:
        return BONUS_MATERIALS['christmas']
    elif 'halloween' in subject_lower or 'hauntville' in subject_lower or 'mistero' in subject_lower:
        return BONUS_MATERIALS['halloween']
    return BONUS_MATERIALS['default']

def detect_language(text):
    """Rileva la lingua dell'email per la profilazione e la risposta automatica."""
    text_lower = text.lower()
    if any(w in text_lower for w in ['hallo', 'danke', 'buch', 'kürbis', 'rätsel']):
        return 'DE'
    elif any(w in text_lower for w in ['bonjour', 'merci', 'livre', 'citrouille']):
        return 'FR'
    elif any(w in text_lower for w in ['hola', 'gracias', 'libro', 'calabaza']):
        return 'ES'
    elif any(w in text_lower for w in ['hej', 'tack', 'bok', 'mysterium']):
        return 'SV'
    elif any(w in text_lower for w in ['ciao', 'grazie', 'salve', 'libro', 'mistero', 'richiesta', 'natale']):
        return 'IT'
    else:
        return 'EN'

def send_auto_response(gmail_service, to_email, lang, drive_link):
    """Invia un'email automatica al lettore con il link del materiale bonus nella sua lingua."""
    template = EMAIL_TEMPLATES.get(lang, EMAIL_TEMPLATES['EN'])
    subject = template['subject']
    body = template['body'].format(link=drive_link)

    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        print(f"Email di risposta automatica inviata con successo a: {to_email} [{lang}]")
    except Exception as e:
        print(f"Errore durante l'invio dell'email automatica: {e}")

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

def process_incoming_emails(gmail_service, sheets_service, sheet_name):
    """Elabora le email non lette, assegna il link, risponde in automatico e aggiorna il foglio."""
    try:
        # Esclude le notifiche di sistema da GitHub
        results = gmail_service.users().messages().list(userId='me', q='is:unread -from:github.com', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print("Nessuna nueva email da elaborare al momento.")
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
                drive_link = get_bonus_link(subject)
                notes_text = f"Oggetto: {subject} | Link Bonus: {drive_link}"
                
                # Invia l'email automatica al lettore
                send_auto_response(gmail_service, email, lang, drive_link)
            else:
                req_type = 'Fan Mail / Generico'
                notes_text = f"Oggetto: {subject}"

            append_reader(sheets_service, sheet_name, date_str, email, name, lang, req_type, 'Completato', notes_text)

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
    sheets_service = build('sheets', 'v4', credentials=creds)

    print("Connessione a Gmail e Sheets completata con successo!")

    sheet_name = get_first_sheet_name(sheets_service)
    print(f"Scheda Google Sheets rilevata: {sheet_name}")

    process_incoming_emails(gmail_service, sheets_service, sheet_name)

if __name__ == '__main__':
    main()
