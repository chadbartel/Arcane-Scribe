document.addEventListener("DOMContentLoaded", () => {
    // --- DOM ELEMENTS ---
    const loginForm = document.getElementById("login-form");
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    const loggingInView = document.getElementById("logging-in-view");
    const loginError = document.getElementById("login-error");

    const queryButton = document.getElementById("query-button");
    const queryInput = document.getElementById("query-input");

    const answerText = document.getElementById("answer-text");
    const sourcesContainer = document.getElementById("sources-container");

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

    /*
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
            const response = await fetch(`${API_BASE_URL}/login`, {
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
        console.log("1. Starting to populate dropdown. Disabling button.");
        srdDropdownButton.disabled = true;
        srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">Loading SRDs...</span></li>`;

        try {
            console.log("2. Calling makeAuthenticatedRequest for /srd...");
            const srd_ids = await makeAuthenticatedRequest("/srd", "GET");
            console.log("3. Received API response:", srd_ids);

            // Defensive check: ensure we have an array
            if (!Array.isArray(srd_ids)) {
                throw new TypeError("API response for SRD list is not an array.");
            }
            
            console.log("4. Clearing dropdown menu HTML.");
            srdDropdownMenu.innerHTML = ""; 

            if (srd_ids.length > 0) {
                console.log("5. SRD list has items. Starting forEach loop.");
                srd_ids.forEach((srd_id, index) => {
                    console.log(`6. Creating item for: ${srd_id} (index: ${index})`);
                    const listItem = document.createElement("li");
                    const link = document.createElement("a");
                    link.className = "dropdown-item";
                    link.href = "#";
                    link.textContent = srd_id;
                    
                    link.addEventListener("click", (e) => {
                        e.preventDefault();
                        srdDropdownButton.textContent = srd_id;
                        srdDropdownButton.dataset.selectedSrd = srd_id;
                    });
                    
                    listItem.appendChild(link);
                    srdDropdownMenu.appendChild(listItem);
                });
                console.log("7. Finished forEach loop.");
            } else {
                 console.log("5b. SRD list is empty.");
                 srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">No SRDs found.</span></li>`;
            }
        } catch (error) {
            console.error("8. [CATCH BLOCK] Failed to populate SRD dropdown:", error);
            srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text text-danger">Error loading SRDs.</span></li>`;
            throw error; 
        } finally {
            console.log("9. [FINALLY BLOCK] Re-enabling dropdown button.");
            // Re-enable the dropdown button whether the call succeeded or failed
            srdDropdownButton.disabled = false;
        }
    }

    // Helper function to build the query payload
    function buildQueryPayload() {
        // Use the data attribute for a more reliable way to get the selected value
        const srdId = srdDropdownButton.dataset.selectedSrd;
        const invokeGenerativeLlm = invokeLlmSwitch.checked;

        // Construct the payload object
        const payload = {
            query_text: queryInput.value,
            srd_id: srdId,
            invoke_generative_llm: invokeGenerativeLlm,
            generation_config: {}
        };

        // If the LLM is invoked, add generation config parameters
        if (invokeGenerativeLlm) {
            const temp = parseFloat(temperatureSlider.value);
            if (!isNaN(temp)) payload.generation_config.temperature = temp;

            const topP = parseFloat(topPSlider.value);
            if (!isNaN(topP)) payload.generation_config.topP = topP;

            const maxTokenCount = parseInt(maxTokensInput.value, 10);
            if (!isNaN(maxTokenCount) && maxTokenCount > 0) payload.generation_config.maxTokenCount = maxTokenCount;

            const stopSequences = stopSequencesInput.value.split(',').map(s => s.trim()).filter(s => s);
            if (stopSequences.length > 0) payload.generation_config.stopSequences = stopSequences;
        }

        return payload;
    }

    // Function to handle the query button click
    async function handleQuery() {
        const query = queryInput.value;
        const srdId = srdDropdownButton.dataset.selectedSrd;

        // Validate input
        if (!query || !srdId || srdId === "Select an SRD") {
            alert("Please select an SRD and enter a query.");
            return;
        }

        // Clear previous results and show loading state
        answerText.textContent = "Getting answer...";
        sourcesContainer.innerHTML = ""; // Clear old sources
        queryButton.disabled = true;

        // Build the query payload
        const payload = buildQueryPayload();

        // Get the query response
        try {
            const responseData = await makeAuthenticatedRequest("/query", "POST", payload);
            displayRagResponse(responseData); // Call the new display function
        } catch (error) {
            answerText.textContent = `Error during query: ${error.message}`;
        } finally {
            queryButton.disabled = false; // Re-enable button
        }
    }

    // Function to parse and display the RAG response
    function displayRagResponse(data) {
        // Clear loading message
        answerText.textContent = "";

        // Check if the response contains an answer or an error
        if (data && data.answer) {
            answerText.textContent = data.answer;
        } else if (data && data.error) {
            answerText.textContent = `An error occurred: ${data.error}`;
        } else {
            answerText.textContent = "Received an unexpected response from the API.";
        }

        // Clear and populate the sources container
        sourcesContainer.innerHTML = "";
        // Check for 'source_documents_content' and ensure it's an array
        if (data && data.source_documents_content && Array.isArray(data.source_documents_content)) {
            const uniqueSources = new Map();

            data.source_documents_content.forEach(doc => {
                // Access 'source' and 'page' directly from the 'doc' object,
                // not from a nested 'metadata' object.
                const sourceName = doc.source || "Unknown Document";
                const pageNum = doc.page;

                // We check if page is not undefined because page 0 is valid.
                if (sourceName && typeof pageNum !== 'undefined') {
                    const uniqueKey = `${sourceName}-page-${pageNum}`;
                    if (!uniqueSources.has(uniqueKey)) {
                        uniqueSources.set(uniqueKey, { sourceName, pageNum });
                    }
                }
            });

            if (uniqueSources.size > 0) {
                const sourceList = document.createElement("div");
                // Using 'd-flex flex-wrap' to allow badges to wrap to the next line
                sourceList.className = "d-flex flex-wrap gap-2"; 

                uniqueSources.forEach(sourceInfo => {
                    const badge = document.createElement("span");
                    // Using Bootstrap's badge component for a cleaner look
                    badge.className = "badge text-bg-secondary"; 
                    badge.textContent = `${sourceInfo.sourceName} (p. ${sourceInfo.pageNum + 1})`; // Add 1 to page for human-readable format

                    sourceList.appendChild(badge);
                });

                sourcesContainer.appendChild(sourceList);
            }
        }
    }

    // Function to make authenticated requests to the API
    async function makeAuthenticatedRequest(endpoint, method, body = null) {
        // Retrieve the ID token from local storage
        const idToken = localStorage.getItem("idToken");

        // Check if the user is authenticated
        if (!idToken) {
            const error = new Error("Authentication error. Please log in again.");
            console.error(error);
            showView("login-view"); // Force user back to login
            throw error;
        }

        // Prepare the request headers and options
        const headers = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${idToken}`
        };

        // Set the method and headers for the fetch request
        const config = { method, headers };

        // Stringify the body if it exists
        if (body) {
            config.body = JSON.stringify(body);
        }

        try {
            // Make the fetch request
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
            // Check if the response is ok (status in the range 200-299)
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const contentType = response.headers.get("content-type");
            // Check if the response is JSON or text
            if (contentType && contentType.includes("application/json")) {
                return response.json();
            }
            return response.text();
        } catch (error) {
            // Log the error and rethrow it for handling in the calling function
            console.error(`Authenticated request to ${endpoint} failed:`, error);
            throw error;
        }
    }

    // Initial view state
    showView("login-view");
});