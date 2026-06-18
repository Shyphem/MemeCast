import { invoke } from '@tauri-apps/api/core';
import { emit } from '@tauri-apps/api/event';

const inputAlias = document.getElementById("input-alias");
const btnSave = document.getElementById("btn-save");

// Charger l'existant s'il y en a un
inputAlias.value = localStorage.getItem("memecast_alias") || "";

btnSave.addEventListener("click", async () => {
    const alias = inputAlias.value.trim();

    if (!alias) {
        alert("Veuillez entrer un alias pour ce client.");
        return;
    }

    // Sauvegarde l'alias
    localStorage.setItem("memecast_alias", alias);

    // Config par défaut si pas encore créée
    if (!localStorage.getItem("memecast_config")) {
        localStorage.setItem("memecast_config", JSON.stringify({
            volume: 50,
            opacity: 100,
            announce_sound: true,
            random_position: true,
            position: "pos-random"
        }));
    }

    // Prévenir l'overlay que la config est prête
    await emit('config-saved');

    // Fermer la fenêtre de setup
    await invoke('close_setup');
});
