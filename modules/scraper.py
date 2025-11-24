"""
Scraper pour extraire les travaux depuis Brightspace
Navigation: Accueil → Tous les cours → Dropdown "Mes travaux" → Travaux → Extraction
VERSION FINALE - Avec gestion de la pagination (200 par page) + Multi-comptes
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime
from typing import List, Dict, Optional
import time
import re

from utils.logger import logger
from utils.data_parser import parse_date


class BrightspaceScraper:
    """
    Scraper pour extraire les travaux de tous les cours Brightspace
    """
    
    def __init__(self, auth_manager, home_url):
        """
        Initialise le scraper
        
        Args:
            auth_manager: Instance de AuthManager pour ce compte
            home_url: URL de la page d'accueil Brightspace
        """
        self.auth_manager = auth_manager
        self.home_url = home_url
        logger.debug("BrightspaceScraper initialisé")
    
    def scrape_all_assignments(self, headless=True) -> List[Dict]:
        """
        Scrape tous les travaux de tous les cours
        
        Args:
            headless: Si True, navigateur invisible
        
        Returns:
            List[Dict]: Liste de tous les travaux
        """
        logger.info("🔍 Démarrage du scraping Brightspace...")
        
        # Obtenir une session valide
        cookies = self.auth_manager.get_valid_session()
        
        if not cookies:
            logger.error("❌ Impossible d'obtenir une session valide")
            return []
        
        all_assignments = []
        
        try:
            with sync_playwright() as p:
                # Lancer le navigateur
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                
                # Ajouter les cookies de session
                cookie_list = []
                for name, data in cookies.items():
                    cookie_list.append({
                        'name': name,
                        'value': data['value'],
                        'domain': data['domain'],
                        'path': data['path']
                    })
                
                context.add_cookies(cookie_list)
                page = context.new_page()
                
                # Navigation vers page d'accueil
                logger.info(f"🏠 Navigation vers {self.home_url}")
                page.goto(self.home_url, wait_until='load', timeout=60000)
                time.sleep(3)
                
                # Fermer popup si présent
                try:
                    popup = page.locator('button:has-text("Compris")').first
                    if popup.count() > 0:
                        logger.info("Fermeture du popup...")
                        popup.click()
                        time.sleep(2)
                except:
                    pass

                # Trouver tous les cours
                logger.info("📚 Recherche des cours...")

                # Attendre que les cours se chargent (important pour Railway avec CPU limité)
                try:
                    logger.info("⏳ Attente du chargement des cours...")
                    page.wait_for_selector('.d2l-card-container', timeout=15000)
                    time.sleep(2)  # Délai supplémentaire pour s'assurer que tout est chargé
                except:
                    logger.warning("⚠️ Timeout en attente des cours, tentative de récupération...")

                course_cards = page.locator('.d2l-card-container').all()
                
                logger.info(f"📚 {len(course_cards)} cours trouvés")
                
                if len(course_cards) == 0:
                    logger.error("❌ Aucun cours trouvé")
                    browser.close()
                    return []
                
                # PARCOURIR TOUS LES COURS
                for index, course_card in enumerate(course_cards, 1):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Cours {index}/{len(course_cards)}")
                    logger.info(f"{'='*60}")
                    
                    try:
                        # Extraire le nom du cours
                        try:
                            course_name = course_card.locator('.d2l-card-link-text').inner_text()
                        except:
                            course_name = f"Cours {index}"
                        
                        logger.info(f"📖 Cours: {course_name}")
                        
                        # Clic sur le cours
                        course_link = course_card.locator('a[href^="/d2l/home/"]').first
                        
                        if course_link.count() == 0:
                            logger.warning(f"⚠️ Lien du cours introuvable")
                            continue
                        
                        logger.info("📂 Entrée dans le cours...")
                        course_link.click()
                        page.wait_for_load_state('load', timeout=60000)
                        time.sleep(3)
                        
                        # Vérifier erreur 404
                        if '404' in page.url or 'error' in page.url.lower():
                            logger.warning("⚠️ Cours inaccessible (404)")
                            page.goto(self.home_url, wait_until='load')
                            time.sleep(1)
                            continue
                        
                        # Ouvrir dropdown "Mes travaux"
                        dropdown = page.locator('button.d2l-dropdown-opener:has-text("Mes travaux")').first
                        
                        if dropdown.count() == 0:
                            logger.warning(f"⚠️ Pas de section 'Mes travaux'")
                            page.goto(self.home_url, wait_until='load')
                            time.sleep(1)
                            continue
                        
                        logger.info("📂 Ouverture du menu 'Mes travaux'...")
                        dropdown.click()
                        time.sleep(1)
                        
                        # Clic sur "Travaux"
                        travaux_link = page.locator('d2l-menu-item-link[text="Travaux"] a').first
                        
                        if travaux_link.count() == 0:
                            logger.warning(f"⚠️ Lien 'Travaux' introuvable")
                            page.goto(self.home_url, wait_until='load')
                            time.sleep(1)
                            continue
                        
                        logger.info("📋 Accès à la section Travaux...")
                        travaux_link.click()
                        page.wait_for_load_state('load', timeout=60000)
                        time.sleep(3)
                        
                        # Extraire les travaux (avec pagination)
                        course_assignments = self._extract_assignments_from_page(page, course_name)
                        
                        if course_assignments:
                            logger.info(f"✅ {len(course_assignments)} travaux trouvés")
                            all_assignments.extend(course_assignments)
                        else:
                            logger.info("ℹ️ Aucun travail dans ce cours")
                        
                        # Retour à l'accueil
                        page.goto(self.home_url, wait_until='load')
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur cours {index}: {e}")
                        try:
                            page.goto(self.home_url, wait_until='load')
                            time.sleep(1)
                        except:
                            pass
                        continue
                
                # Fermer le navigateur
                browser.close()
                
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ Scraping terminé")
                logger.info(f"   Total brut: {len(all_assignments)} travaux")
                logger.info(f"{'='*60}")
                
                return all_assignments
                
        except Exception as e:
            logger.error(f"❌ Erreur globale: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _extract_assignments_from_page(self, page, course_name: str) -> List[Dict]:
        """
        Extrait tous les travaux de la page actuelle (tableau)
        AVEC gestion de la pagination (changement à 200 par page)
        
        Args:
            page: Page Playwright
            course_name: Nom du cours
        
        Returns:
            List[Dict]: Liste des travaux trouvés
        """
        assignments = []
        
        try:
            # ÉTAPE 1 : Gestion de la pagination
            page_size_select = page.locator('select[title="Résultat par page"]').first
            
            if page_size_select.count() > 0:
                current_option = page_size_select.locator('option[selected]').first
                
                if current_option.count() > 0:
                    current_value = current_option.get_attribute('value')
                    logger.debug(f"   📄 Résultats par page actuel: {current_value}")
                    
                    if current_value != "200":
                        logger.info("   🔄 Changement à 200 par page...")
                        
                        try:
                            page_size_select.select_option("200")
                            page.wait_for_load_state('load', timeout=60000)
                            time.sleep(2)
                            logger.info("   ✅ Page rechargée avec 200 travaux/page")
                        
                        except Exception as e:
                            logger.warning(f"   ⚠️ Impossible de changer la taille: {e}")
                    else:
                        logger.info("   ✅ Déjà sur 200 par page")
                else:
                    logger.debug("   ℹ️ Pas d'option sélectionnée détectée")
            else:
                logger.debug("   ℹ️ Pas de dropdown pagination")
            
            # ÉTAPE 2 : Extraction des travaux
            rows = page.locator('tr:has(th.d2l-table-cell-first)').all()
            
            logger.info(f"📋 {len(rows)} lignes trouvées")
            
            # Ignorer les 2 premières lignes (en-têtes)
            if len(rows) > 2:
                rows = rows[2:]
                logger.info(f"✂️ 2 lignes d'en-tête ignorées, {len(rows)} travaux à traiter")
            else:
                logger.warning(f"⚠️ Tableau trop court ({len(rows)} lignes)")
                return []
            
            # Extraire chaque travail
            for row in rows:
                try:
                    full_text = row.inner_text()
                    assignment = self._parse_assignment_text(full_text, course_name, page.url)
                    
                    if assignment:
                        assignments.append(assignment)
                        status_emoji = "✅" if assignment['is_completed'] else "📋"
                        logger.debug(f"  {status_emoji} {assignment['title']} - {assignment['status']}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'extraire un travail: {e}")
                    continue
            
            return assignments
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _parse_assignment_text(self, text: str, course_name: str, page_url: str) -> Optional[Dict]:
        """
        Parse le texte d'une ligne de travail
        
        Args:
            text: Texte brut de la ligne
            course_name: Nom du cours
            page_url: URL de la page
        
        Returns:
            Dict ou None
        """
        try:
            full_text = text
            
            # 1. Extraire le titre
            if "Échéance" in text:
                title = text.split("Échéance")[0].strip()
            elif "Disponible" in text:
                title = text.split("Disponible")[0].strip()
            else:
                words = text.split()[:3]
                title = " ".join(words)
            
            if not title or len(title) < 2:
                return None
            
            # Filtrer les titres génériques
            if title.lower() in ['travail', 'work', 'assignment', 'état', 'score']:
                logger.debug(f"   ⏭️ Titre ignoré (générique): {title}")
                return None
            
            if 'état' in title.lower() and 'achèvement' in title.lower():
                logger.debug(f"   ⏭️ Titre ignoré (en-tête): {title}")
                return None
            
            # 2. Extraire la date
            due_date = None
            is_quiz = False
            
            date_match = re.search(
                r'Échéance\s*:?\s*([a-zéû]+\.?\s+\d+\s+\d{4}\s+\d+\s*h\s*\d+)',
                full_text,
                re.IGNORECASE
            )
            
            if not date_match:
                date_match = re.search(
                    r'Disponible\s+jusqu\'au\s+([a-zéû]+\.?\s+\d+\s+\d{4}\s+\d+\s*h\s*\d+)',
                    full_text,
                    re.IGNORECASE
                )
                if date_match:
                    is_quiz = True
            
            if date_match:
                date_str = date_match.group(1)
                logger.debug(f"   📅 Date extraite: '{date_str}'")
                date_str_normalized = re.sub(r'(\d+)h(\d+)', r'\1 h \2', date_str)
                due_date = parse_date(date_str_normalized)
                
                if not due_date:
                    logger.warning(f"   ⚠️ Échec parsing de '{date_str_normalized}'")
            
            # 3. Vérifier si soumis
            is_submitted = "soumission" in full_text.lower()
            
            # 4. Extraire la note
            score = None
            total = None
            has_grade = False
            
            note_match = re.search(r'(\d+)\s*/\s*(\d+)\s*-\s*(\d+)\s*%', full_text)
            if note_match:
                score = int(note_match.group(1))
                total = int(note_match.group(2))
                has_grade = True
            
            # 5. Déterminer le statut
            is_overdue = False
            
            if due_date:
                is_overdue = due_date < datetime.now()
            
            if has_grade:
                status = "graded"
                is_completed = True
            elif is_submitted:
                status = "submitted"
                is_completed = True
            elif is_overdue:
                if is_quiz:
                    status = "missed"
                    is_completed = True
                else:
                    status = "overdue"
                    is_completed = False
            else:
                status = "pending"
                is_completed = False
            
            # 6. Construire l'objet
            assignment_id = f"{course_name}_{title}".replace(" ", "_").replace("/", "_")
            
            assignment = {
                'id': assignment_id,
                'title': title,
                'course': course_name,
                'due_date': due_date.isoformat() if due_date else None,
                'link': page_url,
                'is_completed': is_completed,
                'grade': score,
                'description': None,
                'status': status
            }
            
            return assignment
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur parsing: {e}")
            logger.debug(f"   Texte: {text[:100]}")
            return None
    
    def _filter_future_assignments(self, assignments: List[Dict]) -> List[Dict]:
        """Filtre les travaux: garde seulement ceux non complétés"""
        filtered = []
        
        for assignment in assignments:
            if not assignment['is_completed']:
                filtered.append(assignment)
                logger.debug(f"  ✅ Gardé: {assignment['title']} ({assignment['status']})")
            else:
                logger.debug(f"  ⏭️ Ignoré: {assignment['title']} - {assignment['status']}")
        
        return filtered
    
    def sync_to_database(self, db) -> Dict:
        """
        Scrape tous les travaux et synchronise avec la base de données
        AVEC NETTOYAGE INTELLIGENT
        
        Args:
            db: Instance de Database pour ce compte
        
        Returns:
            Dict: Résultats de la synchronisation
        """
        logger.info("🔄 Synchronisation avec Brightspace...")
        
        start_time = datetime.now()
        
        # 1. SCRAPING
        all_assignments = self.scrape_all_assignments(headless=True)
        
        if not all_assignments:
            logger.warning("⚠️ Aucun travail trouvé")
            db.log_sync(status='success', assignments_found=0, new=0, updated=0)
            return {'status': 'success', 'total': 0, 'new': 0, 'updated': 0, 'deleted': 0}
        
        # 2. FILTRAGE (garde seulement pending)
        pending_assignments = self._filter_future_assignments(all_assignments)
        
        logger.info(f"\n📊 Filtrage:")
        logger.info(f"   Total trouvés: {len(all_assignments)}")
        logger.info(f"   À conserver: {len(pending_assignments)}")
        logger.info(f"   Ignorés (complétés): {len(all_assignments) - len(pending_assignments)}")
        
        # 3. NETTOYAGE INTELLIGENT DE LA DB
        current_ids = {a['id'] for a in pending_assignments}
        db_assignments = db.get_all_assignments()
        
        deleted_count = 0
        for db_assignment in db_assignments:
            db_id = db_assignment['id']
            
            if db_id not in current_ids:
                # Travail n'est plus détecté
                # On supprime SEULEMENT si marqué completed
                if db_assignment.get('is_completed', False):
                    db.delete_assignment(db_id)
                    logger.info(f"🗑️ Supprimé (complété): {db_assignment['title']}")
                    deleted_count += 1
                else:
                    logger.warning(f"⚠️ Travail non détecté mais gardé: {db_assignment['title']}")
        
        # 4. SAUVEGARDE/MISE À JOUR
        new_count = 0
        updated_count = 0
        
        for assignment in pending_assignments:
            is_new = db.save_assignment(assignment)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
        
        # 5. LOG
        db.log_sync(
            status='success',
            assignments_found=len(pending_assignments),
            new=new_count,
            updated=updated_count
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ Sync: {len(pending_assignments)} travaux ({new_count} nouveaux, {updated_count} MàJ, {deleted_count} supprimés)")
        logger.info(f"   Durée: {duration:.1f}s")
        
        return {
            'status': 'success',
            'total': len(pending_assignments),
            'new': new_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'duration': duration
        }