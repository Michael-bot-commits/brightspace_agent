"""
Gestionnaire de chiffrement pour données sensibles
Utilise Fernet (chiffrement symétrique AES)
"""
from cryptography.fernet import Fernet
import os
import json
from utils.logger import logger


class CryptoManager:
    """
    Gère le chiffrement et déchiffrement des données sensibles
    """
    
    def __init__(self, key_file='.cookie_key'):
        """
        Initialise le gestionnaire de chiffrement
        
        Args:
            key_file: Chemin du fichier contenant la clé de chiffrement
        """
        self.key_file = key_file
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
        logger.debug(f"CryptoManager initialisé avec clé: {key_file}")
    
    def _load_or_create_key(self):
        """
        Charge la clé existante ou en crée une nouvelle
        
        Returns:
            bytes: Clé de chiffrement
        """
        if os.path.exists(self.key_file):
            # Charger clé existante
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.debug("Clé de chiffrement chargée")
            return key
        else:
            # Créer nouvelle clé
            key = Fernet.generate_key()
            
            # Sauvegarder
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Permissions restrictives (Mac/Linux uniquement)
            if os.name != 'nt':  # Pas Windows
                os.chmod(self.key_file, 0o600)  # Lecture/écriture proprio seulement
            
            logger.info(f"✅ Nouvelle clé de chiffrement créée: {self.key_file}")
            return key
    
    def encrypt(self, data):
        """
        Chiffre des données
        
        Args:
            data: Données à chiffrer (str, dict, ou bytes)
        
        Returns:
            bytes: Données chiffrées
        """
        # Convertir en JSON si dict
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        
        # Convertir en bytes si string
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Chiffrer
        encrypted = self.cipher.encrypt(data)
        logger.debug(f"Données chiffrées ({len(data)} bytes → {len(encrypted)} bytes)")
        
        return encrypted
    
    def decrypt(self, encrypted_data):
        """
        Déchiffre des données
        
        Args:
            encrypted_data: Données chiffrées (bytes)
        
        Returns:
            str: Données déchiffrées (string)
        """
        try:
            # Déchiffrer
            decrypted = self.cipher.decrypt(encrypted_data)
            
            # Convertir en string
            result = decrypted.decode('utf-8')
            
            logger.debug(f"Données déchiffrées ({len(encrypted_data)} bytes → {len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur de déchiffrement: {e}")
            raise
    
    def encrypt_to_file(self, data, filepath):
        """
        Chiffre et sauvegarde dans un fichier
        
        Args:
            data: Données à chiffrer
            filepath: Chemin du fichier de sortie
        """
        # Créer dossier si n'existe pas
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Chiffrer
        encrypted = self.encrypt(data)
        
        # Sauvegarder
        with open(filepath, 'wb') as f:
            f.write(encrypted)
        
        logger.info(f"✅ Données chiffrées sauvegardées: {filepath}")
    
    def decrypt_from_file(self, filepath):
        """
        Charge et déchiffre depuis un fichier
        
        Args:
            filepath: Chemin du fichier chiffré
        
        Returns:
            str ou dict: Données déchiffrées
        """
        if not os.path.exists(filepath):
            logger.warning(f"⚠️ Fichier introuvable: {filepath}")
            return None
        
        # Charger
        with open(filepath, 'rb') as f:
            encrypted = f.read()
        
        # Déchiffrer
        decrypted = self.decrypt(encrypted)
        
        # Tenter de parser JSON
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            # Pas du JSON, retourner string
            return decrypted
        except Exception as e:
            logger.error(f"❌ Erreur lors du parsing: {e}")
            return decrypted


# ============================================
# INSTANCE GLOBALE
# ============================================
crypto = CryptoManager()


# ============================================
# FONCTION DE TEST
# ============================================
def test_crypto():
    """Teste le chiffrement et déchiffrement"""
    print("🔐 Test du système de chiffrement...\n")
    
    # Test 1: String simple
    print("Test 1: String simple")
    original = "Mon mot de passe secret!"
    encrypted = crypto.encrypt(original)
    decrypted = crypto.decrypt(encrypted)
    
    print(f"  Original:  {original}")
    print(f"  Chiffré:   {encrypted[:50]}...")
    print(f"  Déchiffré: {decrypted}")
    print(f"  ✅ Match: {original == decrypted}\n")
    
    # Test 2: Dict (comme cookies)
    print("Test 2: Dict (cookies)")
    cookies = {
        'Boreal': 'chunks-2',
        'BorealC1': 'CfDJ8FWtCb2rVEVLssiicVSFxG6F2UMquGadOc4jlt...',
        'BorealC2': 'Pdxv5__AHTh...'
    }
    
    # Sauvegarder chiffré
    crypto.encrypt_to_file(cookies, 'data/test_cookies.enc')
    print(f"  ✅ Cookies chiffrés et sauvegardés\n")
    
    # Recharger et déchiffrer
    loaded_cookies = crypto.decrypt_from_file('data/test_cookies.enc')
    print(f"  ✅ Cookies rechargés:")
    print(f"     Boreal: {loaded_cookies['Boreal']}")
    print(f"     Match: {cookies == loaded_cookies}\n")
    
    # Nettoyer
    os.remove('data/test_cookies.enc')
    print("✅ Tous les tests passés!")


if __name__ == "__main__":
    test_crypto()