/**
 * MemeCast — File d'attente intelligente
 *
 * Gère la séquence d'affichage des mèmes :
 *   - Les mèmes sont empilés en FIFO
 *   - Un seul mème est affiché à la fois
 *   - Quand un mème expire, le suivant est automatiquement affiché
 *   - Supporte stop, skip, clear
 */

class MemeQueue {
    constructor() {
        /** @type {Array<Object>} */
        this.queue = [];

        /** @type {Object|null} */
        this.currentDrop = null;

        /** @type {number|null} */
        this.currentTimer = null;

        /** @type {boolean} */
        this.isPlaying = false;

        /** @type {Function|null} Callback appelé quand un drop doit être affiché */
        this.onDisplay = null;

        /** @type {Function|null} Callback appelé quand un drop doit être retiré */
        this.onRemove = null;
    }

    /**
     * Ajoute un drop à la file.
     * Si rien n'est en cours, l'affiche immédiatement.
     */
    enqueue(drop) {
        this.queue.push(drop);
        console.log(`[Queue] + ${drop.media_type} de ${drop.sender} (file: ${this.queue.length})`);

        if (!this.isPlaying) {
            this._playNext();
        }
    }

    /**
     * Affiche le prochain drop de la file.
     */
    _playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            this.currentDrop = null;
            console.log("[Queue] File vide — en attente");
            return;
        }

        this.isPlaying = true;
        this.currentDrop = this.queue.shift();

        console.log(
            `[Queue] ▶ ${this.currentDrop.media_type} de ${this.currentDrop.sender} ` +
            `(durée: ${this.currentDrop.duration}s, restant: ${this.queue.length})`
        );

        // Callback d'affichage
        if (this.onDisplay) {
            this.onDisplay(this.currentDrop);
        }

        // Timer pour passer au suivant
        const duration = (this.currentDrop.duration || 8) * 1000;
        this.currentTimer = setTimeout(() => {
            this._finishCurrent();
        }, duration);
    }

    /**
     * Termine le drop en cours et passe au suivant.
     */
    async _finishCurrent() {
        if (this.currentTimer) {
            clearTimeout(this.currentTimer);
            this.currentTimer = null;
        }

        if (this.onRemove && this.currentDrop) {
            await this.onRemove(this.currentDrop);
        }

        this.currentDrop = null;

        // Petit délai entre les drops pour respirer
        setTimeout(() => this._playNext(), 300);
    }

    /**
     * Stoppe le drop en cours (ne passe PAS au suivant).
     */
    async stop() {
        console.log("[Queue] ⏹ Stop");
        if (this.currentTimer) {
            clearTimeout(this.currentTimer);
            this.currentTimer = null;
        }
        if (this.onRemove && this.currentDrop) {
            await this.onRemove(this.currentDrop);
        }
        this.currentDrop = null;
        this.isPlaying = false;
    }

    /**
     * Skip le drop en cours → passe au suivant.
     */
    async skip() {
        console.log("[Queue] ⏭ Skip");
        await this._finishCurrent();
    }

    /**
     * Vide toute la file et stoppe le drop en cours.
     */
    async clear() {
        console.log("[Queue] 🗑 Clear");
        this.queue = [];
        await this.stop();
    }

    /**
     * Nombre de drops en attente (hors celui en cours).
     */
    get pending() {
        return this.queue.length;
    }
}

// Export global
window.MemeQueue = MemeQueue;
