"""
Gestion de la base de données SQLite
Stocke les travaux Brightspace et historique des synchronisations
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os

from utils.logger import logger
from config import config


class Database:
    """
    Gestionnaire de la base de données SQLite
    """
    
    def __init__(self, db_path=None):
        """
        Initialise la connexion à la base de données
        
        Args:
            db_path: Chemin du fichier DB (défaut: depuis config)
        """
        self.db_path = db_path or config.DATABASE_FILE
        self._ensure_data_dir()
        self.init_database()
        logger.info(f"✅ Database initialisée: {self.db_path}")
    
    def _ensure_data_dir(self):
        """Crée le dossier data/ si n'existe pas"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
    
    def get_connection(self):
        """
        Retourne une connexion à la base de données
        
        Returns:
            sqlite3.Connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permet accès par nom de colonne
        return conn
    
    def init_database(self):
        """Crée les tables si elles n'existent pas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ============================================
        # TABLE: assignments
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                course TEXT NOT NULL,
                due_date DATETIME NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                grade REAL,
                link TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_notified DATETIME,
                notification_count INTEGER DEFAULT 0
            )
        ''')
        
        # ============================================
        # TABLE: sync_history
        # ============================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                assignments_found INTEGER DEFAULT 0,
                new_assignments INTEGER DEFAULT 0,
                updated_assignments INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')
        
        # ============================================
        # INDEX pour performance
        # ============================================
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_due_date 
            ON assignments(due_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_is_completed 
            ON assignments(is_completed)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_course
            ON assignments(course)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.debug("Tables de base de données créées/vérifiées")
    
    def save_assignment(self, assignment: Dict) -> bool:
        """
        Insère ou met à jour un travail
        
        Args:
            assignment: Dict avec clés: id, title, course, due_date, etc.
        
        Returns:
            bool: True si nouveau, False si mis à jour
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Vérifier si existe déjà
        cursor.execute('SELECT id FROM assignments WHERE id = ?', (assignment['id'],))
        exists = cursor.fetchone() is not None
        
        if exists:
            # UPDATE
            cursor.execute('''
                UPDATE assignments
                SET title = ?, course = ?, due_date = ?, is_completed = ?,
                    grade = ?, link = ?, description = ?, updated_at = ?
                WHERE id = ?
            ''', (
                assignment['title'],
                assignment['course'],
                assignment['due_date'],
                assignment.get('is_completed', False),
                assignment.get('grade'),
                assignment.get('link'),
                assignment.get('description'),
                datetime.now(),
                assignment['id']
            ))
            logger.debug(f"Travail mis à jour: {assignment['title']}")
            conn.commit()
            conn.close()
            return False
        else:
            # INSERT
            cursor.execute('''
                INSERT INTO assignments 
                (id, title, course, due_date, is_completed, grade, link, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assignment['id'],
                assignment['title'],
                assignment['course'],
                assignment['due_date'],
                assignment.get('is_completed', False),
                assignment.get('grade'),
                assignment.get('link'),
                assignment.get('description')
            ))
            logger.info(f"✅ Nouveau travail ajouté: {assignment['title']}")
            conn.commit()
            conn.close()
            return True
    
    def get_all_assignments(self) -> List[Dict]:
        """
        Retourne tous les travaux
        
        Returns:
            List de dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM assignments ORDER BY due_date ASC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_pending_assignments(self) -> List[Dict]:
        """
        Retourne tous les travaux non complétés
        
        Returns:
            List de dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM assignments
            WHERE is_completed = 0
            ORDER BY due_date ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_assignments_due_soon(self, days=3) -> List[Dict]:
        """
        Retourne travaux avec échéance dans X jours
        
        Args:
            days: Nombre de jours
        
        Returns:
            List de dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM assignments
            WHERE is_completed = 0
            AND due_date BETWEEN datetime('now') 
                AND datetime('now', '+' || ? || ' days')
            ORDER BY due_date ASC
        ''', (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_assignment_by_id(self, assignment_id: str) -> Optional[Dict]:
        """
        Retourne un travail par son ID
        
        Args:
            assignment_id: ID du travail
        
        Returns:
            Dict ou None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM assignments WHERE id = ?', (assignment_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def mark_as_notified(self, assignment_id: str):
        """
        Marque un travail comme notifié
        
        Args:
            assignment_id: ID du travail
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE assignments
            SET last_notified = ?, 
                notification_count = notification_count + 1
            WHERE id = ?
        ''', (datetime.now(), assignment_id))
        
        conn.commit()
        conn.close()
        logger.debug(f"Travail marqué comme notifié: {assignment_id}")
    
    def delete_assignment(self, assignment_id: str):
        """
        Supprime un travail
        
        Args:
            assignment_id: ID du travail
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
        conn.commit()
        conn.close()
        logger.info(f"Travail supprimé: {assignment_id}")
    
    def log_sync(self, status: str, assignments_found: int = 0, 
                 new: int = 0, updated: int = 0, error: str = None):
        """
        Enregistre une synchronisation dans l'historique
        
        Args:
            status: 'success' ou 'error'
            assignments_found: Nombre total trouvés
            new: Nombre de nouveaux
            updated: Nombre mis à jour
            error: Message d'erreur si échec
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_history 
            (status, assignments_found, new_assignments, updated_assignments, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (status, assignments_found, new, updated, error))
        
        conn.commit()
        conn.close()
        
        if status == 'success':
            logger.info(f"✅ Sync réussie: {assignments_found} travaux ({new} nouveaux, {updated} MàJ)")
        else:
            logger.error(f"❌ Sync échouée: {error}")
    
    def get_sync_history(self, limit=10) -> List[Dict]:
        """
        Retourne l'historique des synchronisations
        
        Args:
            limit: Nombre max de résultats
        
        Returns:
            List de dicts
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sync_history
            ORDER BY sync_time DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_statistics(self) -> Dict:
        """
        Retourne des statistiques sur les travaux
        
        Returns:
            Dict avec stats
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total travaux
        cursor.execute('SELECT COUNT(*) as total FROM assignments')
        total = cursor.fetchone()['total']
        
        # Travaux complétés
        cursor.execute('SELECT COUNT(*) as completed FROM assignments WHERE is_completed = 1')
        completed = cursor.fetchone()['completed']
        
        # Travaux en attente
        pending = total - completed
        
        # Travaux urgents (< 48h)
        cursor.execute('''
            SELECT COUNT(*) as urgent FROM assignments
            WHERE is_completed = 0
            AND due_date BETWEEN datetime('now') 
                AND datetime('now', '+2 days')
        ''')
        urgent = cursor.fetchone()['urgent']
        
        # Travaux en retard
        cursor.execute('''
            SELECT COUNT(*) as overdue FROM assignments
            WHERE is_completed = 0
            AND due_date < datetime('now')
        ''')
        overdue = cursor.fetchone()['overdue']
        
        conn.close()
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'urgent': urgent,
            'overdue': overdue,
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }


# ============================================
# INSTANCE GLOBALE
# ============================================
db = Database()


# ============================================
# FONCTION DE TEST
# ============================================
def test_database():
    """Teste toutes les opérations de la base de données"""
    print("🗄️ Test de la base de données...\n")
    
    # Test 1: Créer des travaux de test
    print("=" * 60)
    print("TEST 1: Insertion de travaux")
    print("=" * 60)
    
    travaux_test = [
        {
            'id': 'test-001',
            'title': 'Devoir de Mathématiques',
            'course': 'Calcul 2 (MAT201)',
            'due_date': '2025-10-25 23:59:00',
            'is_completed': False,
            'link': 'https://brightspace.collegeboreal.ca/assignment/1'
        },
        {
            'id': 'test-002',
            'title': 'TP Python - Classes',
            'course': 'Programmation (INF105)',
            'due_date': '2025-10-28 23:59:00',
            'is_completed': False,
            'link': 'https://brightspace.collegeboreal.ca/assignment/2'
        },
        {
            'id': 'test-003',
            'title': 'Essai Philosophie',
            'course': 'Philo 101',
            'due_date': '2025-11-05 23:59:00',
            'is_completed': True,
            'grade': 85.5
        }
    ]
    
    for travail in travaux_test:
        is_new = db.save_assignment(travail)
        print(f"  {'✅ Nouveau' if is_new else '📝 Mis à jour'}: {travail['title']}")
    
    # Test 2: Lire tous les travaux
    print("\n" + "=" * 60)
    print("TEST 2: Lecture de tous les travaux")
    print("=" * 60)
    
    all_assignments = db.get_all_assignments()
    print(f"  Total: {len(all_assignments)} travaux\n")
    
    for assignment in all_assignments:
        status = "✅ Complété" if assignment['is_completed'] else "❌ En attente"
        print(f"  {status} - {assignment['title']}")
        print(f"           Cours: {assignment['course']}")
        print(f"           Échéance: {assignment['due_date']}")
        if assignment['grade']:
            print(f"           Note: {assignment['grade']}/100")
        print()
    
    # Test 3: Travaux en attente
    print("=" * 60)
    print("TEST 3: Travaux en attente")
    print("=" * 60)
    
    pending = db.get_pending_assignments()
    print(f"  {len(pending)} travaux en attente:\n")
    
    for assignment in pending:
        print(f"  📋 {assignment['title']}")
        print(f"     {assignment['course']} - {assignment['due_date']}\n")
    
    # Test 4: Travaux urgents
    print("=" * 60)
    print("TEST 4: Travaux urgents (< 7 jours)")
    print("=" * 60)
    
    due_soon = db.get_assignments_due_soon(days=7)
    print(f"  {len(due_soon)} travaux urgents\n")
    
    # Test 5: Statistiques
    print("=" * 60)
    print("TEST 5: Statistiques")
    print("=" * 60)
    
    stats = db.get_statistics()
    print(f"\n  📊 Statistiques globales:")
    print(f"     Total de travaux: {stats['total']}")
    print(f"     Complétés: {stats['completed']}")
    print(f"     En attente: {stats['pending']}")
    print(f"     Urgents (< 48h): {stats['urgent']}")
    print(f"     En retard: {stats['overdue']}")
    print(f"     Taux de complétion: {stats['completion_rate']:.1f}%")
    
    # Test 6: Historique de sync
    print("\n" + "=" * 60)
    print("TEST 6: Enregistrement d'une synchronisation")
    print("=" * 60)
    
    db.log_sync(
        status='success',
        assignments_found=3,
        new=3,
        updated=0
    )
    print("  ✅ Synchronisation enregistrée")
    
    history = db.get_sync_history(limit=5)
    print(f"\n  📜 Historique (dernières {len(history)} syncs):\n")
    
    for sync in history:
        print(f"  {sync['sync_time']} - {sync['status'].upper()}")
        print(f"     Trouvés: {sync['assignments_found']} | Nouveaux: {sync['new_assignments']} | MàJ: {sync['updated_assignments']}")
        if sync['error_message']:
            print(f"     Erreur: {sync['error_message']}")
        print()
    
    print("=" * 60)
    print("✅ Tous les tests de la base de données réussis!")
    print("=" * 60)


if __name__ == "__main__":
    test_database()