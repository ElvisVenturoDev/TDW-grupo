/* =========================================================
   UTILIDADES COMPARTIDAS - MISKYLAC
   Se carga antes que el resto de scripts (ver base.html).
   Evita repetir en cada archivo el acceso a localStorage,
   el formateo de precios y el debounce.
   ========================================================= */

window.Miskylac = window.Miskylac || {};

Miskylac.storage = {
    get(key, fallback = null) {
        try {
            const value = localStorage.getItem(key);
            return value ?? fallback;
        } catch {
            return fallback;
        }
    },

    set(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch {
            // El sitio sigue funcionando si el navegador bloquea el almacenamiento.
        }
    },

    getJSON(key, fallback = null) {
        try {
            const value = JSON.parse(localStorage.getItem(key) || "null");
            return value ?? fallback;
        } catch {
            return fallback;
        }
    },

    setJSON(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch {
            // Ignorar restricciones de almacenamiento.
        }
    }
};

Miskylac.formatPrice = (amount) => `S/ ${Number(amount || 0).toFixed(2)}`;

Miskylac.debounce = (callback, delay = 180) => {
    let timeoutId;
    return (...args) => {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => callback(...args), delay);
    };
};

Miskylac.prefersReducedMotion = () =>
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
