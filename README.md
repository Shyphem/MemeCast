# 🚀 MemeCast

MemeCast est un système interactif composé d'un **Bot Discord** et d'une application **Desktop Overlay**.
Il permet à une communauté Discord de "lancer" (drop) des images, des GIFs, des vidéos YouTube, des TikToks, ou des sons directement sur les écrans des autres membres du serveur, en temps réel et en surimpression (overlay transparent).

---

## 🛠️ Architecture du projet

Le projet est divisé en deux parties principales :
1. **Serveur (`/server`)** : Le cœur du système. Il contient le bot Discord (en Python via `discord.py`) et un serveur WebSocket (via `FastAPI` et `Uvicorn`) qui agit comme un hub pour transmettre les mèmes aux clients connectés.
2. **Client (`/client`)** : L'application PC (développée avec `Tauri`, `Rust`, et `Vite/Vanilla JS`). Elle affiche une interface de réglages (pour se connecter) et une fenêtre totalement transparente (overlay) qui se superpose à vos jeux ou votre bureau pour afficher le contenu.

---

## ⚙️ Prérequis

### Pour le Serveur
- Un serveur VPS (Linux de préférence) ou un PC allumé H24
- [Docker](https://docs.docker.com/get-docker/) et [Docker Compose](https://docs.docker.com/compose/install/)

### Pour le Client (Compilation)
- Windows (ou macOS/Linux)
- [Node.js](https://nodejs.org/) (v18+)
- [Rust & Cargo](https://rustup.rs/) (Environnement de compilation C++ requis sur Windows, voir les [prérequis Tauri](https://tauri.app/v1/guides/getting-started/prerequisites/))

---

## 🤖 1. Configuration du Bot Discord

Avant de lancer le serveur, vous devez créer le bot sur Discord :

1. Allez sur le [Discord Developer Portal](https://discord.com/developers/applications).
2. Cliquez sur **"New Application"** et donnez-lui le nom `MemeCast`.
3. Allez dans l'onglet **"Bot"** :
   - Récupérez votre **Token** (gardez-le secret).
   - ⚠️ **TRÈS IMPORTANT** : Dans la section **Privileged Gateway Intents**, activez **SERVER MEMBERS INTENT** (nécessaire pour pouvoir cibler un membre avec `@pseudo`).
4. Allez dans l'onglet **"OAuth2" -> "URL Generator"** :
   - Cochez les scopes `bot` et `applications.commands`.
   - Cochez les permissions : `Send Messages`, `Embed Links`, `Attach Files`.
   - Utilisez l'URL générée en bas pour inviter le bot sur votre serveur.

---

## 🖥️ 2. Installation du Serveur (Bot + WebSocket)

Le serveur gère les commandes Discord et dispatche les médias aux applications client.

1. Allez dans le dossier du projet ou clonez-le sur votre VPS.
2. Créez un fichier `.env` à la racine du projet (au même niveau que le `docker-compose.yml`) :

```env
# Le Token de votre bot Discord
DISCORD_TOKEN=MTEw...votre.token.secret...

# L'ID de votre serveur Discord par défaut
GUILD_ID=123456789012345678
```

3. Lancez le serveur avec Docker Compose :

```bash
sudo docker compose up -d --build
```

Le bot va se connecter à Discord et le serveur WebSocket écoutera sur le port `8000`.

---

## 💻 3. Compilation du Client (Application PC)

L'application doit être compilée pour Windows (en `.exe`).

1. Ouvrez un terminal et allez dans le dossier du client :
```bash
cd client
```

2. Installez les dépendances Node.js :
```bash
npm install
```

3. Lancez la compilation avec Tauri :
```bash
npm run tauri build
```
*(Le premier build peut prendre un peu de temps car il compile tout l'environnement Rust).*

4. Une fois terminé, le programme d'installation se trouvera ici :
`client/src-tauri/target/release/bundle/nsis/MemeCast_0.2.0_x64-setup.exe`

Envoyez cet installateur à vos amis !

---

## 🎮 4. Utilisation

### Côté Client (Application)
1. Lancez MemeCast.
2. Remplissez vos informations dans les réglages :
   - **Ton Pseudo** : Votre nom (pour la liste des connectés).
   - **Adresse du serveur** : `ws://VOTRE_IP_VPS:8000/ws` (ou `ws://localhost:8000/ws` si test en local).
   - **Guild ID** : L'ID du serveur Discord.
   - **Ton Discord ID** : Votre propre ID utilisateur Discord (nécessaire pour que les autres puissent vous cibler).
3. Cliquez sur **Se connecter**. Le voyant passera au vert et vous verrez les autres personnes en ligne.
4. Réglez le **volume**, **l'opacité**, la **durée d'affichage** et fermez la fenêtre (elle restera active en arrière-plan).

### Côté Discord (Commandes)
Dans votre serveur Discord, utilisez la commande `/drop` :

```text
/drop url:https://youtu.be/xxx
/drop media:[Fichier MP4/MP3/GIF/PNG]
/drop text:"Bonjour tout le monde"
```

**Options avancées du `/drop` :**
- `target` : Mentionnez un membre précis (ex: `@Shyphem`) pour que le mème ne s'affiche QUE sur son écran !
- `size` : Choisissez la taille d'affichage (Petit, Moyen, Grand, Plein écran).
- `sound` : Attachez un fichier audio supplémentaire (ex: un `.mp3`) qui se jouera en même temps que votre image/GIF.

**Contrôle de la file d'attente :**
- `/skip` : Passe au mème suivant.
- `/stop` : Arrête le mème en cours.
- `/clear` : Vide entièrement la file d'attente.

---

## ⚙️ Dépannage

- **Rien ne s'affiche sur l'écran d'un ami ?**
  Vérifiez que son application est bien au premier plan (ou en mode plein écran fenêtré pour les jeux) et que son `Discord ID` est le bon.
- **La commande /drop ne trouve pas les membres (`target`) ?**
  Assurez-vous d'avoir bien coché **SERVER MEMBERS INTENT** dans le portail développeur Discord et redémarrez le container Docker du bot.
- **Le client indique "Connexion perdue" en boucle ?**
  Vérifiez que le port `8000` est bien ouvert sur le pare-feu (ufw/iptables) de votre VPS.
