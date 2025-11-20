#!/bin/bash

# Script de TEST - Exécution immédiate
# À REMPLACER par la version normale après le test

echo "🚀 Brightspace Agent - TEST IMMÉDIAT"
echo "============================================"
echo ""
echo "🕐 Exécution démarrée: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

python main.py

echo "✅ Exécution terminée: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# Garder le container actif pour voir les logs
echo "⏸️ Test terminé. Container en attente..."
sleep infinity
