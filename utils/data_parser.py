"""
Utilitaires pour parser et manipuler les dates
Supporte différents formats (français, anglais, ISO)
"""
from datetime import datetime, timedelta
import dateparser
from dateutil import parser as dateutil_parser
import re

# Import flexible pour logger
try:
    from utils.logger import logger
except ModuleNotFoundError:
    from logger import logger


def parse_date(date_string):
    """
    Parse une date depuis différents formats
    
    Formats supportés:
    - "20 oct 2025 à 23h59" (français)
    - "Oct 20, 2025 at 11:59 PM" (anglais)
    - "2025-10-20T23:59:00" (ISO)
    - "20/10/2025 23:59"
    - Et bien d'autres...
    
    Args:
        date_string: String contenant une date
    
    Returns:
        datetime ou None si parsing échoue
    """
    if not date_string:
        return None
    
    logger.debug(f"Parsing date: '{date_string}'")
    
    # ============================================
    # MÉTHODE 1: dateparser (très flexible)
    # ============================================
    try:
        parsed = dateparser.parse(
            date_string,
            languages=['fr', 'en'],
            settings={
                'TIMEZONE': 'America/Toronto',
                'RETURN_AS_TIMEZONE_AWARE': False,
                'PREFER_DATES_FROM': 'future'
            }
        )
        if parsed:
            logger.debug(f"✅ Parsé avec dateparser: {parsed}")
            return parsed
    except Exception as e:
        logger.debug(f"dateparser échec: {e}")
    
    # ============================================
    # MÉTHODE 2: dateutil (formats ISO)
    # ============================================
    try:
        parsed = dateutil_parser.parse(date_string, fuzzy=True)
        logger.debug(f"✅ Parsé avec dateutil: {parsed}")
        return parsed
    except Exception as e:
        logger.debug(f"dateutil échec: {e}")
    
    # ============================================
    # MÉTHODE 3: Regex pour format Brightspace français
    # ============================================
    # Format: "20 oct 2025 à 23h59"
    pattern_fr = r'(\d{1,2})\s+(\w+)\s+(\d{4})\s+à\s+(\d{1,2})h(\d{2})'
    match = re.search(pattern_fr, date_string)
    
    if match:
        day, month_str, year, hour, minute = match.groups()
        
        # Mapping mois français
        months_fr = {
            'jan': 1, 'janv': 1, 'janvier': 1,
            'fév': 2, 'févr': 2, 'février': 2,
            'mar': 3, 'mars': 3,
            'avr': 4, 'avril': 4,
            'mai': 5,
            'juin': 6, 'jun': 6,
            'juil': 7, 'juillet': 7,
            'août': 8, 'aou': 8,
            'sep': 9, 'sept': 9, 'septembre': 9,
            'oct': 10, 'octobre': 10,
            'nov': 11, 'novembre': 11,
            'déc': 12, 'décembre': 12
        }
        
        month = months_fr.get(month_str.lower())
        
        if month:
            parsed = datetime(
                int(year), month, int(day),
                int(hour), int(minute)
            )
            logger.debug(f"✅ Parsé avec regex FR: {parsed}")
            return parsed
    
    # Échec
    logger.warning(f"⚠️ Impossible de parser: '{date_string}'")
    return None


def time_until(target_date):
    """
    Calcule le temps restant jusqu'à une date
    
    Args:
        target_date: datetime ou string
    
    Returns:
        dict: {
            'days': int,
            'hours': int,
            'minutes': int,
            'total_hours': float,
            'is_overdue': bool
        }
    """
    # Parser si string
    if isinstance(target_date, str):
        target_date = parse_date(target_date)
    
    if not target_date:
        return None
    
    # Calculer différence
    now = datetime.now()
    delta = target_date - now
    
    # Si passé (négatif)
    if delta.total_seconds() < 0:
        return {
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'total_hours': 0,
            'is_overdue': True
        }
    
    # Décomposer
    return {
        'days': delta.days,
        'hours': delta.seconds // 3600,
        'minutes': (delta.seconds % 3600) // 60,
        'total_hours': delta.total_seconds() / 3600,
        'is_overdue': False
    }


def format_time_remaining(target_date):
    """
    Formate joliment le temps restant
    
    Args:
        target_date: datetime ou string
    
    Returns:
        str: Format lisible (ex: "2 jours 5h" ou "URGENT: 3h")
    """
    time_info = time_until(target_date)
    
    if not time_info:
        return "Date invalide"
    
    if time_info['is_overdue']:
        return "⚠️ EN RETARD"
    
    days = time_info['days']
    hours = time_info['hours']
    minutes = time_info['minutes']
    total_hours = time_info['total_hours']
    
    # Moins de 3 heures = URGENT
    if total_hours < 3:
        return f"🚨 URGENT: {hours}h {minutes}min"
    
    # Moins de 24h
    elif days == 0:
        return f"⏰ {hours}h {minutes}min"
    
    # Demain
    elif days == 1:
        return f"📅 Demain à {hours}h{minutes:02d}"
    
    # Plusieurs jours
    else:
        return f"📅 {days} jours {hours}h"


def is_due_soon(target_date, threshold_hours=48):
    """
    Vérifie si une date d'échéance est proche
    
    Args:
        target_date: datetime ou string
        threshold_hours: Seuil en heures (défaut: 48h)
    
    Returns:
        bool: True si échéance proche
    """
    time_info = time_until(target_date)
    
    if not time_info:
        return False
    
    return (
        time_info['total_hours'] <= threshold_hours 
        and not time_info['is_overdue']
    )


# ============================================
# FONCTION DE TEST
# ============================================
def test_date_parser():
    """Teste le parsing de différents formats"""
    print("📅 Test du parser de dates...\n")
    
    # Dates à tester
    test_dates = [
        "20 oct 2025 à 23h59",
        "Oct 20, 2025 at 11:59 PM",
        "2025-10-20T23:59:00",
        "20/10/2025 23:59",
        "dans 2 jours",
        "demain à 15h"
    ]
    
    print("=" * 60)
    print("TEST 1: Parsing de différents formats")
    print("=" * 60)
    
    for date_str in test_dates:
        parsed = parse_date(date_str)
        if parsed:
            remaining = format_time_remaining(parsed)
            print(f"\n✅ '{date_str}'")
            print(f"   → Parsé: {parsed}")
            print(f"   → Temps restant: {remaining}")
        else:
            print(f"\n❌ Échec: '{date_str}'")
    
    # Test de comparaison
    print("\n" + "=" * 60)
    print("TEST 2: Comparaison de dates")
    print("=" * 60)
    
    date1 = parse_date("20 oct 2025 à 23h59")
    date2 = parse_date("21 oct 2025 à 10h00")
    
    if date1 and date2:
        print(f"\n  Date 1: {date1}")
        print(f"  Date 2: {date2}")
        print(f"  Date 1 < Date 2: {date1 < date2}")
        print(f"  ✅ Comparaison fonctionne!")
    
    # Test is_due_soon
    print("\n" + "=" * 60)
    print("TEST 3: Détection échéances proches")
    print("=" * 60)
    
    # Date dans 1 jour
    tomorrow = datetime.now() + timedelta(days=1)
    print(f"\n  Date test: {tomorrow}")
    print(f"  Est proche (< 48h)? {is_due_soon(tomorrow, threshold_hours=48)}")
    print(f"  ✅ Should be True")
    
    # Date dans 1 semaine
    next_week = datetime.now() + timedelta(days=7)
    print(f"\n  Date test: {next_week}")
    print(f"  Est proche (< 48h)? {is_due_soon(next_week, threshold_hours=48)}")
    print(f"  ✅ Should be False")
    
    print("\n" + "=" * 60)
    print("✅ Tous les tests terminés!")
    print("=" * 60)


if __name__ == "__main__":
    test_date_parser()