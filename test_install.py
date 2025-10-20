"""
Script de test pour vérifier que toutes les dépendances sont installées
"""

def test_imports():
    """Teste l'import de chaque package important"""
    
    print("🧪 Test des imports...")
    
    try:
        # Web scraping
        from playwright.sync_api import sync_playwright
        print("✅ Playwright OK")
        
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup OK")
        
        # API clients
        from anthropic import Anthropic
        print("✅ Anthropic OK")
        
        from twilio.rest import Client
        print("✅ Twilio OK")
        
        # Utilitaires
        import requests
        print("✅ Requests OK")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv OK")
        
        from cryptography.fernet import Fernet
        print("✅ Cryptography OK")
        
        from dateutil import parser
        print("✅ python-dateutil OK")
        
        import dateparser
        print("✅ dateparser OK")
        
        import schedule
        print("✅ schedule OK")
        
        import colorlog
        print("✅ colorlog OK")
        
        from flask import Flask
        print("✅ Flask OK")
        
        import sqlite3
        print("✅ sqlite3 OK")
        
        print("\n🎉 Tous les imports fonctionnent!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Erreur d'import: {e}")
        print("Réinstalle les dépendances: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    test_imports()