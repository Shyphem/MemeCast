/**
 * MemeCast — Effets Visuels
 *
 * Fonctions utilitaires pour appliquer des effets CSS
 * aux éléments mème dans l'overlay.
 */

const Effects = {
    /**
     * Applique les classes de position à un élément.
     */
    applyPosition(element, position) {
        // Retirer toute position existante
        element.className = element.className
            .split(" ")
            .filter((c) => !c.startsWith("pos-"))
            .join(" ");

        if (position === "random") {
            const positions = [
                "top_left", "top", "top_right",
                "left", "center", "right",
                "bottom_left", "bottom", "bottom_right",
            ];
            position = positions[Math.floor(Math.random() * positions.length)];
        }

        element.classList.add(`pos-${position}`);
    },

    /**
     * Applique la classe de taille à un élément.
     */
    applySize(element, size) {
        element.classList.add(`size-${size || "medium"}`);
    },

    /**
     * Joue l'animation d'entrée.
     */
    animateIn(element, effect = "fade_in") {
        element.classList.add(`anim-${effect}`);
    },

    /**
     * Joue l'animation de sortie et retourne une Promise qui résout quand c'est fini.
     */
    animateOut(element, effect = "fade_out") {
        return new Promise((resolve) => {
            element.classList.remove("anim-fade_in", "anim-bounce", "anim-slide_in");
            element.classList.add(`anim-${effect}`);

            element.addEventListener("animationend", () => resolve(), { once: true });

            // Safety timeout au cas où l'animation ne se déclenche pas
            setTimeout(resolve, 600);
        });
    },

    /**
     * Applique un effet continu (spin, shake, flip).
     */
    applyContinuousEffect(element, effects) {
        if (!effects || !Array.isArray(effects)) return;

        for (const fx of effects) {
            if (["spin", "shake", "flip"].includes(fx)) {
                element.classList.add(`effect-${fx}`);
            }
        }
    },

    /**
     * Crée un emoji flottant pour les réactions.
     */
    createEmojiRain(container, emoji, count = 5) {
        for (let i = 0; i < count; i++) {
            const el = document.createElement("div");
            el.className = "emoji-rain";
            el.textContent = emoji;
            el.style.left = `${Math.random() * 90 + 5}vw`;
            el.style.top = `${-(Math.random() * 10 + 5)}vh`;
            el.style.animationDelay = `${Math.random() * 0.8}s`;
            el.style.animationDuration = `${2 + Math.random() * 2}s`;
            el.style.fontSize = `${2 + Math.random() * 3}rem`;

            container.appendChild(el);

            // Auto-suppression après l'animation
            el.addEventListener("animationend", () => el.remove());

            // Safety cleanup
            setTimeout(() => {
                if (el.parentNode) el.remove();
            }, 6000);
        }
    },
};

// Export global pour les autres scripts
window.Effects = Effects;
