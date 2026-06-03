# Utiliser une image Python officielle légère
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier des dépendances (depuis le dossier server)
COPY server/requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source du serveur
COPY server/ ./server/

# Définir la variable d'environnement pour que Python trouve le module "server"
ENV PYTHONPATH=/app

# Exposer le port du serveur FastAPI
EXPOSE 8000

# Commande pour démarrer le bot et l'API
CMD ["python", "-m", "server.bot.main"]
