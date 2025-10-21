"""
Configuration centralisée de l'application
Charge les variables depuis .env et les rend accessibles partout
"""
import os
from dotenv import load_dotenv
from utils.logger import logger

# Charger variables d'environnement depuis .env
load_dotenv()


class Config:
    """
    Configuration globale de l'application
    Toutes les variables sont chargées depuis .env
    """
    
    # ============================================
    # PORTAIL ÉTUDIANT
    # ============================================
    PORTAL_USERNAME = os.getenv('PORTAL_USERNAME')
    PORTAL_PASSWORD = os.getenv('PORTAL_PASSWORD')
    PORTAL_LOGIN_URL = os.getenv('PORTAL_LOGIN_URL', 'https://login.collegeboreal.ca')
    PORTAL_HOME_URL = os.getenv('PORTAL_HOME_URL', 'https://mon.collegeboreal.ca')
    
    # ============================================
    # TWILIO (WhatsApp)
    # ============================================
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
    YOUR_WHATSAPP_NUMBER = os.getenv('YOUR_WHATSAPP_NUMBER')
    
    # ============================================
    # ANTHROPIC CLAUDE API
    # ============================================
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # ============================================
    # CONFIGURATION AGENT
    # ============================================
    SYNC_INTERVAL_HOURS = int(os.getenv('SYNC_INTERVAL_HOURS', 2))
    NOTIFICATION_TIME = os.getenv('NOTIFICATION_TIME', '08:00')
    CHECK_UPCOMING_DAYS = int(os.getenv('CHECK_UPCOMING_DAYS', 7))
    URGENT_THRESHOLD_HOURS = int(os.getenv('URGENT_THRESHOLD_HOURS', 48))
    
    # ============================================
    # CHEMINS FICHIERS
    # ============================================
    ENCRYPTION_KEY_FILE = os.getenv('ENCRYPTION_KEY_FILE', '.cookie_key')
    COOKIES_FILE = os.getenv('COOKIES_FILE', 'data/cookies.enc')
    DATABASE_FILE = os.getenv('DATABASE_FILE', 'data/assignments.db')
    
    # ============================================
    # MODE DEBUG
    # ============================================
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """
        Valide que toutes les configurations CRITIQUES sont présentes
        
        Returns:
            bool: True si config valide
        
        Raises:
            ValueError: Si config manquante
        """
        # Variables requises (pour l'instant juste portail)
        required = [
            ('PORTAL_USERNAME', cls.PORTAL_USERNAME),
            ('PORTAL_PASSWORD', cls.PORTAL_PASSWORD),
        ]
        
        # Variables optionnelles (pour plus tard)
        optional = [
            ('TWILIO_ACCOUNT_SID', cls.TWILIO_ACCOUNT_SID),
            ('TWILIO_AUTH_TOKEN', cls.TWILIO_AUTH_TOKEN),
            ('ANTHROPIC_API_KEY', cls.ANTHROPIC_API_KEY),
        ]
        
        missing_required = []
        missing_optional = []
        
        # Vérifier variables requises
        for var_name, var_value in required:
            if not var_value:
                missing_required.append(var_name)
        
        # Vérifier variables optionnelles
        for var_name, var_value in optional:
            if not var_value:
                missing_optional.append(var_name)
        
        # Erreur si requises manquantes
        if missing_required:
            logger.error(f"❌ Variables REQUISES manquantes dans .env: {', '.join(missing_required)}")
            raise ValueError(f"Configuration incomplète. Vérifiez votre fichier .env")
        
        # Warning si optionnelles manquantes
        if missing_optional:
            logger.warning(f"⚠️ Variables optionnelles manquantes: {', '.join(missing_optional)}")
            logger.warning("   Certaines fonctionnalités seront désactivées")
        
        logger.info("✅ Configuration validée")
        return True
    
    @classmethod
    def print_config(cls):
        """Affiche la configuration (SANS les secrets!)"""
        print("\n" + "="*60)
        print("CONFIGURATION ACTUELLE")
        print("="*60)
        
        print("\n📚 Portail Étudiant:")
        print(f"  Username: {cls.PORTAL_USERNAME}")
        print(f"  Password: {'*' * len(cls.PORTAL_PASSWORD) if cls.PORTAL_PASSWORD else 'NON CONFIGURÉ'}")
        print(f"  Login URL: {cls.PORTAL_LOGIN_URL}")
        print(f"  Home URL: {cls.PORTAL_HOME_URL}")
        
        print("\n📱 WhatsApp (Twilio):")
        print(f"  Account SID: {'Configuré ✅' if cls.TWILIO_ACCOUNT_SID else 'Non configuré ❌'}")
        print(f"  Auth Token: {'Configuré ✅' if cls.TWILIO_AUTH_TOKEN else 'Non configuré ❌'}")
        print(f"  Twilio Number: {cls.TWILIO_WHATSAPP_NUMBER or 'Non configuré'}")
        print(f"  Your Number: {cls.YOUR_WHATSAPP_NUMBER or 'Non configuré'}")
        
        print("\n🤖 Agent IA (Claude):")
        print(f"  API Key: {'Configuré ✅' if cls.ANTHROPIC_API_KEY else 'Non configuré ❌'}")
        
        print("\n⚙️ Configuration Agent:")
        print(f"  Sync Interval: Toutes les {cls.SYNC_INTERVAL_HOURS}h")
        print(f"  Notification Time: {cls.NOTIFICATION_TIME}")
        print(f"  Check Upcoming: {cls.CHECK_UPCOMING_DAYS} jours")
        print(f"  Urgent Threshold: {cls.URGENT_THRESHOLD_HOURS}h")
        
        print("\n📁 Fichiers:")
        print(f"  Encryption Key: {cls.ENCRYPTION_KEY_FILE}")
        print(f"  Cookies: {cls.COOKIES_FILE}")
        print(f"  Database: {cls.DATABASE_FILE}")
        
        print("\n🐛 Debug:")
        print(f"  Debug Mode: {cls.DEBUG}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        
        print("\n" + "="*60 + "\n")


# ============================================
# INSTANCE GLOBALE
# ============================================
config = Config()


# ============================================
# FONCTION DE TEST
# ============================================
def test_config():
    """Teste la configuration"""
    print("⚙️ Test de la configuration...\n")
    
    # Afficher config
    config.print_config()
    
    # Valider
    try:
        config.validate()
        print("✅ Configuration valide!")
    except ValueError as e:
        print(f"❌ Erreur de configuration: {e}")
        print("\n💡 Assure-toi d'avoir rempli ton fichier .env")


if __name__ == "__main__":
    test_config()