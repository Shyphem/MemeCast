/**
 * MemeCast — Settings App Logic
 *
 * Gère l'interface de réglages :
 *   - Sauvegarde/restauration des préférences dans localStorage
 *   - Sliders, toggles, position grid
 *   - Boutons de la barre de titre (minimiser, fermer)
 *   - Connexion WebSocket (les réglages sont partagés avec la fenêtre overlay)
 */

import { enable, isEnabled, disable } from '@tauri-apps/plugin-autostart';
import { check } from '@tauri-apps/plugin-updater';
import { getCurrentWindow } from '@tauri-apps/api/window';

document.addEventListener("DOMContentLoaded", async () => {
    // ============================================
    // Références DOM
    // ============================================

    const $ = (sel) => document.querySelector(sel);

    const elements = {
        // Connexion
        wsUrl: $("#input-ws-url"),
        guildId: $("#input-guild-id"),
        discordId: $("#input-discord-id"),
        btnConnect: $("#btn-connect"),
        statusDot: $(".status-dot"),
        statusText: $(".status-text"),

        // Système
        toggleAutostart: $("#toggle-autostart"),
        btnCheckUpdate: $("#btn-check-update"),

        // Audio
        sliderVolume: $("#slider-volume"),
        valVolume: $("#val-volume"),
        sliderOpacity: $("#slider-opacity"),
        valOpacity: $("#val-opacity"),
        sliderDuration: $("#slider-duration"),
        valDuration: $("#val-duration"),
        toggleAnnounce: $("#toggle-announce"),

        // Position
        toggleRandomPos: $("#toggle-random-pos"),
        positionGrid: $("#position-grid"),
        posButtons: document.querySelectorAll(".pos-btn"),

        // Titlebar
        btnMinimize: $("#btn-minimize"),
        btnClose: $("#btn-close"),
    };

    // ============================================
    // Config (localStorage)
    // ============================================

    const CONFIG_KEY = "memecast_config";

    function loadConfig() {
        try {
            return JSON.parse(localStorage.getItem(CONFIG_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function saveConfig(config) {
        localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
    }

    async function restoreUI() {
        const cfg = loadConfig();

        // Connexion
        elements.wsUrl.value = cfg.ws_url || "ws://localhost:8000/ws";
        elements.guildId.value = cfg.guild_id || "";
        elements.discordId.value = cfg.discord_id || "";

        // Audio
        elements.sliderVolume.value = cfg.volume ?? 50;
        elements.valVolume.textContent = `${cfg.volume ?? 50}%`;
        elements.sliderOpacity.value = cfg.opacity ?? 100;
        elements.valOpacity.textContent = `${cfg.opacity ?? 100}%`;
        elements.sliderDuration.value = cfg.image_duration ?? 8;
        elements.valDuration.textContent = `${cfg.image_duration ?? 8}s`;
        elements.toggleAnnounce.checked = cfg.announce_sound !== false;

        // Position
        elements.toggleRandomPos.checked = cfg.random_position === true;
        const activePos = cfg.position || "center";

        elements.posButtons.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.pos === activePos);
        });

        // Désactiver la grille si aléatoire
        updatePositionGridState(cfg.random_position === true);

        // Autostart
        try {
            elements.toggleAutostart.checked = await isEnabled();
        } catch (e) {
            console.log("[System] Autostart non supporté dans cet environnement");
            elements.toggleAutostart.disabled = true;
        }
    }

    function collectConfig() {
        const activePos = document.querySelector(".pos-btn.active");

        return {
            ws_url: elements.wsUrl.value.trim(),
            guild_id: elements.guildId.value.trim(),
            discord_id: elements.discordId.value.trim(),
            volume: parseInt(elements.sliderVolume.value),
            opacity: parseInt(elements.sliderOpacity.value),
            image_duration: parseInt(elements.sliderDuration.value),
            announce_sound: elements.toggleAnnounce.checked,
            random_position: elements.toggleRandomPos.checked,
            position: elements.toggleRandomPos.checked
                ? "random"
                : (activePos?.dataset.pos || "center"),
        };
    }

    function autoSave() {
        saveConfig(collectConfig());
    }

    // ============================================
    // Sliders
    // ============================================

    function setupSlider(slider, display, suffix, onChange) {
        slider.addEventListener("input", () => {
            display.textContent = `${slider.value}${suffix}`;
            autoSave();
            if (onChange) onChange(slider.value);
        });
    }

    setupSlider(elements.sliderVolume, elements.valVolume, "%");
    setupSlider(elements.sliderOpacity, elements.valOpacity, "%");
    setupSlider(elements.sliderDuration, elements.valDuration, "s");

    // ============================================
    // Toggles
    // ============================================

    elements.toggleAnnounce.addEventListener("change", autoSave);

    elements.toggleRandomPos.addEventListener("change", () => {
        updatePositionGridState(elements.toggleRandomPos.checked);
        autoSave();
    });

    elements.toggleAutostart.addEventListener("change", async () => {
        try {
            if (elements.toggleAutostart.checked) {
                await enable();
            } else {
                await disable();
            }
        } catch (e) {
            console.error("[System] Erreur autostart:", e);
        }
    });

    elements.btnCheckUpdate.addEventListener("click", async () => {
        elements.btnCheckUpdate.disabled = true;
        elements.btnCheckUpdate.textContent = "Recherche...";
        try {
            const update = await check();
            if (update) {
                elements.btnCheckUpdate.textContent = "Téléchargement...";
                await update.downloadAndInstall();
                elements.btnCheckUpdate.textContent = "Redémarrage requis";
            } else {
                elements.btnCheckUpdate.textContent = "À jour !";
                setTimeout(() => {
                    elements.btnCheckUpdate.textContent = "Vérifier";
                    elements.btnCheckUpdate.disabled = false;
                }, 3000);
            }
        } catch (e) {
            console.error("[System] Erreur updater:", e);
            elements.btnCheckUpdate.textContent = "Erreur";
            setTimeout(() => {
                elements.btnCheckUpdate.textContent = "Vérifier";
                elements.btnCheckUpdate.disabled = false;
            }, 3000);
        }
    });

    function updatePositionGridState(isRandom) {
        elements.posButtons.forEach((btn) => {
            btn.style.opacity = isRandom ? "0.3" : "1";
            btn.style.pointerEvents = isRandom ? "none" : "auto";
        });
    }

    // ============================================
    // Position Grid
    // ============================================

    elements.posButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            elements.posButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            autoSave();
        });
    });

    // ============================================
    // Connexion
    // ============================================

    function setStatus(state, text) {
        elements.statusDot.className = `status-dot ${state}`;
        elements.statusText.textContent = text;
    }

    elements.btnConnect.addEventListener("click", () => {
        const wsUrl = elements.wsUrl.value.trim();
        const guildId = elements.guildId.value.trim();
        const discordId = elements.discordId.value.trim();

        if (!guildId || !discordId) {
            setStatus("offline", "❌ Guild ID et Discord ID requis");
            return;
        }

        autoSave();
        setStatus("connecting", "Connexion en cours...");
        elements.btnConnect.textContent = "Connexion...";
        elements.btnConnect.disabled = true;

        // Tester la connexion WebSocket
        try {
            const testWs = new WebSocket(wsUrl);

            testWs.onopen = () => {
                // Envoyer l'auth
                testWs.send(JSON.stringify({
                    type: "auth",
                    guild_id: guildId,
                    discord_id: discordId,
                }));
            };

            testWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === "auth_ok") {
                        setStatus("online", `✅ Connecté ! (${data.online?.length || 0} en ligne)`);
                        elements.btnConnect.textContent = "Reconnecter";
                    } else if (data.type === "auth_fail") {
                        setStatus("offline", `❌ ${data.reason}`);
                        elements.btnConnect.textContent = "Se connecter";
                    }
                } catch (e) {
                    // ignore
                }
                elements.btnConnect.disabled = false;
                // Garder la connexion ouverte pour la fenêtre settings aussi
                // (la fenêtre overlay a sa propre connexion)
            };

            testWs.onerror = () => {
                setStatus("offline", "❌ Impossible de se connecter au serveur");
                elements.btnConnect.textContent = "Se connecter";
                elements.btnConnect.disabled = false;
            };

            testWs.onclose = () => {
                if (elements.statusDot.classList.contains("connecting")) {
                    setStatus("offline", "❌ Connexion perdue");
                    elements.btnConnect.textContent = "Se connecter";
                    elements.btnConnect.disabled = false;
                }
            };
        } catch (e) {
            setStatus("offline", "❌ URL invalide");
            elements.btnConnect.textContent = "Se connecter";
            elements.btnConnect.disabled = false;
        }
    });

    // ============================================
    // Titlebar Buttons (Tauri IPC)
    // ============================================

    elements.btnMinimize.addEventListener("click", async () => {
        try {
            await getCurrentWindow().minimize();
        } catch {
            // Fallback si pas dans Tauri (dev dans navigateur)
            console.log("[UI] Minimize (non-Tauri environment)");
        }
    });

    elements.btnClose.addEventListener("click", async () => {
        try {
            await getCurrentWindow().hide();
        } catch {
            console.log("[UI] Close (non-Tauri environment)");
        }
    });

    // ============================================
    // Init
    // ============================================

    restoreUI();
    console.log("[Settings] MemeCast settings loaded");
});
