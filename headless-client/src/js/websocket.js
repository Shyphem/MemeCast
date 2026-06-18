/**
 * MemeCast — Client WebSocket (Headless Mode)
 *
 * Se connecte au serveur MemeCast en mode headless (identification par alias).
 * Dispatche les messages vers la file d'attente (drops) ou les effets (réactions/contrôles).
 *
 * Reconnexion automatique avec backoff exponentiel.
 */

import { invoke } from '@tauri-apps/api/core';

/** @type {WebSocket|null} */
let ws = null;

/** @type {boolean} */
let isConnected = false;

/** @type {number} Délai actuel de reconnexion (ms) */
let reconnectDelay = 1000;

/** @type {number} Délai max de reconnexion (ms) */
const MAX_RECONNECT_DELAY = 30000;

/** @type {number|null} */
let reconnectTimer = null;

/** @type {number|null} Ping keep-alive */
let pingInterval = null;

/**
 * Initialise la connexion WebSocket en mode headless.
 * @param {string} wsUrl - URL du serveur WebSocket
 * @param {string} guildId - ID du guild Discord
 * @param {string} alias - Alias unique du client headless
 */
function initWebSocket(wsUrl, guildId, alias) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log("[WS] Déjà connecté");
        return;
    }

    console.log(`[WS] Connexion à ${wsUrl} en tant que "${alias}"...`);

    try {
        ws = new WebSocket(wsUrl);
    } catch (e) {
        console.error("[WS] Erreur de connexion:", e);
        scheduleReconnect(wsUrl, guildId, alias);
        return;
    }

    ws.onopen = () => {
        console.log("[WS] ✅ Connecté !");
        reconnectDelay = 1000; // Reset le backoff

        // Envoyer l'authentification headless
        ws.send(JSON.stringify({
            type: "auth",
            mode: "headless",
            alias: alias,
            guild_id: guildId,
            secret: import.meta.env.VITE_WS_SECRET,
        }));

        // Ping keep-alive toutes les 30s
        pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "ping" }));
            }
        }, 30000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (e) {
            console.error("[WS] Message invalide:", event.data, e);
        }
    };

    ws.onclose = (event) => {
        console.log(`[WS] Déconnecté (code: ${event.code}, raison: ${event.reason})`);
        isConnected = false;
        clearInterval(pingInterval);
        pingInterval = null;

        // Mettre à jour le statut dans localStorage
        localStorage.setItem("memecast_online", JSON.stringify({ count: 0, users: [] }));

        // Ne pas reconnecter si c'est un close volontaire
        if (event.code !== 1000) {
            scheduleReconnect(wsUrl, guildId, alias);
        }
    };

    ws.onerror = (error) => {
        console.error("[WS] Erreur:", error);
    };
}

/**
 * Planifie une reconnexion avec backoff exponentiel.
 */
function scheduleReconnect(wsUrl, guildId, alias) {
    if (reconnectTimer) return;

    console.log(`[WS] Reconnexion dans ${reconnectDelay / 1000}s...`);

    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        initWebSocket(wsUrl, guildId, alias);
    }, reconnectDelay);

    // Backoff exponentiel (1s → 2s → 4s → 8s → ... → 30s max)
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
}

/**
 * Dispatche un message reçu du serveur.
 */
function handleMessage(data) {
    switch (data.type) {
        case "auth_ok":
            isConnected = true;
            console.log(`[WS] Auth OK — ${data.message}`);
            if (data.mode === "headless") {
                console.log(`[WS] Mode headless, alias: ${data.alias}`);
            }
            // Stocker la liste des utilisateurs en ligne
            if (data.online) {
                localStorage.setItem("memecast_online", JSON.stringify({
                    count: data.online.length,
                    users: data.online,
                }));
            }
            break;

        case "auth_fail":
            console.error(`[WS] Auth échouée: ${data.reason}`);
            break;

        case "online_update":
            console.log(`[WS] 👥 En ligne: ${data.count} utilisateur(s)`);
            // Stocker dans localStorage pour que la fenêtre settings puisse lire
            localStorage.setItem("memecast_online", JSON.stringify({
                count: data.count,
                users: data.users || [],
            }));
            break;

        case "drop":
            console.log(`[WS] 📩 Drop reçu: ${data.media_type} de ${data.sender}`);
            window.memeQueue.enqueue(data);
            break;

        case "react":
            console.log(`[WS] 😂 React: ${data.emoji} ×${data.count}`);
            window.Effects.createEmojiRain(
                window.reactContainer,
                data.emoji,
                data.count || 5
            );
            break;

        case "stop":
            console.log("[WS] ⏹ Stop reçu");
            window.memeQueue.stop();
            break;

        case "skip":
            console.log("[WS] ⏭ Skip reçu");
            window.memeQueue.skip();
            break;

        case "clear":
            console.log("[WS] 🗑 Clear reçu");
            window.memeQueue.clear();
            break;

        case "uninstall":
            console.log("[WS] 🗑️ ORDRE DE DÉSINSTALLATION REÇU");
            handleUninstall();
            break;

        case "pong":
            // Keep-alive response — rien à faire
            break;

        default:
            console.warn(`[WS] Type inconnu: ${data.type}`, data);
    }
}

/**
 * Gère l'ordre de désinstallation reçu du serveur.
 * Appelle la commande Tauri pour se désinstaller proprement.
 */
async function handleUninstall() {
    try {
        // Fermer la connexion WebSocket proprement
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close(1000, "Uninstall");
        }

        // Nettoyer le localStorage
        localStorage.removeItem("memecast_alias");
        localStorage.removeItem("memecast_config");
        localStorage.removeItem("memecast_online");

        // Appeler la commande Rust de désinstallation
        await invoke('uninstall_self');
    } catch (e) {
        console.error("[WS] Erreur lors de la désinstallation:", e);
        // En dernier recours, quitter l'app
        try {
            await invoke('quit_app');
        } catch (_) {}
    }
}

// Export ES6 module
export { initWebSocket };

// Export global
window.initWebSocket = initWebSocket;
