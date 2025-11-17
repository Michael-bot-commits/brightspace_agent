"""
Gestionnaire d'authentification pour le portail Collège Boréal
Automatise le login et gère les cookies de session
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from cryptography.fernet import Fernet
from environs import Env

from utils.logger import logger

env = Env()
env.read_env()


class AuthManager:
    """
    Gère l'authentification automatique au portail étudiant
    """
    
    def __init__(self, username: str, password: str, cookies_file: str):
        """
        Initialise le gestionnaire d'authentification
        
        Args:
            username: Nom d'utilisateur Brightspace
            password: Mot de passe
            cookies_file: Chemin vers le fichier de cookies chiffrés
        """
        self.username = username
        self.password = password
        self.login_url = "https://login.collegeboreal.ca"
        self.cookies_file = cookies_file
        
        # Clé de chiffrement
        self.encryption_key = env.str('ENCRYPTION_KEY').encode()
        self.cipher = Fernet(self.encryption_key)
        
        logger.debug(f"AuthManager initialisé pour {username}")
    
    def get_valid_session(self) -> Optional[Dict]:
        """
        Retourne une session valide (cookies)
        Vérifie d'abord si cookies existants sont valides, sinon reconnecte
        
        Returns:
            Dict: Cookies de session ou None
        """
        logger.info("🔍 Récupération d'une session valide...")
        
        # Essayer de charger les cookies existants
        cookies = self._load_cookies()
        
        if cookies and self._verify_session(cookies):
            logger.info("✅ Session existante valide")
            return cookies
        
        logger.info("⚠️ Cookies existants invalides, nouveau login requis")
        
        # Nouvelle connexion
        return self._new_login()
    
    def _load_cookies(self) -> Optional[Dict]:
        """Charge les cookies depuis le fichier chiffré"""
        if not os.path.exists(self.cookies_file):
            logger.debug(f"Pas de cookies existants: {self.cookies_file}")
            return None
        
        try:
            with open(self.cookies_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            cookies = json.loads(decrypted_data.decode())
            
            logger.info(f"✅ Cookies chargés depuis {self.cookies_file}")
            return cookies
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement cookies: {e}")
            return None
    
    def _save_cookies(self, cookies: Dict):
        """Sauvegarde les cookies de manière chiffrée"""
        try:
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            
            # Chiffrer les cookies
            cookies_json = json.dumps(cookies).encode()
            encrypted_data = self.cipher.encrypt(cookies_json)
            
            # Sauvegarder
            with open(self.cookies_file, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"✅ Cookies sauvegardés (chiffrés): {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde cookies: {e}")
    
    def _verify_session(self, cookies: Dict) -> bool:
        """
        Vérifie si les cookies sont encore valides
        
        Args:
            cookies: Cookies à vérifier
        
        Returns:
            bool: True si valides, False sinon
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # Convertir cookies
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
                
                # Tester l'accès
                response = page.goto("https://login.collegeboreal.ca/?app=BS", 
                                    wait_until='load', 
                                    timeout=30000)
                
                time.sleep(2)
                
                # Vérifier si redirigé vers login
                is_valid = 'login' not in page.url.lower() and response.status == 200
                
                browser.close()
                
                if is_valid:
                    logger.debug("✅ Cookies valides")
                else:
                    logger.warning("⚠️ Session expirée (redirection vers login)")
                
                return is_valid
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur vérification session: {e}")
            return False
    
    def _new_login(self) -> Optional[Dict]:
        """
        Effectue une nouvelle connexion et retourne les cookies
        
        Returns:
            Dict: Cookies de session ou None
        """
        logger.info("🔐 Nouveau login requis...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                
                # Navigation vers login
                logger.info("🔐 Tentative de connexion au portail...")
                logger.info(f"Navigation vers {self.login_url}")
                page.goto(self.login_url, wait_until='load', timeout=60000)
                time.sleep(3)
                
                # Remplir le formulaire
                logger.info("Remplissage du formulaire de connexion...")
                page.fill('input[name="txtUsername"]', self.username)
                page.fill('input[name="txtPassword"]', self.password)
                time.sleep(2)
                
                # Soumettre
                logger.info("Clic sur le bouton de connexion...")
                page.click('input[type="submit"]')
                
                # Attendre redirection
                logger.info("Attente de la redirection après connexion...")
                try:
                    page.wait_for_url("**/portal/**", timeout=15000)
                    logger.info("✅ Connexion réussie")
                except PlaywrightTimeout:
                    logger.warning("⚠️ Timeout mais semble connecté")
                
                time.sleep(3)
                
                # Extraire cookies
                logger.info("Extraction des cookies de session...")
                browser_cookies = context.cookies()
                
                cookies = {}
                for cookie in browser_cookies:
                    cookies[cookie['name']] = {
                        'value': cookie['value'],
                        'domain': cookie['domain'],
                        'path': cookie['path']
                    }
                
                logger.info(f"✅ {len(cookies)} cookies extraits")
                
                # Sauvegarder
                self._save_cookies(cookies)
                
                browser.close()
                
                return cookies
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du login: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None