"""
Gestionnaire d'authentification pour le portail Collège Boréal
Automatise le login et gère les cookies de session
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from utils.logger import logger
from utils.crypto import crypto
from config import config


class AuthManager:
    """
    Gère l'authentification automatique au portail étudiant
    """
    
    def __init__(self):
        """Initialise le gestionnaire d'authentification"""
        self.username = config.PORTAL_USERNAME
        self.password = config.PORTAL_PASSWORD
        self.login_url = config.PORTAL_LOGIN_URL
        self.home_url = config.PORTAL_HOME_URL
        self.cookies_file = config.COOKIES_FILE
        
        logger.debug("AuthManager initialisé")
    
    def login(self, headless=True) -> Optional[Dict]:
        """
        Effectue le login automatique via Playwright
        
        Args:
            headless: Si True, navigateur invisible. Si False, navigateur visible.
        
        Returns:
            Dict: Cookies de session ou None si échec
        """
        logger.info("🔐 Tentative de connexion au portail...")
        
        try:
            with sync_playwright() as p:
                # ============================================
                # LANCER LE NAVIGATEUR
                # ============================================
                logger.debug(f"Lancement navigateur (headless={headless})")
                browser = p.chromium.launch(
                    headless=headless,
                    slow_mo=500 if not headless else 0  # Ralentir si visible (pour debug)
                )
                
                # Créer contexte avec user agent (sembler humain)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                
                # ============================================
                # ALLER SUR PAGE DE LOGIN
                # ============================================
                logger.info(f"Navigation vers {self.login_url}")
                page.goto(self.login_url, wait_until='networkidle', timeout=30000)
                
                # Attendre que la page charge complètement
                time.sleep(2)
                
                # ============================================
                # REMPLIR LE FORMULAIRE
                # ============================================
                logger.info("Remplissage du formulaire de connexion...")
                
                # Trouver et remplir le champ username
                # Note: Ces sélecteurs peuvent varier selon le portail
                # Tu devras peut-être les ajuster après inspection
                try:
                    # Essayer différents sélecteurs possibles
                    username_selectors = [
                        'input[name="username"]',
                        'input[name="txtUserName"]',
                        'input[type="text"]',
                        '#username',
                        '#UserName'
                    ]
                    
                    username_filled = False
                    for selector in username_selectors:
                        try:
                            page.fill(selector, self.username, timeout=3000)
                            logger.debug(f"Username rempli avec sélecteur: {selector}")
                            username_filled = True
                            break
                        except:
                            continue
                    
                    if not username_filled:
                        logger.error("❌ Impossible de trouver le champ username")
                        browser.close()
                        return None
                    
                    # Remplir password
                    password_selectors = [
                        'input[name="password"]',
                        'input[name="txtPassword"]',
                        'input[type="password"]',
                        '#password',
                        '#Password'
                    ]
                    
                    password_filled = False
                    for selector in password_selectors:
                        try:
                            page.fill(selector, self.password, timeout=3000)
                            logger.debug(f"Password rempli avec sélecteur: {selector}")
                            password_filled = True
                            break
                        except:
                            continue
                    
                    if not password_filled:
                        logger.error("❌ Impossible de trouver le champ password")
                        browser.close()
                        return None
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors du remplissage du formulaire: {e}")
                    browser.close()
                    return None
                
                # ============================================
                # CLIQUER SUR LE BOUTON DE CONNEXION
                # ============================================
                logger.info("Clic sur le bouton de connexion...")
                
                try:
                    # Sélecteurs possibles pour le bouton
                    button_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Connexion")',
                        'button:has-text("Login")',
                        'button:has-text("Se connecter")',
                        '#submit',
                        '.submit-button'
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            page.click(selector, timeout=3000)
                            logger.debug(f"Bouton cliqué avec sélecteur: {selector}")
                            button_clicked = True
                            break
                        except:
                            continue
                    
                    if not button_clicked:
                        logger.error("❌ Impossible de trouver le bouton de connexion")
                        browser.close()
                        return None
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors du clic sur le bouton: {e}")
                    browser.close()
                    return None
                
                # ============================================
                # ATTENDRE LA REDIRECTION
                # ============================================
                logger.info("Attente de la redirection après connexion...")
                
                try:
                    # Attendre qu'on soit redirigé vers le portail
                    page.wait_for_url(f"{self.home_url}*", timeout=15000)
                    logger.info(f"✅ Redirection réussie vers {page.url}")
                    
                except PlaywrightTimeout:
                    # Si timeout, vérifier si on est quand même connecté
                    current_url = page.url
                    if self.home_url in current_url or 'mon.collegeboreal.ca' in current_url:
                        logger.warning("⚠️ Timeout mais semble connecté")
                    else:
                        logger.error(f"❌ Échec de connexion. URL actuelle: {current_url}")
                        
                        # Prendre screenshot pour debug
                        page.screenshot(path='logs/login_failed.png')
                        logger.info("Screenshot sauvegardé: logs/login_failed.png")
                        
                        browser.close()
                        return None
                
                # ============================================
                # EXTRAIRE LES COOKIES
                # ============================================
                logger.info("Extraction des cookies de session...")
                
                cookies = context.cookies()
                
                # Filtrer les cookies importants
                session_cookies = {}
                important_cookie_names = ['Boreal', 'BorealC1', 'BorealC2', 'ASP.NET_SessionId', '.AspNetCore']
                
                for cookie in cookies:
                    # Garder tous les cookies du domaine collegeboreal.ca
                    if 'collegeboreal' in cookie['domain']:
                        session_cookies[cookie['name']] = {
                            'value': cookie['value'],
                            'domain': cookie['domain'],
                            'path': cookie['path'],
                            'expires': cookie.get('expires', None)
                        }
                
                logger.info(f"✅ {len(session_cookies)} cookies extraits")
                logger.debug(f"Cookies: {list(session_cookies.keys())}")
                
                # Fermer le navigateur
                browser.close()
                
                # Sauvegarder les cookies
                if session_cookies:
                    self.save_cookies(session_cookies)
                    return session_cookies
                else:
                    logger.error("❌ Aucun cookie extrait")
                    return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du login: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def save_cookies(self, cookies: Dict):
        """
        Sauvegarde les cookies de manière chiffrée
        
        Args:
            cookies: Dict des cookies à sauvegarder
        """
        try:
            # Ajouter timestamp
            cookies_with_metadata = {
                'cookies': cookies,
                'saved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            # Chiffrer et sauvegarder
            crypto.encrypt_to_file(cookies_with_metadata, self.cookies_file)
            logger.info(f"✅ Cookies sauvegardés (chiffrés): {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des cookies: {e}")
    
    def load_cookies(self) -> Optional[Dict]:
        """
        Charge les cookies sauvegardés
        
        Returns:
            Dict: Cookies ou None si pas trouvés/expirés
        """
        try:
            # Déchiffrer et charger
            data = crypto.decrypt_from_file(self.cookies_file)
            
            if not data:
                logger.info("ℹ️ Aucun cookie sauvegardé trouvé")
                return None
            
            # Vérifier expiration
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now() > expires_at:
                logger.warning("⚠️ Cookies expirés")
                return None
            
            logger.info(f"✅ Cookies chargés depuis {self.cookies_file}")
            return data['cookies']
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des cookies: {e}")
            return None
    
    def is_session_valid(self, cookies: Dict) -> bool:
        """
        Vérifie si les cookies sont toujours valides
        
        Args:
            cookies: Dict des cookies à tester
        
        Returns:
            bool: True si valides
        """
        if not cookies:
            return False
        
        try:
            import requests
            
            # Convertir cookies pour requests
            cookies_dict = {name: data['value'] for name, data in cookies.items()}
            
            # Faire une requête test vers le portail
            response = requests.get(
                self.home_url,
                cookies=cookies_dict,
                timeout=10,
                allow_redirects=False
            )
            
            # Si status 200 ou 304 = OK
            # Si redirect vers login (302/303) = Expiré
            if response.status_code in [200, 304]:
                logger.info("✅ Session valide")
                return True
            elif response.status_code in [302, 303, 307]:
                logger.warning("⚠️ Session expirée (redirection vers login)")
                return False
            else:
                logger.warning(f"⚠️ Status inattendu: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification de session: {e}")
            return False
    
    def get_valid_session(self, force_refresh=False) -> Optional[Dict]:
        """
        Retourne une session valide (charge existante ou crée nouvelle)
        
        Args:
            force_refresh: Si True, force un nouveau login même si cookies existent
        
        Returns:
            Dict: Cookies de session valides ou None
        """
        logger.info("🔍 Récupération d'une session valide...")
        
        if not force_refresh:
            # Essayer de charger cookies existants
            cookies = self.load_cookies()
            
            if cookies:
                # Vérifier s'ils sont toujours valides
                if self.is_session_valid(cookies):
                    logger.info("✅ Cookies existants valides, réutilisation")
                    return cookies
                else:
                    logger.info("⚠️ Cookies existants invalides, nouveau login requis")
        
        # Login nécessaire
        logger.info("🔐 Nouveau login requis...")
        cookies = self.login(headless=True)
        
        return cookies
    
    def logout(self):
        """Supprime les cookies sauvegardés (déconnexion)"""
        import os
        
        try:
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                logger.info("✅ Cookies supprimés (déconnexion)")
            else:
                logger.info("ℹ️ Aucun cookie à supprimer")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la déconnexion: {e}")


# ============================================
# INSTANCE GLOBALE
# ============================================
auth_manager = AuthManager()


# ============================================
# FONCTION DE TEST
# ============================================
def test_auth():
    """Teste le système d'authentification"""
    print("🔐 Test du système d'authentification...\n")
    
    print("=" * 60)
    print("IMPORTANT: Ce test va ouvrir un navigateur visible")
    print("pour que tu puisses voir le processus de connexion.")
    print("=" * 60)
    
    input("\n👉 Appuie sur ENTRÉE pour commencer le test...")
    
    # Test 1: Login avec navigateur visible
    print("\n" + "=" * 60)
    print("TEST 1: Connexion automatique (navigateur visible)")
    print("=" * 60)
    
    cookies = auth_manager.login(headless=False)
    
    if cookies:
        print(f"\n✅ Connexion réussie!")
        print(f"   Cookies extraits: {len(cookies)}")
        print(f"   Cookies: {list(cookies.keys())[:5]}...")  # Premiers 5
    else:
        print("\n❌ Échec de connexion")
        print("   Vérifie tes credentials dans .env")
        return
    
    # Test 2: Sauvegarder cookies
    print("\n" + "=" * 60)
    print("TEST 2: Sauvegarde des cookies")
    print("=" * 60)
    
    auth_manager.save_cookies(cookies)
    print("✅ Cookies sauvegardés (chiffrés)")
    
    # Test 3: Recharger cookies
    print("\n" + "=" * 60)
    print("TEST 3: Rechargement des cookies")
    print("=" * 60)
    
    loaded_cookies = auth_manager.load_cookies()
    if loaded_cookies:
        print(f"✅ Cookies rechargés: {len(loaded_cookies['cookies'])} cookies")
    else:
        print("❌ Échec du rechargement")
    
    # Test 4: Valider session
    print("\n" + "=" * 60)
    print("TEST 4: Validation de la session")
    print("=" * 60)
    
    is_valid = auth_manager.is_session_valid(cookies)
    if is_valid:
        print("✅ Session valide!")
    else:
        print("❌ Session invalide")
    
    # Test 5: get_valid_session
    print("\n" + "=" * 60)
    print("TEST 5: Récupération session valide")
    print("=" * 60)
    
    session = auth_manager.get_valid_session()
    if session:
        print("✅ Session valide obtenue")
    else:
        print("❌ Impossible d'obtenir session valide")
    
    print("\n" + "=" * 60)
    print("✅ Tests terminéss!")
    print("=" * 60)


if __name__ == "__main__":
    test_auth()