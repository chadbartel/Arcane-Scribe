document.addEventListener("DOMContentLoaded", () => {
    // --- DOM ELEMENTS ---
    const loginForm = document.getElementById("login-form");
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    const loggingInView = document.getElementById("logging-in-view");
    const loginError = document.getElementById("login-error");
    const apiSuffix = "/api/v1";

    // Check if the page is being served from localhost
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.hostname === "arcane-scribe-dev.thatsmidnight.com";

    // Local and prod API URLs
    const DEV_API_URL = "https://arcane-scribe-dev.thatsmidnight.com";
    const PROD_API_URL = "https://arcane-scribe.thatsmidnight.com";

    // Determine the API base URL based on the environment
    const API_BASE_URL = isLocal ? DEV_API_URL + apiSuffix : PROD_API_URL + apiSuffix;

    // --- LOGIN LOGIC ---
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginError.textContent = "";

        // Show loading view and hide login form
        loginView.classList.add("d-none");
        loggingInView.classList.remove("d-none");

        // Get username and password from form
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        try {
            // Make the login request to the API
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            // Parse the response
            const data = await response.json();

            // Check if the response is successful
            if (!response.ok) {
                throw new Error(data.detail || "Login failed");
            }

            // Store tokens securely. localStorage is simple for now.
            localStorage.setItem("idToken", data.IdToken);
            localStorage.setItem("accessToken", data.AccessToken);
            localStorage.setItem("refreshToken", data.RefreshToken);

            // Switch views - hide loading and show app
            loggingInView.classList.add("d-none");
            appView.classList.remove("d-none");

        } catch (error) {
            // Handle errors and display them
            console.error("Login Error:", error);
            loginError.textContent = `Error: ${error.message}`;
            
            // Hide loading view and show login form again on error
            loggingInView.classList.add("d-none");
            loginView.classList.remove("d-none");
        }
    });

    // --- RAG QUERY LOGIC ---
    const queryButton = document.getElementById("query-button");
    const queryInput = document.getElementById("query-input");
    const srdIdInput = document.getElementById("srd-id-input");
    const responseArea = document.getElementById("response-area");

    // Ensure the query button is only enabled when logged in
    queryButton.addEventListener("click", async () => {
        const query = queryInput.value;
        const srdId = srdIdInput.value;
        if (!query) return;
        if (!srdId) return;

        // Clear previous response
        responseArea.textContent = "Getting answer...";

        // This function would make the authenticated API call
        const response = await makeAuthenticatedRequest("/query", "POST", {
            query_text: query,
            srd_id: srdId
        });

        // Display the response in the response area
        responseArea.textContent = JSON.stringify(response, null, 2);
    });

    // --- AUTHENTICATED API REQUEST HELPER ---
    async function makeAuthenticatedRequest(endpoint, method, body = null) {
        // Get the ID Token from localStorage
        const idToken = localStorage.getItem("idToken");

        // Check if the ID Token exists
        if (!idToken) {
            // Handle not being logged in
            console.error("No ID Token found. Please log in.");
            // Here you would redirect to login or show the login form
            return;
        }

        // Prepare headers for the request
        const headers = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${idToken}`
        };

        // Prepare the request configuration
        const config = {
            method: method,
            headers: headers,
        };

        // If there's a body, stringify it
        if (body) {
            config.body = JSON.stringify(body);
        }

        try {
            // Make the authenticated request to the API
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

            // TODO: Add logic here to check for 401 Unauthorized and use the
            // RefreshToken to get a new IdToken.

            // If the response is not ok, throw an error
            if (!response.ok) {
                // Handle specific error responses
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            // Parse and return the JSON response
            return await response.json();
        } catch (error) {
            // Handle errors from the request
            console.error("Authenticated request failed:", error);
            responseArea.textContent = `API Error: ${error.message}`;
        }
    }
});