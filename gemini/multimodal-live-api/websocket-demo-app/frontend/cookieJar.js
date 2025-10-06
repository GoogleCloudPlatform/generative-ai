class CookieJar {
    /**
     * @class CookieJar
     * @classdesc A utility class for managing cookies associated with HTML input elements.
     */

    /**
     * @static
     * @method init
     * @memberof CookieJar
     * @description Initializes the CookieJar for a given element. Loads saved value from cookie and sets up auto-saving on value change.
     * @param {string} elementId - The ID of the HTML input element.
     */
    static init(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`❌ Element with ID '${elementId}' not found.`);
            return;
        }

        const cookieName = `CookieJar_${elementId}`;

        // Load existing value from cookie
        const savedValue = CookieJar.getCookie(cookieName);
        if (savedValue) {
            console.log(`🍪 Found cookie for ${elementId}. Loading value: ${savedValue}`);
            element.value = savedValue;
        }

        // Save on value change
        element.addEventListener('input', () => {
            console.log(`🍪 Saving value for ${elementId} to cookie...`);
            CookieJar.setCookie(cookieName, element.value);
        });
    }

    /**
     * @static
     * @method setCookie
     * @memberof CookieJar
     * @description Sets a cookie with the given name, value, and optional expiration days.
     * @param {string} name - The name of the cookie.
     * @param {string} value - The value to store in the cookie.
     * @param {number} [days=365] - The number of days until the cookie expires. Defaults to 365.
     */
    static setCookie(name, value, days = 365) {
        const expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/`;
        console.log(`🍪 Cookie '${name}' set successfully!`);
    }

    /**
     * @static
     * @method getCookie
     * @memberof CookieJar
     * @description Retrieves the value of a cookie with the given name.
     * @param {string} name - The name of the cookie to retrieve.
     * @returns {string|null} The value of the cookie if found, otherwise null.
     */
    static getCookie(name) {
        const cookieValue = document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`);
        return cookieValue ? decodeURIComponent(cookieValue.pop()) : null;
    }
}