"""
Gestionnaire de base de données SQLite pour les travaux Brightspace
Stocke les travaux, leur statut, et l'historique des synchronisations
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

from utils.logger import logger


class Database:
    """Gère la base de données SQLite pour stocker les travaux"""
    
    def __init__(self, db_file: str = 'data/assignments.db'):
        """
        Initialise la connexion à la base de données
        
        Args:
            db_file: Chemin vers le fichier de base de données
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self._create_tables()
        logger.debug(f"Database initialisée: {db_file}")
    
    def _create_tables(self):
        """Crée les tables si elles n'existent pas"""
        
        # Table des travaux
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                course TEXT NOT NULL,
                due_date TEXT,
                link TEXT,
                is_completed INTEGER DEFAULT 0,
                grade INTEGER,
                description TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table de l'historique des synchronisations
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                assignments_found INTEGER,
                new_assignments INTEGER,
                updated_assignments INTEGER,
                error_message TEXT
            )
        ''')
        
        self.conn.commit()
    
    def save_assignment(self, assignment: Dict) -> bool:
        """
        Sauvegarde ou met à jour un travail
        
        Args:
            assignment: Dictionnaire contenant les infos du travail
        
        Returns:
            bool: True si nouveau, False si mis à jour
        """
        try:
            # Vérifier si existe déjà
            existing = self.get_assignment(assignment['id'])
            
            if existing:
                # Mise à jour
                self.cursor.execute('''
                    UPDATE assignments 
                    SET title=?, course=?, due_date=?, link=?, 
                        is_completed=?, grade=?, description=?, status=?,
                        updated_at=?
                    WHERE id=?
                ''', (
                    assignment['title'],
                    assignment['course'],
                    assignment['due_date'],
                    assignment['link'],
                    int(assignment['is_completed']),
                    assignment['grade'],
                    assignment['description'],
                    assignment['status'],
                    datetime.now().isoformat(),
                    assignment['id']
                ))
                self.conn.commit()
                return False
            else:
                # Insertion
                self.cursor.execute('''
                    INSERT INTO assignments 
                    (id, title, course, due_date, link, is_completed, grade, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assignment['id'],
                    assignment['title'],
                    assignment['course'],
                    assignment['due_date'],
                    assignment['link'],
                    int(assignment['is_completed']),
                    assignment['grade'],
                    assignment['description'],
                    assignment['status']
                ))
                self.conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur sauvegarde travail: {e}")
            return False
    
    def get_assignment(self, assignment_id: str) -> Optional[Dict]:
        """
        Récupère un travail par son ID
        
        Args:
            assignment_id: ID du travail
        
        Returns:
            Dict ou None
        """
        try:
            self.cursor.execute('''
                SELECT * FROM assignments WHERE id = ?
            ''', (assignment_id,))
            
            row = self.cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'course': row[2],
                    'due_date': row[3],
                    'link': row[4],
                    'is_completed': bool(row[5]),
                    'grade': row[6],
                    'description': row[7],
                    'status': row[8]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération travail {assignment_id}: {e}")
            return None
    
    def get_pending_assignments(self) -> List[Dict]:
        """
        Récupère tous les travaux non complétés
        
        Returns:
            List[Dict]: Liste des travaux à faire
        """
        try:
            self.cursor.execute('''
                SELECT * FROM assignments 
                WHERE is_completed = 0
                ORDER BY due_date ASC
            ''')
            
            rows = self.cursor.fetchall()
            assignments = []
            
            for row in rows:
                assignments.append({
                    'id': row[0],
                    'title': row[1],
                    'course': row[2],
                    'due_date': row[3],
                    'link': row[4],
                    'is_completed': bool(row[5]),
                    'grade': row[6],
                    'description': row[7],
                    'status': row[8]
                })
            
            return assignments
            
        except Exception as e:
            logger.error(f"Erreur récupération travaux pending: {e}")
            return []
    
    def get_all_assignments(self) -> List[Dict]:
        """
        Récupère TOUS les travaux (completed et pending)
        
        Returns:
            List[Dict]: Liste de tous les travaux
        """
        try:
            self.cursor.execute('''
                SELECT * FROM assignments
                ORDER BY due_date ASC
            ''')
            
            rows = self.cursor.fetchall()
            assignments = []
            
            for row in rows:
                assignments.append({
                    'id': row[0],
                    'title': row[1],
                    'course': row[2],
                    'due_date': row[3],
                    'link': row[4],
                    'is_completed': bool(row[5]),
                    'grade': row[6],
                    'description': row[7],
                    'status': row[8]
                })
            
            return assignments
            
        except Exception as e:
            logger.error(f"Erreur récupération tous travaux: {e}")
            return []
    
    def delete_assignment(self, assignment_id: str) -> bool:
        """
        Supprime un travail de la base de données
        
        Args:
            assignment_id: ID du travail à supprimer
        
        Returns:
            bool: True si supprimé, False sinon
        """
        try:
            self.cursor.execute('''
                DELETE FROM assignments WHERE id = ?
            ''', (assignment_id,))
            self.conn.commit()
            
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Erreur suppression travail {assignment_id}: {e}")
            return False
    
    def log_sync(self, status: str, assignments_found: int, new: int, updated: int, error: str = None):
        """
        Enregistre une synchronisation dans l'historique
        
        Args:
            status: 'success' ou 'error'
            assignments_found: Nombre de travaux trouvés
            new: Nombre de nouveaux travaux
            updated: Nombre de travaux mis à jour
            error: Message d'erreur (optionnel)
        """
        try:
            self.cursor.execute('''
                INSERT INTO sync_history 
                (status, assignments_found, new_assignments, updated_assignments, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (status, assignments_found, new, updated, error))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Erreur log sync: {e}")
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """
        Récupère l'historique des synchronisations
        
        Args:
            limit: Nombre maximum de résultats
        
        Returns:
            List[Dict]: Historique des syncs
        """
        try:
            self.cursor.execute('''
                SELECT * FROM sync_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = self.cursor.fetchall()
            history = []
            
            for row in rows:
                history.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'assignments_found': row[3],
                    'new_assignments': row[4],
                    'updated_assignments': row[5],
                    'error_message': row[6]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return []
    
    def close(self):
        """Ferme la connexion à la base de données"""
        self.conn.close()