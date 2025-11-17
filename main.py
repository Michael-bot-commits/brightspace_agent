"""
Orchestrateur principal - Multi-comptes avec notifications et système de retry
Gère le scraping de plusieurs comptes et l'envoi de notifications
"""
import sys
import os
import time
from datetime import datetime
from typing import Dict, List

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.accounts import ACCOUNTS, validate_config
from modules.scraper import BrightspaceScraper
from modules.database import Database
from modules.notifier import notifier
from modules.auth_manager import AuthManager
from utils.logger import logger


class MultiAccountManager:
    """Gère le scraping et les notifications pour plusieurs comptes"""
    
    def __init__(self):
        """Initialise le gestionnaire multi-comptes"""
        if not validate_config():
            sys.exit(1)
        
        logger.info("="*60)
        logger.info("🚀 BRIGHTSPACE AGENT - MULTI-COMPTES")
        logger.info("="*60)
    
    def process_account_with_retry(self, account: Dict, max_retries: int = 3) -> Dict:
        """
        Traite un compte avec système de retry automatique
        
        Args:
            account: Configuration du compte
            max_retries: Nombre maximum de tentatives
        
        Returns:
            Dict: Résultats du traitement
        """
        retry_delays = [30, 60, 90]  # Délais progressifs en secondes
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"🔄 Tentative {attempt}/{max_retries}")
            
            # Supprimer les cookies avant retry (sauf première tentative)
            if attempt > 1:
                logger.info(f"🧹 Nettoyage: Suppression des cookies pour nouveau login...")
                if os.path.exists(account['cookies_file']):
                    try:
                        os.remove(account['cookies_file'])
                        logger.info(f"✅ Cookies supprimés: {account['cookies_file']}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur suppression cookies: {e}")
            
            # Tenter le scraping
            result = self.process_account(account)
            
            # Vérifier si le scraping a réussi
            if result['status'] == 'success' and result['total'] > 0:
                logger.info(f"✅ Scraping réussi à la tentative {attempt}/{max_retries}")
                return result
            
            # Si échec et pas la dernière tentative
            if attempt < max_retries:
                delay = retry_delays[attempt - 1]
                logger.warning(f"⚠️ Tentative {attempt}/{max_retries} échouée (0 cours trouvés)")
                logger.info(f"⏳ Attente de {delay} secondes avant retry...")
                time.sleep(delay)
            else:
                # Dernière tentative échouée
                logger.error(f"❌ Échec après {max_retries} tentatives pour {account['name']}")
                logger.error(f"❌ Aucun cours trouvé malgré les retries")
        
        # Retourner le dernier résultat (échec)
        return result
    
    def process_account(self, account: Dict) -> Dict:
        """
        Traite un compte: scraping + notifications
        
        Args:
            account: Configuration du compte
        
        Returns:
            Dict: Résultats du traitement
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"👤 COMPTE: {account['name']}")
        logger.info(f"{'='*60}")
        
        try:
            # Créer les dossiers si nécessaire
            account_dir = os.path.dirname(account['cookies_file'])
            os.makedirs(account_dir, exist_ok=True)
            
            # Initialiser scraper et DB pour ce compte
            auth_manager = AuthManager(
                username=account['brightspace_username'],
                password=account['brightspace_password'],
                cookies_file=account['cookies_file']
            )
            
            db = Database(account['db_file'])
            
            scraper = BrightspaceScraper(
                auth_manager=auth_manager,
                home_url="https://login.collegeboreal.ca/?app=BS"
            )
            
            # Récupérer les travaux AVANT scraping (pour comparaison)
            old_assignments = db.get_all_assignments()
            old_ids = {a['id'] for a in old_assignments}
            
            # SCRAPING avec nettoyage intelligent
            logger.info("🔄 Démarrage du scraping...")
            result = scraper.sync_to_database(db)
            
            # Récupérer les travaux APRÈS scraping
            new_assignments = db.get_all_assignments()
            pending_assignments = db.get_pending_assignments()
            
            # DÉTECTION DES NOUVEAUX TRAVAUX
            new_ids = {a['id'] for a in new_assignments}
            truly_new_ids = new_ids - old_ids
            truly_new = [a for a in new_assignments if a['id'] in truly_new_ids]
            
            logger.info(f"📊 Résumé:")
            logger.info(f"   Travaux détectés: {len(new_assignments)}")
            logger.info(f"   Nouveaux: {len(truly_new)}")
            logger.info(f"   À faire: {len(pending_assignments)}")
            
            # NOTIFICATIONS (si activées)
            if account['notifications']['enabled']:
                self._send_notifications(account, truly_new, pending_assignments)
            else:
                logger.info("📧 Notifications désactivées pour ce compte")
            
            return {
                'status': 'success',
                'account': account['name'],
                'total': len(new_assignments),
                'new': len(truly_new),
                'pending': len(pending_assignments)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement compte {account['name']}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            return {
                'status': 'error',
                'account': account['name'],
                'total': 0,
                'error': str(e)
            }
    
    def _send_notifications(self, account: Dict, new_assignments: List[Dict], 
                           pending_assignments: List[Dict]):
        """Envoie les notifications appropriées"""
        config = account['notifications']
        
        # Vérifier si on utilise la fusion intelligente
        use_smart_fusion = config.get('smart_fusion', False)
        
        if use_smart_fusion:
            # ============================================
            # NOUVELLE MÉTHODE : FUSION INTELLIGENTE
            # ============================================
            logger.info("📧 Utilisation de la fusion intelligente des notifications")
            
            # Calculer les travaux urgents
            urgent_threshold = config['urgent_threshold']
            urgent_assignments = []
            
            for assignment in pending_assignments:
                if assignment['due_date']:
                    due_date = datetime.fromisoformat(assignment['due_date'])
                    hours_left = (due_date - datetime.now()).total_seconds() / 3600
                    
                    if 0 < hours_left < urgent_threshold:
                        urgent_assignments.append(assignment)
            
            # Déterminer le moment de la journée
            current_time = datetime.now().strftime('%H:%M')
            time_of_day = None
            
            if (config['morning_summary'] and 
                current_time == config['morning_summary_time']):
                time_of_day = 'morning'
                logger.info("☀️ Heure du résumé matin détectée")
            elif (config['evening_summary'] and 
                  current_time == config['evening_summary_time']):
                time_of_day = 'evening'
                logger.info("🌙 Heure du résumé soir détectée")
            
            # Envoi d'une seule notification intelligente
            result = notifier.send_smart_notification(
                account_name=account['name'],
                to_email=account['email_recipient'],
                new_assignments=new_assignments,
                urgent_assignments=urgent_assignments,
                all_assignments=pending_assignments,
                time_of_day=time_of_day
            )
            
            if result:
                logger.info("✅ Notification intelligente envoyée avec succès")
            else:
                logger.info("ℹ️ Aucune notification à envoyer")
        
        else:
            # ============================================
            # ANCIENNE MÉTHODE : NOTIFICATIONS SÉPARÉES
            # ============================================
            logger.info("📧 Utilisation du mode notifications séparées")
            
            current_time = datetime.now().strftime('%H:%M')
            
            # TYPE 1: Nouveaux travaux
            if config['new_assignments'] and new_assignments:
                logger.info(f"📧 Envoi notification nouveaux travaux ({len(new_assignments)})...")
                notifier.notify_new_assignments(
                    account['name'],
                    account['email_recipient'],
                    new_assignments
                )
            
            # TYPE 2: Travaux urgents (< threshold heures)
            urgent_threshold = config['urgent_threshold']
            urgent_assignments = []
            
            for assignment in pending_assignments:
                if assignment['due_date']:
                    due_date = datetime.fromisoformat(assignment['due_date'])
                    hours_left = (due_date - datetime.now()).total_seconds() / 3600
                    
                    if 0 < hours_left < urgent_threshold:
                        urgent_assignments.append(assignment)
            
            if urgent_assignments:
                logger.info(f"📧 Envoi alerte urgence ({len(urgent_assignments)} travaux < {urgent_threshold}h)...")
                notifier.notify_urgent_assignments(
                    account['name'],
                    account['email_recipient'],
                    urgent_assignments
                )
            
            # TYPE 3: Résumé du matin
            if config['morning_summary'] and current_time == config['morning_summary_time']:
                logger.info(f"📧 Envoi résumé du matin...")
                notifier.send_morning_summary(
                    account['name'],
                    account['email_recipient'],
                    pending_assignments
                )
            
            # TYPE 4: Résumé du soir
            if config['evening_summary'] and current_time == config['evening_summary_time']:
                logger.info(f"📧 Envoi résumé du soir...")
                notifier.send_evening_summary(
                    account['name'],
                    account['email_recipient'],
                    pending_assignments
                )
    
    def run(self):
        """Traite tous les comptes configurés"""
        start_time = datetime.now()
        results = []
        
        for account in ACCOUNTS:
            # Utiliser process_account_with_retry au lieu de process_account
            result = self.process_account_with_retry(account, max_retries=3)
            results.append(result)
        
        # Résumé final
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ SYNCHRONISATION TERMINÉE")
        logger.info(f"{'='*60}")
        logger.info(f"   Durée totale: {duration:.1f} secondes")
        logger.info(f"   Comptes traités: {len(results)}")
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        logger.info(f"   Succès: {success_count}/{len(results)}")
        
        for result in results:
            if result['status'] == 'success':
                logger.info(f"\n   📊 {result['account']}:")
                logger.info(f"      Nouveaux travaux: {result['new']}")
                logger.info(f"      À faire: {result['pending']}")
            else:
                logger.error(f"\n   ❌ {result['account']}: {result.get('error', 'Erreur inconnue')}")
        
        logger.info(f"\n{'='*60}\n")


def main():
    """Point d'entrée principal"""
    manager = MultiAccountManager()
    manager.run()


if __name__ == "__main__":
    main()