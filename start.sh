#!/bin/bash

# Script de démarrage pour Railway
# Exécute le programme en boucle avec cron simulé

echo "🚀 Brightspace Agent - Démarrage sur Railway"
echo "============================================"

# Fonction pour exécuter le scraping
run_scraping() {
    echo ""
    echo "🕐 Exécution démarrée: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    python main.py
    echo "✅ Exécution terminée: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""
}

# Fonction pour calculer le temps d'attente jusqu'à la prochaine exécution
wait_until_next_run() {
    current_hour=$(date +%H)
    current_minute=$(date +%M)

    # Convertir en minutes depuis minuit
    current_minutes=$((10#$current_hour * 60 + 10#$current_minute))

    # Heures d'exécution : 8h00 (480 min) et 22h00 (1320 min)
    morning_time=125   # 8h00
    evening_time=135  # 22h00

    # Calculer le temps d'attente
    if [ $current_minutes -lt $morning_time ]; then
        # Attendre jusqu'à 8h00
        wait_minutes=$((morning_time - current_minutes))
    elif [ $current_minutes -lt $evening_time ]; then
        # Attendre jusqu'à 22h00
        wait_minutes=$((evening_time - current_minutes))
    else
        # Attendre jusqu'à 8h00 demain (1440 min/jour)
        wait_minutes=$((1440 - current_minutes + morning_time))
    fi

    wait_seconds=$((wait_minutes * 60))

    echo "⏰ Prochaine exécution dans $wait_minutes minutes"
    echo "💤 Attente jusqu'à $(date -d "+$wait_minutes minutes" '+%H:%M')..."

    sleep $wait_seconds
}

# Boucle infinie
while true; do
    current_hour=$(date +%H)
    current_minute=$(date +%M)

    # Vérifier si on est à l'heure d'exécution (±2 minutes de tolérance)
    if ([ "$current_hour" -eq 8 ] && [ "$current_minute" -lt 5 ]) || \
       ([ "$current_hour" -eq 22 ] && [ "$current_minute" -lt 5 ]); then
        run_scraping
        # Attendre 10 minutes pour éviter double exécution
        echo "⏸️  Pause de 10 minutes..."
        sleep 600
    fi

    # Attendre jusqu'à la prochaine exécution
    wait_until_next_run
done
