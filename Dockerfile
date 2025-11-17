# Utiliser Python 3.11 comme base
FROM python:3.11-slim

# Installer les dépendances système pour Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer Playwright et ses navigateurs
RUN playwright install chromium
RUN playwright install-deps chromium

# Copier tout le projet
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p data/account1 data/account2 logs

# Définir les permissions
RUN chmod +x run_agent.sh || true

# Commande par défaut
CMD ["bash", "start.sh"]
