/**
 * FaceIn - Gestionnaire de stockage local IndexedDB
 * Module de persistance locale pour stocker le descripteur biométrique de référence.
 * Conforme au principe de confidentialité : aucune donnée biométrique brute ne quitte l'appareil.
 */
class StorageManager {
    constructor() {
        this.dbName = 'FaceInDB';
        this.dbVersion = 1;
        this.storeName = 'vectors';
        this.db = null;
    }

    /**
     * Ouvre ou initialise la base de données IndexedDB FaceInDB
     * @returns {Promise<IDBDatabase>} Instance de la base de données ouverte
     */
    init() {
        if (this.db) {
            return Promise.resolve(this.db);
        }

        return new Promise((resolve, reject) => {
            if (!window.indexedDB) {
                return reject(new Error("IndexedDB n'est pas supporté par ce navigateur."));
            }

            const request = window.indexedDB.open(this.dbName, this.dbVersion);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName, { keyPath: 'userId' });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                this.db.onclose = () => {
                    this.db = null;
                };
                resolve(this.db);
            };

            request.onerror = (event) => {
                reject(new Error(`Erreur lors de l'ouverture de la base IndexedDB: ${event.target.error?.message || event.target.error}`));
            };
        });
    }

    /**
     * Enregistre le vecteur de référence pour un utilisateur sous forme de Float64Array
     * @param {string} userId - Identifiant pseudo de l'utilisateur
     * @param {Float32Array|Float64Array|number[]} vector - Vecteur 128D de référence
     * @returns {Promise<boolean>} Résout à true si la sauvegarde a réussi
     */
    async saveVector(userId, vector) {
        const db = await this.init();

        return new Promise((resolve, reject) => {
            if (!userId || typeof userId !== 'string' || userId.trim() === '') {
                return reject(new Error("L'identifiant utilisateur (userId) est requis."));
            }

            if (!vector || vector.length !== 128) {
                return reject(new Error("Le vecteur biométrique doit comporter exactement 128 dimensions."));
            }

            // Stockage sous forme de Float64Array comme spécifié
            const float64Vector = vector instanceof Float64Array ? vector : new Float64Array(vector);

            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);

            const record = {
                userId: userId.trim(),
                vector: float64Vector,
                dateEnregistrement: new Date().toISOString()
            };

            const request = store.put(record);

            request.onsuccess = () => {
                resolve(true);
            };

            request.onerror = (event) => {
                reject(new Error(`Erreur lors de la sauvegarde du vecteur: ${event.target.error?.message || event.target.error}`));
            };
        });
    }

    /**
     * Récupère le vecteur de référence d'un utilisateur
     * @param {string} userId - Identifiant de l'utilisateur
     * @returns {Promise<Float64Array|null>} Le vecteur Float64Array ou null s'il n'existe pas
     */
    async getVector(userId) {
        const db = await this.init();

        return new Promise((resolve, reject) => {
            if (!userId) {
                return reject(new Error("L'identifiant utilisateur (userId) est requis."));
            }

            const transaction = db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.get(userId.trim());

            request.onsuccess = (event) => {
                const result = event.target.result;
                if (result && result.vector) {
                    const vec = result.vector instanceof Float64Array ? result.vector : new Float64Array(result.vector);
                    resolve(vec);
                } else {
                    resolve(null);
                }
            };

            request.onerror = (event) => {
                reject(new Error(`Erreur lors de la récupération du vecteur: ${event.target.error?.message || event.target.error}`));
            };
        });
    }

    /**
     * Supprime le vecteur associé à un utilisateur
     * @param {string} userId - Identifiant de l'utilisateur
     * @returns {Promise<boolean>} Résout à true si la suppression a réussi
     */
    async deleteVector(userId) {
        const db = await this.init();

        return new Promise((resolve, reject) => {
            if (!userId) {
                return reject(new Error("L'identifiant utilisateur (userId) est requis."));
            }

            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.delete(userId.trim());

            request.onsuccess = () => {
                resolve(true);
            };

            request.onerror = (event) => {
                reject(new Error(`Erreur lors de la suppression du vecteur: ${event.target.error?.message || event.target.error}`));
            };
        });
    }

    /**
     * Vérifie si un vecteur existe pour l'identifiant donné
     * @param {string} userId - Identifiant de l'utilisateur
     * @returns {Promise<boolean>} True si le vecteur existe en base locale
     */
    async hasVector(userId) {
        const vec = await this.getVector(userId);
        return vec !== null;
    }
}

// Exposition globale
window.StorageManager = new StorageManager();
