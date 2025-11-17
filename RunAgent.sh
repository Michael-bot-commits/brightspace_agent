#!/bin/bash

# ============================================
# Script d'exécution pour Brightspace Agent
# Ce script est appelé par le crontab à 8h et 22h
# ============================================

# Chemin vers le dossier du projet
PROJECT_DIR="$HOME/Documents/D2L_AI_AGENT/brightspace-agent"

# Chemin vers l'environnement virtuel
VENV_PATH="$PROJECT_DIR/venv"

# Fichier de log
LOG_FILE="$PROJECT_DIR/logs/cron_execution.log"

# ============================================
# EXÉCUTION
# ============================================

# Se déplacer dans le dossier du projet
cd "$PROJECT_DIR" || exit 1

# Créer le dossier logs s'il n'existe pas
mkdir -p logs

# Ajouter timestamp dans le log
echo "========================================" >> "$LOG_FILE"
echo "🕐 Exécution démarrée: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# ACTIVER l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..." >> "$LOG_FILE"
source "$VENV_PATH/bin/activate" >> "$LOG_FILE" 2>&1

# Vérifier que l'activation a réussi
if [ $? -ne 0 ]; then
    echo "❌ Erreur: Impossible d'activer l'environnement virtuel" >> "$LOG_FILE"
    exit 1
fi

# Exécuter le programme avec Python du venv
echo "🚀 Lancement du programme..." >> "$LOG_FILE"
python main.py >> "$LOG_FILE" 2>&1

# Code de sortie
EXIT_CODE=$?

# Désactiver le venv
deactivate

# Log du résultat
echo "" >> "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Exécution terminée avec succès" >> "$LOG_FILE"
else
    echo "❌ Exécution échouée (code: $EXIT_CODE)" >> "$LOG_FILE"
fi
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE

