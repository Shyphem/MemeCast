/**
 * MemeCast — Moteur de rendu Overlay
 *
 * Crée et affiche les éléments mème (image, GIF, vidéo, texte)
 * dans la fenêtre overlay transparente.
 */

// Containers DOM
const overlayContainer = document.getElementById("overlay-container");
const reactContainer = document.getElementById("react-container");

// File d'attente
const memeQueue = new MemeQueue();

/**
 * Crée l'élément DOM pour un drop.
 */
function createMemeElement(drop) {
    const wrapper = document.createElement("div");
    wrapper.className = "meme-element";
    wrapper.id = `meme-${drop.id}`;

    switch (drop.media_type) {
        case "image":
        case "gif": {
            const img = document.createElement("img");
            img.src = drop.media_url;
            img.alt = "meme";
            img.draggable = false;
            img.onerror = () => {
                console.error(`[Overlay] Image load error: ${drop.media_url}`);
                wrapper.remove();
                memeQueue.skip();
            };
            wrapper.appendChild(img);
            break;
        }

        case "video": {
            const video = document.createElement("video");
            video.src = drop.media_url;
            video.autoplay = true;
            video.loop = false;
            video.muted = false; // Son activé par défaut
            video.playsInline = true;

            // Lire la config de volume
            const config = JSON.parse(localStorage.getItem("memecast_config") || "{}");
            video.volume = (config.volume ?? 50) / 100;

            video.onerror = () => {
                console.error(`[Overlay] Video load error: ${drop.media_url}`);
                wrapper.remove();
                memeQueue.skip();
            };

            wrapper.appendChild(video);
            break;
        }

        case "audio": {
            // Pas d'élément visuel pour l'audio pur
            // Mais on cache quand même le wrapper au cas où
            wrapper.style.display = "none";
            break;
        }

        case "text": {
            const textDiv = document.createElement("div");
            textDiv.className = "meme-text";
            textDiv.textContent = drop.text || "...";
            wrapper.appendChild(textDiv);
            break;
        }

        default:
            console.warn(`[Overlay] Type inconnu: ${drop.media_type}`);
            return null;
    }

    // Badge sender
    if (drop.sender && drop.sender !== "unknown") {
        const badge = document.createElement("div");
        badge.className = "meme-sender";
        badge.textContent = `par ${drop.sender}`;
        wrapper.appendChild(badge);
    }

    return wrapper;
}

/**
 * Affiche un drop dans l'overlay.
 */
function displayDrop(drop) {
    const element = createMemeElement(drop);
    if (!element) return;

    // Lire la configuration locale pour surcharger les valeurs par défaut du bot
    const config = JSON.parse(localStorage.getItem("memecast_config") || "{}");
    const finalPosition = config.position || drop.position;

    // Appliquer taille et position
    Effects.applySize(element, drop.size);
    Effects.applyPosition(element, finalPosition);

    // Ajouter au DOM
    overlayContainer.appendChild(element);

    // Animation d'entrée
    const entryEffect = drop.effects?.find(e =>
        ["fade_in", "bounce", "slide_in"].includes(e)
    ) || "fade_in";
    Effects.animateIn(element, entryEffect);

    // Effets continus
    Effects.applyContinuousEffect(element, drop.effects);

    // Jouer le son d'annonce si activé
    playAnnounceSoundIfEnabled();

    // Jouer le son attaché
    if (drop.sound_url) {
        playSound(drop.sound_url);
    }

    console.log(`[Overlay] ✅ Affiché: ${drop.media_type} (${drop.id})`);
}

/**
 * Retire un drop de l'overlay avec animation de sortie.
 */
async function removeDrop(drop) {
    const element = document.getElementById(`meme-${drop.id}`);
    if (!element) return;

    const exitEffect = drop.effects?.find(e =>
        ["fade_out", "slide_out"].includes(e)
    ) || "fade_out";

    await Effects.animateOut(element, exitEffect);
    element.remove();

    console.log(`[Overlay] ❌ Retiré: ${drop.id}`);
}

/**
 * Joue un son court.
 */
function playSound(url) {
    try {
        const audio = new Audio(url);
        const config = JSON.parse(localStorage.getItem("memecast_config") || "{}");
        audio.volume = (config.volume ?? 50) / 100;

        // Limiter à 10 secondes
        setTimeout(() => {
            audio.pause();
            audio.currentTime = 0;
        }, 10000);

        audio.play().catch(e => console.warn("[Audio] Erreur:", e));
    } catch (e) {
        console.warn("[Audio] Impossible de jouer:", e);
    }
}

/**
 * Son d'annonce quand un mème arrive.
 */
function playAnnounceSoundIfEnabled() {
    const config = JSON.parse(localStorage.getItem("memecast_config") || "{}");
    if (config.announce_sound !== false) {
        // Son système court (bip)
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = "sine";
            gain.gain.value = 0.15;
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.3);
        } catch (e) {
            // Pas de son — pas grave
        }
    }
}

// --- Connecter la queue aux fonctions d'affichage ---
memeQueue.onDisplay = displayDrop;
memeQueue.onRemove = removeDrop;

// Export global
window.memeQueue = memeQueue;
window.overlayContainer = overlayContainer;
window.reactContainer = reactContainer;
