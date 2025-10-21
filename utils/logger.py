"""
Système de logging avec couleurs et rotation de fichiers
"""
import logging
import colorlog
from logging.handlers import RotatingFileHandler
import os


def setup_logger(name='brightspace-agent', log_file='logs/agent.log', level=logging.DEBUG):
    """
    Configure et retourne un logger avec:
    - Sortie console avec couleurs
    - Sortie fichier avec rotation automatique
    
    Args:
        name: Nom du logger
        log_file: Chemin du fichier de log
        level: Niveau minimum de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configuré
    """
    
    # Créer dossier logs si n'existe pas
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Créer logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Éviter duplication des handlers si logger déjà configuré
    if logger.handlers:
        return logger
    
    # ============================================
    # FORMAT CONSOLE (avec couleurs)
    # ============================================
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # ============================================
    # FORMAT FICHIER (sans couleurs)
    # ============================================
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ============================================
    # HANDLER CONSOLE
    # ============================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Montrer INFO et plus dans console
    console_handler.setFormatter(console_formatter)
    
    # ============================================
    # HANDLER FICHIER (avec rotation)
    # ============================================
    # Rotation: quand fichier atteint 5 MB, créer nouveau fichier
    # Garder max 5 fichiers (agent.log, agent.log.1, ..., agent.log.4)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Tout logger dans fichier
    file_handler.setFormatter(file_formatter)
    
    # ============================================
    # AJOUTER HANDLERS AU LOGGER
    # ============================================
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# ============================================
# INSTANCE GLOBALE
# ============================================
# Créer logger par défaut qu'on peut importer partout
logger = setup_logger()


# ============================================
# FONCTION DE TEST
# ============================================
def test_logger():
    """Teste tous les niveaux de log"""
    logger.debug("🔍 Ceci est un message DEBUG (détails techniques)")
    logger.info("ℹ️ Ceci est un message INFO (information normale)")
    logger.warning("⚠️ Ceci est un message WARNING (attention)")
    logger.error("❌ Ceci est un message ERROR (erreur)")
    logger.critical("🚨 Ceci est un message CRITICAL (fatal)")


if __name__ == "__main__":
    # Si on exécute ce fichier directement, tester le logger
    print("Test du système de logging...\n")
    test_logger()
    print("\n✅ Logs écrits dans logs/agent.log")