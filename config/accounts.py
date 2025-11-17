"""
Configuration des comptes Brightspace - Multi-comptes
Utilise les variables d'environnement pour Railway
"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def get_account_config(account_num):
    """Récupère la config d'un compte depuis les variables d'environnement"""
    return {
        'id': f'account{account_num}',
        'name': os.getenv(f'ACCOUNT_NAME_{account_num}', f'Account{account_num}'),
        'brightspace_username': os.getenv(f'BRIGHTSPACE_USERNAME_{account_num}'),
        'brightspace_password': os.getenv(f'BRIGHTSPACE_PASSWORD_{account_num}'),
        'email_recipient': os.getenv(f'EMAIL_RECIPIENT_{account_num}'),
        'cookies_file': f'data/account{account_num}/cookies.enc',
        'db_file': f'data/account{account_num}/assignments.db',
        'notifications': {
            'enabled': os.getenv(f'NOTIFICATIONS_ENABLED_{account_num}', 'true').lower() == 'true',
            'smart_fusion': os.getenv(f'SMART_FUSION_{account_num}', 'true').lower() == 'true',
            'new_assignments': True,
            'urgent_threshold': int(os.getenv(f'URGENT_THRESHOLD_{account_num}', '24')),
            'morning_summary': os.getenv(f'MORNING_SUMMARY_{account_num}', 'true').lower() == 'true',
            'morning_summary_time': os.getenv(f'MORNING_TIME_{account_num}', '08:00'),
            'evening_summary': os.getenv(f'EVENING_SUMMARY_{account_num}', 'true').lower() == 'true',
            'evening_summary_time': os.getenv(f'EVENING_TIME_{account_num}', '22:00')
        }
    }

# Construire la liste des comptes actifs
ACCOUNTS = []
account_num = 1

while True:
    username = os.getenv(f'BRIGHTSPACE_USERNAME_{account_num}')
    if not username:
        break

    ACCOUNTS.append(get_account_config(account_num))
    account_num += 1

# Configuration email globale
EMAIL_CONFIG = {
    'sender': os.getenv('EMAIL_SENDER'),
    'password': os.getenv('EMAIL_PASSWORD')
}

def validate_config():
    """Valide la configuration"""
    if not EMAIL_CONFIG['sender'] or not EMAIL_CONFIG['password']:
        print("❌ Erreur: EMAIL_SENDER ou EMAIL_PASSWORD manquant")
        return False

    if not ACCOUNTS:
        print("❌ Erreur: Aucun compte configuré")
        return False

    for account in ACCOUNTS:
        if not account['brightspace_username'] or not account['brightspace_password']:
            print(f"❌ Erreur: Identifiants manquants pour {account['name']}")
            return False
        if not account['email_recipient']:
            print(f"❌ Erreur: Email destinataire manquant pour {account['name']}")
            return False

    print(f"✅ Configuration valide: {len(ACCOUNTS)} compte(s) configuré(s)")
    return True