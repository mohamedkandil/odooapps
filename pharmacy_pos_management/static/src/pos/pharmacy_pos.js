/** @odoo-module **/

/**
 * Lightweight POS bootstrap for pharmacy-specific styling and runtime flags.
 *
 * The backend models and APIs expose stock, expiry, prescription, and payment
 * data for a dedicated OWL screen or a POS extension layer.
 */
const applyPharmacyRuntimeHints = () => {
    const root = document.documentElement;
    const language = root.getAttribute("lang") || "";
    if (language.toLowerCase().startsWith("ar")) {
        root.setAttribute("dir", "rtl");
        root.classList.add("o_pharmacy_pos_rtl");
    }
};

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyPharmacyRuntimeHints);
} else {
    applyPharmacyRuntimeHints();
}
