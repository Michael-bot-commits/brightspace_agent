"""
Module de notifications par email avec yagmail
Envoie des alertes pour nouveaux travaux, échéances proches, résumés quotidiens
"""
import yagmail
from datetime import datetime, timedelta
from typing import List, Dict
import re

from utils.logger import logger
from config.accounts import EMAIL_CONFIG


class EmailNotifier:
    """Gère l'envoi de notifications par email avec yagmail"""
    
    def __init__(self):
        self.config = EMAIL_CONFIG
        self.enabled = self.config.get('enabled', True)
        
        # Initialiser yagmail
        if self.enabled:
            try:
                self.yag = yagmail.SMTP(
                    user=self.config['sender_email'],
                    password=self.config['sender_password']
                )
                logger.debug("✅ Yagmail initialisé")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation yagmail: {e}")
                self.enabled = False
    
    def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """
        Envoie un email HTML avec yagmail
        
        Args:
            to_email: Email du destinataire
            subject: Sujet de l'email
            html_body: Corps HTML de l'email
        
        Returns:
            bool: True si envoyé, False sinon
        """
        if not self.enabled:
            return False
        
        try:
            # NETTOYER les caractères problématiques
            subject_clean = subject.replace('\xa0', ' ').replace('\u202f', ' ').replace('\u00a0', ' ')
            html_body_clean = html_body.replace('\xa0', ' ').replace('\u202f', ' ').replace('\u00a0', ' ')
            
            # Envoyer avec yagmail
            self.yag.send(
                to=to_email,
                subject=subject_clean,
                contents=html_body_clean
            )
            
            # Log sans détails pour éviter erreurs encodage
            print(f"✅ Email envoye a {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur email: {type(e).__name__}")
            return False
    
    # ============================================
    # NOUVELLE MÉTHODE : FUSION INTELLIGENTE
    # ============================================
    
    def send_smart_notification(self, account_name: str, to_email: str,
                                new_assignments: List[Dict], 
                                urgent_assignments: List[Dict],
                                all_assignments: List[Dict], 
                                time_of_day: str = None) -> bool:
        """
        Envoie une notification intelligente fusionnée selon les conditions
        
        Args:
            account_name: Nom du compte
            to_email: Email destinataire
            new_assignments: Liste nouveaux travaux
            urgent_assignments: Liste travaux urgents
            all_assignments: Liste tous travaux en attente
            time_of_day: 'morning', 'evening' ou None
        
        Returns:
            bool: True si envoyé, False sinon
        """
        has_new = len(new_assignments) > 0
        has_urgent = len(urgent_assignments) > 0
        is_summary_time = time_of_day in ['morning', 'evening']
        
        # CAS 1 : Nouveaux + Urgents
        if has_new and has_urgent:
            subject = f"🎓⚠️ [{account_name}] {len(new_assignments)} {'nouveaux travaux' if len(new_assignments) > 1 else 'nouveau travail'} (dont {len(urgent_assignments)} urgent{'s' if len(urgent_assignments) > 1 else ''})"
            html = self._generate_combined_email(
                account_name, new_assignments, urgent_assignments, 
                all_assignments, time_of_day
            )
        
        # CAS 2 : Nouveaux seulement
        elif has_new:
            subject = f"🎓 [{account_name}] {len(new_assignments)} {'nouveaux travaux' if len(new_assignments) > 1 else 'nouveau travail'}"
            html = self._generate_new_only_email(
                account_name, new_assignments, all_assignments, time_of_day
            )
        
        # CAS 3 : Urgents seulement
        elif has_urgent:
            subject = f"⚠️ [{account_name}] {len(urgent_assignments)} {'travaux urgents' if len(urgent_assignments) > 1 else 'travail urgent'}"
            html = self._generate_urgent_only_email(
                account_name, urgent_assignments, all_assignments, time_of_day
            )
        
        # CAS 4 : Résumé seulement (si heure correspond)
        elif is_summary_time:
            emoji = "☀️" if time_of_day == 'morning' else "🌙"
            period = "matin" if time_of_day == 'morning' else "soir"
            subject = f"{emoji} [{account_name}] Résumé du {period} - {len(all_assignments)} {'travaux' if len(all_assignments) != 1 else 'travail'} à faire"
            html = self._generate_summary_only_email(
                account_name, all_assignments, time_of_day
            )
        
        # CAS 5 : Rien à envoyer
        else:
            return False
        
        return self.send_email(to_email, subject, html)
    
    def _generate_combined_email(self, account_name: str, 
                                 new_assignments: List[Dict],
                                 urgent_assignments: List[Dict],
                                 all_assignments: List[Dict],
                                 time_of_day: str = None) -> str:
        """Génère email fusionné Nouveaux + Urgents"""
        
        # Section nouveaux
        new_html = ""
        for assignment in new_assignments:
            due_date_str = "Non définie"
            if assignment['due_date']:
                due_date = datetime.fromisoformat(assignment['due_date'])
                due_date_str = due_date.strftime("%d %B %Y à %H:%M")
            
            # Marquer si urgent
            is_urgent = assignment in urgent_assignments
            urgent_badge = " [URGENT]" if is_urgent else ""
            border_color = "#f44336" if is_urgent else "#4CAF50"
            title_color = "#f44336" if is_urgent else "#333" 
            
            new_html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid {border_color}; 
                        margin: 10px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color:{title_color};">
                    {assignment['title']}{urgent_badge}
                </h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date_str}
                </p>
            </div>
            """
        
        # Section urgents (détails supplémentaires)
        urgent_html = ""
        for assignment in urgent_assignments:
            due_date = datetime.fromisoformat(assignment['due_date'])
            time_left = due_date - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            
            urgent_html += f"""
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #f44336; 
                        margin: 10px 0; border-radius: 5px; border: 2px solid #ffc107;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #f44336; font-weight: bold; font-size: 18px;">
                    ⏰ Temps restant: {hours_left} {'heures' if hours_left > 1 else 'heure'} !
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date.strftime("%d %B %Y à %H:%M")}
                </p>
            </div>
            """
        
        # Résumé en bas
        summary_html = ""
        
        # Email complet
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.4; }}
            </style>
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">🎓 Brightspace Agent</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    Bonjour {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    🆕 NOUVEAUX TRAVAUX DÉTECTÉS ({len(new_assignments)})
                </h2>
                
                {new_html}
                
                <h2 style="color: #f44336; margin-top: 30px;">
                    ⚠️ DÉTAILS DES TRAVAUX URGENTS
                </h2>
                
                {urgent_html}
            </div>
            
            {summary_html}
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    📊 Synchronisation effectuée le {datetime.now().strftime("%d/%m/%Y à %H:%M")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_new_only_email(self, account_name: str,
                                 new_assignments: List[Dict],
                                 all_assignments: List[Dict],
                                 time_of_day: str = None) -> str:
        """Génère email Nouveaux seulement"""
        
        # Section nouveaux
        new_html = ""
        for assignment in new_assignments:
            due_date_str = "Non définie"
            if assignment['due_date']:
                due_date = datetime.fromisoformat(assignment['due_date'])
                due_date_str = due_date.strftime("%d %B %Y à %H:%M")
            
            new_html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid #4CAF50; 
                        margin: 10px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date_str}
                </p>
            </div>
            """
        
        # Résumé en bas
        summary_html = ""
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.4; }}
            </style>
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">🎓 Brightspace Agent</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    Bonjour {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    🆕 NOUVEAUX TRAVAUX DÉTECTÉS ({len(new_assignments)})
                </h2>
                
                {new_html}
            </div>
            
            {summary_html}
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    📊 Synchronisation effectuée le {datetime.now().strftime("%d/%m/%Y à %H:%M")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_urgent_only_email(self, account_name: str,
                                    urgent_assignments: List[Dict],
                                    all_assignments: List[Dict],
                                    time_of_day: str = None) -> str:
        """Génère email Urgents seulement"""
        
        # Section urgents
        urgent_html = ""
        for assignment in urgent_assignments:
            due_date = datetime.fromisoformat(assignment['due_date'])
            time_left = due_date - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            
            urgent_html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid #f44336; 
                        margin: 10px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #f44336;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #f44336; font-weight: bold; font-size: 18px;">
                    ⏰ Temps restant: {hours_left} {'heures' if hours_left > 1 else 'heure'} !
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date.strftime("%d %B %Y à %H:%M")}
                </p>
            </div>
            """
        
        # Résumé en bas
        summary_html = ""
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">⚠️ ALERTE URGENTE</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    {account_name}, tu as des travaux urgents !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    🚨 {len(urgent_assignments)} {'travaux' if len(urgent_assignments) > 1 else 'travail'} à rendre bientôt
                </h2>
                
                {urgent_html}
                
                <div style="text-align: center; padding: 20px; background: #fff3cd; 
                            border-radius: 5px; margin-top: 20px; border: 2px solid #ffc107;">
                    <p style="margin: 0; color: #856404; font-weight: bold;">
                        ⏰ N'oublie pas de soumettre tes travaux à temps !
                    </p>
                </div>
            </div>
            
            {summary_html}
        </body>
        </html>
        """
        
        return html
    
    def _generate_summary_only_email(self, account_name: str,
                                     all_assignments: List[Dict],
                                     time_of_day: str) -> str:
        """Génère email Résumé seulement"""
        
        emoji = "☀️" if time_of_day == 'morning' else "🌙"
        greeting = "Bonjour" if time_of_day == 'morning' else "Bonsoir"
        period = "matin" if time_of_day == 'morning' else "soir"
        count = len(all_assignments)
        
        if count == 0:
            content_html = """
            <div style="text-align: center; padding: 40px; background: #e8f5e9; border-radius: 10px;">
                <h2 style="color: #2e7d32; margin: 0;">🎉 Aucun travail en attente !</h2>
                <p style="color: #666; margin: 10px 0 0 0;">
                    {} !
                </p>
            </div>
            """.format("Profite de ta journée" if time_of_day == 'morning' else "Repose-toi bien 😴")
        else:
            # Trier par urgence
            sorted_assignments = sorted(
                [a for a in all_assignments if a['due_date']],
                key=lambda x: x['due_date']
            )
            
            assignments_html = self._generate_assignments_html(sorted_assignments)
            
            content_html = f"""
            <p style="color: #666; font-size: 16px;">
                Aucun nouveau travail depuis hier.<br>
                Aucun travail urgent pour le moment.
            </p>
            
            <h2 style="color: #333; margin-top: 30px;">
                Tu as {count} {'travaux' if count != 1 else 'travail'} à faire
            </h2>
            
            {assignments_html}
            """
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">{emoji} Résumé du {period}</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    {greeting} {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                {content_html}
            </div>
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    📅 {datetime.now().strftime("%A %d %B %Y")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_summary_stats(self, all_assignments: List[Dict]) -> str:
        """Génère le bloc de statistiques résumé pour tous les emails"""
        
        total_count = len(all_assignments)
        
        # Compter par catégorie d'urgence
        now = datetime.now()
        urgent_count = 0
        soon_count = 0
        later_count = 0
        
        for assignment in all_assignments:
            if assignment['due_date']:
                due_date = datetime.fromisoformat(assignment['due_date'])
                time_left = due_date - now
                hours_left = int(time_left.total_seconds() / 3600)
                days_left = time_left.days
                
                if hours_left < 24:
                    urgent_count += 1
                elif days_left < 3:
                    soon_count += 1
                else:
                    later_count += 1
            else:
                later_count += 1
        
        html = f"""
        <div style="background: #f5f5f5; padding: 20px; margin-top: 30px; border-radius: 5px;">
            <h3 style="color: #333; margin: 0 0 15px 0;">
                📊 Résumé complet de ta situation
            </h3>
            
            <p style="margin: 5px 0; color: #666; font-size: 16px;">
                Tu as <strong>{total_count} {'travaux' if total_count != 1 else 'travail'}</strong> à faire :
            </p>
            
            <ul style="list-style: none; padding: 0; margin: 10px 0;">
                <li style="color: #f44336; margin: 5px 0; font-size: 15px;">
                    🔴 Urgents (moins de 24h) : <strong>{urgent_count}</strong>
                </li>
                <li style="color: #FF9800; margin: 5px 0; font-size: 15px;">
                    🟡 Bientôt (moins de 3 jours) : <strong>{soon_count}</strong>
                </li>
                <li style="color: #4CAF50; margin: 5px 0; font-size: 15px;">
                    🟢 Plus tard : <strong>{later_count}</strong>
                </li>
            </ul>
        </div>
        """
        
        return html
    def notify_new_assignments(self, account_name: str, to_email: str, 
                               new_assignments: List[Dict]) -> bool:
        """Notifie de nouveaux travaux"""
        
        if not new_assignments:
            return False
        
        count = len(new_assignments)
        subject = f"🎓 [{account_name}] {count} {'nouveaux travaux' if count > 1 else 'nouveau travail'}"
        
        # Générer HTML
        assignments_html = ""
        for assignment in new_assignments:
            due_date_str = "Non définie"
            if assignment['due_date']:
                due_date = datetime.fromisoformat(assignment['due_date'])
                due_date_str = due_date.strftime("%d %B %Y à %H:%M")
            
            assignments_html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid #4CAF50; 
                        margin: 10px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date_str}
                </p>
            </div>
            """
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            </style>
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">🎓 Brightspace Agent</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    Bonjour {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    📝 {count} {'nouveaux travaux détectés' if count > 1 else 'nouveau travail détecté'}
                </h2>
                
                {assignments_html}
            </div>
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    📊 Synchronisation effectuée le {datetime.now().strftime("%d/%m/%Y à %H:%M")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html)
    
    def notify_urgent_assignments(self, account_name: str, to_email: str,
                                  urgent_assignments: List[Dict]) -> bool:
        """Notifie des travaux urgents (< 24h)"""
        
        if not urgent_assignments:
            return False
        
        count = len(urgent_assignments)
        subject = f"⚠️ [{account_name}] {count} {'travaux urgents' if count > 1 else 'travail urgent'}"
        
        assignments_html = ""
        for assignment in urgent_assignments:
            due_date = datetime.fromisoformat(assignment['due_date'])
            time_left = due_date - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            
            color = "#f44336"
            
            assignments_html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid {color}; 
                        margin: 10px 0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #f44336;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📚 Cours:</strong> {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: {color}; font-weight: bold; font-size: 18px;">
                    ⏰ Temps restant: {hours_left} {'heures' if hours_left > 1 else 'heure'} !
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📅 Échéance:</strong> {due_date.strftime("%d %B %Y à %H:%M")}
                </p>
            </div>
            """
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">⚠️ ALERTE URGENTE</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    {account_name}, tu as des travaux urgents !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    🚨 {count} {'travaux' if count > 1 else 'travail'} à rendre bientôt
                </h2>
                
                {assignments_html}
            </div>
            
            <div style="text-align: center; padding: 20px; background: #fff3cd; 
                        border-radius: 5px; margin-top: 20px; border: 2px solid #ffc107;">
                <p style="margin: 0; color: #856404; font-weight: bold;">
                    ⏰ N'oublie pas de soumettre tes travaux à temps !
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html)
    
    def send_morning_summary(self, account_name: str, to_email: str,
                            pending_assignments: List[Dict]) -> bool:
        """Envoie un résumé du matin"""
        
        count = len(pending_assignments)
        subject = f"☀️ [{account_name}] Résumé du matin - {count} {'travaux' if count != 1 else 'travail'} à faire"
        
        if count == 0:
            assignments_html = """
            <div style="text-align: center; padding: 40px; background: #e8f5e9; border-radius: 10px;">
                <h2 style="color: #2e7d32; margin: 0;">🎉 Aucun travail en attente !</h2>
                <p style="color: #666; margin: 10px 0 0 0;">Profite de ta journée !</p>
            </div>
            """
        else:
            sorted_assignments = sorted(
                [a for a in pending_assignments if a['due_date']],
                key=lambda x: x['due_date']
            )
            
            assignments_html = self._generate_assignments_html(sorted_assignments)
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">☀️ Résumé du matin</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    Bonjour {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    Tu as {count} {'travaux' if count != 1 else 'travail'} à faire
                </h2>
                
                {assignments_html}
            </div>
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    📅 {datetime.now().strftime("%A %d %B %Y")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html)
    
    def send_evening_summary(self, account_name: str, to_email: str,
                            pending_assignments: List[Dict]) -> bool:
        """Envoie un résumé du soir"""
        
        count = len(pending_assignments)
        subject = f"🌙 [{account_name}] Résumé du soir - {count} {'travaux' if count != 1 else 'travail'} à faire"
        
        if count == 0:
            assignments_html = """
            <div style="text-align: center; padding: 40px; background: #e8f5e9; border-radius: 10px;">
                <h2 style="color: #2e7d32; margin: 0;">🎉 Aucun travail en attente !</h2>
                <p style="color: #666; margin: 10px 0 0 0;">Repose-toi bien ! 😴</p>
            </div>
            """
        else:
            sorted_assignments = sorted(
                [a for a in pending_assignments if a['due_date']],
                key=lambda x: x['due_date']
            )
            
            assignments_html = self._generate_assignments_html(sorted_assignments)
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="margin: 0;">🌙 Résumé du soir</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">
                    Bonsoir {account_name} !
                </p>
            </div>
            
            <div style="padding: 20px 0;">
                <h2 style="color: #333;">
                    Voici où tu en es avant de dormir :
                </h2>
                
                <p style="color: #666; font-size: 18px; font-weight: bold;">
                    Tu as {count} {'travaux' if count != 1 else 'travail'} à faire
                </p>
                
                {assignments_html}
            </div>
            
            <div style="text-align: center; padding: 20px; background: #f0f4ff; 
                        border-radius: 5px; margin-top: 20px; border-left: 4px solid #667eea;">
                <p style="margin: 0; color: #667eea; font-weight: bold;">
                    💡 Astuce: Planifie ta journée de demain en fonction des échéances
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; background: #f5f5f5; 
                        border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #666;">
                    {datetime.now().strftime("%A %d %B %Y - %H:%M")}
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html)
    
    def _generate_assignments_html(self, sorted_assignments: List[Dict]) -> str:
        """Génère le HTML pour la liste des travaux"""
        html = ""
        
        for assignment in sorted_assignments:
            due_date = datetime.fromisoformat(assignment['due_date'])
            time_left = due_date - datetime.now()
            days_left = time_left.days
            hours_left = int(time_left.total_seconds() / 3600)
            
            if hours_left < 24:
                emoji = "🔴"
                color = "#f44336"
                urgency = "URGENT"
            elif days_left < 3:
                emoji = "🟡"
                color = "#FF9800"
                urgency = "Bientôt"
            elif days_left < 7:
                emoji = "🟢"
                color = "#4CAF50"
                urgency = "Cette semaine"
            else:
                emoji = "🟢"
                color = "#4CAF50"
                urgency = "Plus tard"
            
            html += f"""
            <div style="background: white; padding: 15px; border-left: 4px solid {color}; 
                        margin: 10px 0; border-radius: 5px;">
                <p style="margin: 0 0 5px 0; color: {color}; font-weight: bold;">
                    {emoji} {urgency}
                </p>
                <h3 style="margin: 0 0 10px 0; color: #333;">{assignment['title']}</h3>
                <p style="margin: 5px 0; color: #666; font-size: 14px;">
                    {assignment['course'][:50]}...
                </p>
                <p style="margin: 5px 0; color: #666;">
                    📅 {due_date.strftime("%d %B %Y à %H:%M")} 
                    ({days_left} {'jours' if days_left != 1 else 'jour'})
                </p>
            </div>
            """
        
        return html


# Instance globale
notifier = EmailNotifier()