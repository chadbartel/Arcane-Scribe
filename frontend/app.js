document.addEventListener("DOMContentLoaded", () => {
    // --- DOM ELEMENTS ---
    const loginForm = document.getElementById("login-form");
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    const loggingInView = document.getElementById("logging-in-view");
    const loginError = document.getElementById("login-error");
    
    const queryButton = document.getElementById("query-button");
    const queryInput = document.getElementById("query-input");
    const responseArea = document.getElementById("response-area");
    
    const srdDropdownButton = document.getElementById("srd-dropdown-button");
    const srdDropdownMenu = document.getElementById("srd-dropdown-menu");

    const invokeLlmSwitch = document.getElementById("invoke-llm-switch");
    const genConfigOptions = document.getElementById("generation-config-options");
    const temperatureSlider = document.getElementById("temperature-slider");
    const temperatureValue = document.getElementById("temperature-value");
    const topPSlider = document.getElementById("top-p-slider");
    const topPValue = document.getElementById("top-p-value");
    const maxTokensInput = document.getElementById("max-tokens-input");
    const stopSequencesInput = document.getElementById("stop-sequences-input");

    // --- API Configuration ---
    const apiSuffix = "/api/v1";
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.hostname === "arcane-scribe-dev.thatsmidnight.com";
    const DEV_API_URL = "https://arcane-scribe-dev.thatsmidnight.com";
    const API_BASE_URL = isLocal ? `${DEV_API_URL}${apiSuffix}` : apiSuffix;

    // --- STATE MANAGEMENT ---
    const VIEWS = ["login-view", "logging-in-view", "app-view"];

    /**
     * Hides all views and shows only the one specified by ID.
     * @param {string} viewId The ID of the view to show.
     */
    function showView(viewId) {
        VIEWS.forEach(id => {
            const view = document.getElementById(id);
            if (id === viewId) {
                view.classList.remove("d-none");
            } else {
                view.classList.add("d-none");
            }
        });
    }

    // --- EVENT LISTENERS ---
    // Add event listeners for login and query actions
    loginForm.addEventListener("submit", handleLogin);
    queryButton.addEventListener("click", handleQuery);

    // Add event listeners for the model controls
    invokeLlmSwitch.addEventListener("change", () => {
        // Disable generation config options if the LLM is not invoked
        genConfigOptions.style.opacity = invokeLlmSwitch.checked ? "1" : "0.5";
        genConfigOptions.querySelectorAll("input").forEach(input => {
            input.disabled = !invokeLlmSwitch.checked;
        });
    });

    // Initialize temperature slider
    temperatureSlider.addEventListener("input", () => {
        temperatureValue.textContent = temperatureSlider.value;
    });

    // Initialize top-p slider
    topPSlider.addEventListener("input", () => {
        topPValue.textContent = topPSlider.value;
    });

    // --- FUNCTIONS ---
    // Function to handle login
    async function handleLogin(e) {
        e.preventDefault();
        loginError.textContent = "";
        loginView.classList.add("d-none");
        loggingInView.classList.remove("d-none");

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Login failed");

            localStorage.setItem("idToken", data.IdToken);
            await populateSrdDropdown();

            loggingInView.classList.add("d-none");
            appView.classList.remove("d-none");
        } catch (error) {
            console.error("Login Error:", error);
            loginError.textContent = `Error: ${error.message}`;
            loggingInView.classList.add("d-none");
            loginView.classList.remove("d-none");
        }
    }

    // Function to make authenticated requests
    async function populateSrdDropdown() {
        try {
            const srd_ids = await makeAuthenticatedRequest("/srd", "GET");
            srdDropdownMenu.innerHTML = ""; 

            if (srd_ids && srd_ids.length > 0) {
                srd_ids.forEach(srd_id => {
                    const listItem = document.createElement("li");
                    const link = document.createElement("a");
                    link.className = "dropdown-item";
                    link.href = "#";
                    link.textContent = srd_id;
                    link.addEventListener("click", (e) => {
                        e.preventDefault();
                        srdDropdownButton.textContent = srd_id;
                    });
                    listItem.appendChild(link);
                    srdDropdownMenu.appendChild(listItem);
                });
            } else {
                 srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">No SRDs found.</span></li>`;
            }
        } catch (error) {
            console.error("Failed to populate SRD dropdown:", error);
            srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text text-danger">Error loading SRDs.</span></li>`;
        }
    }
    
    // Helper function to build the query payload
    function buildQueryPayload() {
        const srdId = srdDropdownButton.textContent.trim();
        const invokeGenerativeLlm = invokeLlmSwitch.checked;

        const payload = {
            query_text: queryInput.value,
            srd_id: srdId,
            invoke_generative_llm: invokeGenerativeLlm,
            generation_config: {}
        };
        
        // Only add generation config if the LLM is being invoked
        if (invokeGenerativeLlm) {
            // Use API's expected camelCase names
            const temp = parseFloat(temperatureSlider.value);
            if (!isNaN(temp)) payload.generation_config.temperature = temp;
            
            const topP = parseFloat(topPSlider.value);
            if (!isNaN(topP)) payload.generation_config.topP = topP;

            const maxTokenCount = parseInt(maxTokensInput.value, 10);
            if (!isNaN(maxTokenCount)) payload.generation_config.maxTokenCount = maxTokenCount;

            const stopSequences = stopSequencesInput.value
                .split(',')
                .map(s => s.trim())
                .filter(s => s); // Remove empty strings
            if (stopSequences.length > 0) payload.generation_config.stopSequences = stopSequences;
        }
        
        return payload;
    }

    // Function to handle the query button click
    async function handleQuery() {
        const query = queryInput.value;
        const srdId = srdDropdownButton.textContent.trim();

        if (!query) {
            alert("Please enter a query.");
            return;
        }
        if (!srdId || srdId === "Select an SRD") {
            alert("Please select an SRD from the dropdown.");
            return;
        }

        responseArea.textContent = "Getting answer...";
        
        const payload = buildQueryPayload();
        
        const response = await makeAuthenticatedRequest("/query", "POST", payload);

        responseArea.textContent = JSON.stringify(response, null, 2);
    }

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

    // --- NEW: FUNCTION TO POPULATE DROPDOWN ---
    async function populateSrdDropdown() {
        try {
            const srd_ids = await makeAuthenticatedRequest("/srd", "GET");
            
            srdDropdownMenu.innerHTML = ""; // Clear existing static items

            if (srd_ids && srd_ids.length > 0) {
                srd_ids.forEach(srd_id => {
                    const listItem = document.createElement("li");
                    const link = document.createElement("a");
                    link.className = "dropdown-item";
                    link.href = "#";
                    link.textContent = srd_id;
                    
                    link.addEventListener("click", (e) => {
                        e.preventDefault();
                        // Update button text to show selection
                        srdDropdownButton.textContent = srd_id;
                    });
                    
                    listItem.appendChild(link);
                    srdDropdownMenu.appendChild(listItem);
                });
            } else {
                 const listItem = document.createElement("li");
                 listItem.innerHTML = `<span class="dropdown-item-text">No SRDs found.</span>`;
                 srdDropdownMenu.appendChild(listItem);
            }
        } catch (error) {
            console.error("Failed to populate SRD dropdown:", error);
            const listItem = document.createElement("li");
            listItem.innerHTML = `<span class="dropdown-item-text text-danger">Error loading SRDs.</span>`;
            srdDropdownMenu.appendChild(listItem);
        }
    }

    // --- RAG QUERY LOGIC ---
    // Ensure the query button is only enabled when logged in
    queryButton.addEventListener("click", async () => {
        const query = queryInput.value;
        const srdId = srdDropdownButton.textContent.trim(); // Get SRD from button text

        // Validate input
        if (!query) {
            alert("Please enter a query.");
            return;
        }
        if (!srdId || srdId === "Select an SRD") {
            alert("Please select an SRD from the dropdown.");
            return;
        }

        // Clear previous response
        responseArea.textContent = "Getting answer...";

        // Make the authenticated request to the RAG API
        const response = await makeAuthenticatedRequest("/query", "POST", {
            query_text: query,
            srd_id: srdId,
            invoke_generative_llm: true,
            generation_config: {}
        });

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
            throw error;
        }
    }
});