# 🚀 MemeCast

MemeCast is an interactive system consisting of a **Discord Bot** and a **Desktop Overlay Application**.
It allows a Discord community to "drop" images, GIFs, YouTube videos or sounds directly onto the screens of other server members in real-time, using a transparent overlay. Like the Live Chat of the CacaBox.

---

## 🛠️ Project Architecture

The project is divided into two main parts:
1. **Server (`/server`)**: The core of the system. It contains the Discord bot (in Python using `discord.py`) and a WebSocket server (using `FastAPI` and `Uvicorn`) that acts as a hub to transmit memes to connected clients.
2. **Client (`/client`)**: The desktop application (developed with `Tauri`, `Rust`, and `Vite/Vanilla JS`). It provides a settings interface (for connection setup) and a fully transparent overlay window that sits on top of your games or desktop to display the content.

---

## ⚙️ Prerequisites

### For the Server
- A VPS server (Linux preferred)
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### For the Client (Build Process)
- Windows (or macOS/Linux)
- [Node.js](https://nodejs.org/) (v18+)
- [Rust & Cargo](https://rustup.rs/) (C++ build tools required on Windows, see [Tauri prerequisites](https://tauri.app/v1/guides/getting-started/prerequisites/))

---

## 🤖 1. Discord Bot Configuration

Before starting the server, you need to create the bot on Discord:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click on **"New Application"** and name it `MemeCast`.
3. Go to the **"Bot"** tab:
   - Copy your **Token** (keep it secret).
   - ⚠️ **VERY IMPORTANT**: Under the **Privileged Gateway Intents** section, enable **SERVER MEMBERS INTENT** (this is required to target a specific member using `@username`).
4. Go to the **"OAuth2" -> "URL Generator"** tab:
   - Check the `bot` and `applications.commands` scopes.
   - Check the following permissions: `Send Messages`, `Embed Links`, `Attach Files`.
   - Use the generated URL at the bottom to invite the bot to your server.

---

## 🖥️ 2. Server Installation (Bot + WebSocket)

The server handles Discord commands and dispatches media to the client applications.

1. Navigate to the project directory or clone it onto your VPS.
2. Create a `.env` file at the root of the project (next to `docker-compose.yml`):

```env
# Your Discord bot Token
DISCORD_TOKEN=MTEw...your.secret.token...

# Your default Discord Server (Guild) ID
GUILD_ID=123456789012345678
```

3. Start the server using Docker Compose:

```bash
sudo docker compose up -d --build
```

The bot will connect to Discord and the WebSocket server will listen on port `8000`.

---

## 💻 3. Client Compilation (Desktop App)

The application needs to be compiled for Windows (as an `.exe`).

1. Open a terminal and navigate to the client folder:
```bash
cd client
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the build process with Tauri:
```bash
npm run tauri build
```
*(The first build may take some time as it compiles the entire Rust environment).*

4. Once finished, the installer will be located here:
`client/src-tauri/target/release/bundle/nsis/MemeCast_0.2.0_x64-setup.exe`

Send this installer to your friends!

---

## 🎮 4. Usage

### Client Side (Application)
1. Launch MemeCast.
2. Fill in your details in the settings:
   - **Username (Ton Pseudo)**: Your display name (for the online users list).
   - **Server Address (Adresse du serveur)**: `ws://YOUR_VPS_IP:8000/ws` (or `ws://localhost:8000/ws` for local testing).
   - **Guild ID**: The Discord server ID.
   - **Your Discord ID (Ton Discord ID)**: Your personal Discord user ID (needed so others can target you).
3. Click **Connect (Se connecter)**. The status indicator will turn green and you will see other online users.
4. Adjust the **volume**, **opacity**, **display duration**, and close the window (it will remain active in the background).

### Discord Side (Commands)
In your Discord server, use the `/drop` command:

```text
/drop url:https://youtu.be/xxx
/drop media:[MP4/MP3/GIF/PNG File]
/drop text:"Hello everyone"
```

**Advanced `/drop` options:**
- `target`: Tag a specific member (e.g., `@Shyphem`) so the meme ONLY appears on their screen!
- `size`: Choose the display size (Small, Medium, Large, Fullscreen).
- `sound`: Attach an additional audio file (e.g., an `.mp3`) that will play at the same time as your image/GIF.

**Queue control:**
- `/skip`: Skips to the next meme.
- `/stop`: Stops the current meme.
- `/clear`: Completely clears the meme queue.

---

## ⚙️ Troubleshooting

- **Nothing is showing up on a friend's screen?**
  Ensure their application is running (or in borderless windowed mode for games) and that their `Discord ID` is correct in the settings.
- **The /drop command can't find members (`target`)?**
  Make sure you have enabled the **SERVER MEMBERS INTENT** in the Discord Developer Portal and restart the bot's Docker container.
- **The client repeatedly says "Connection lost"?**
  Check that port `8000` is open on your VPS firewall (ufw/iptables).
