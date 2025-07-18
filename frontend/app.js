document.addEventListener("DOMContentLoaded", () => {
    // --- DOM ELEMENTS ---
    const loginForm = document.getElementById("login-form");
    const newPasswordForm = document.getElementById("new-password-form");
    const loginError = document.getElementById("login-error");
    const newPasswordError = document.getElementById("new-password-error");

    const queryButton = document.getElementById("query-button");
    const queryInput = document.getElementById("query-input");
    const answerText = document.getElementById("answer-text");
    const sourcesContainer = document.getElementById("sources-container");
    const srdDropdownButton = document.getElementById("srd-dropdown-button");
    const srdDropdownMenu = document.getElementById("srd-dropdown-menu");

    // Model configuration elements
    const numDocsInput = document.getElementById("num-docs-input");
    const invokeLlmSwitch = document.getElementById("invoke-llm-switch");
    const temperatureSlider = document.getElementById("temperature-slider");
    const temperatureValue = document.getElementById("temperature-value");
    const topPSlider = document.getElementById("top-p-slider");
    const topPValue = document.getElementById("top-p-value");
    const maxTokensInput = document.getElementById("max-tokens-input");
    const stopSequencesInput = document.getElementById("stop-sequences-input");

    // Nav elements
    const navbar = document.getElementById("navbarNav");
    const adminNavItem = document.getElementById("admin-nav-item");
    const welcomeUser = document.getElementById("welcome-user");
    const logoutButton = document.getElementById("logout-button");

    // Upload form elements
    const uploadForm = document.getElementById("upload-form");
    const srdIdInput = document.getElementById("srd-id-input");
    const srdIdList = document.getElementById("srd-id-list");
    const fileInput = document.getElementById("file-input");
    const uploadButton = document.getElementById("upload-button");
    const uploadButtonSpinner = document.getElementById("upload-button-spinner");
    const uploadButtonText = document.getElementById("upload-button-text");
    const uploadStatus = document.getElementById("upload-status");

    // Document list elements
    const refreshDocsButton = document.getElementById("refresh-docs-button");
    const documentsTable = document.getElementById("documents-table");
    const documentsTableBody = document.getElementById("documents-table-body");
    const documentsListStatus = document.getElementById("documents-list-status");

    // Deletion section elements
    const deleteDocumentsTableBody = document.getElementById(
        "delete-documents-table-body"
    );
    const selectAllCheckbox = document.getElementById("select-all-checkbox");
    const deleteSelectedButton = document.getElementById(
        "delete-selected-button"
    );
    const deleteButtonSpinner = document.getElementById("delete-button-spinner");
    const deleteButtonText = document.getElementById("delete-button-text");
    const deleteStatus = document.getElementById("delete-status");

    // Admin Panel elements
    const createUserForm = document.getElementById("create-user-form");
    const newUsernameInput = document.getElementById("new-username-input");
    const newEmailInput = document.getElementById("new-email-input");
    const newPasswordInput = document.getElementById("new-password-input");
    const userGroupSelect = document.getElementById("user-group-select");
    const createUserButton = document.getElementById("create-user-button");
    const createUserSpinner = document.getElementById("create-user-spinner");
    const createUserStatus = document.getElementById("create-user-status");
    const refreshUsersButton = document.getElementById("refresh-users-button");
    const usersTable = document.getElementById("users-table");
    const usersTableBody = document.getElementById("users-table-body");
    const userListStatus = document.getElementById("user-list-status");

    // --- API Configuration ---
    const apiSuffix = "/api/v1";
    const isLocal =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname === "arcane-scribe-dev.chadbartel.com";
    const DEV_API_URL = "https://arcane-scribe-dev.chadbartel.com";
    const PROD_API_URL = "https://arcane-scribe.chadbartel.com";
    const API_BASE_URL = isLocal
        ? `${DEV_API_URL}${apiSuffix}`
        : `${PROD_API_URL}${apiSuffix}`;
    console.log("Using API base URL:", API_BASE_URL);

    // --- STATE & VIEW MANAGEMENT ---
    const ALL_SCREENS = [
        "login-view",
        "loading-view",
        "new-password-view",
        "app-view",
    ];
    const CONTENT_VIEWS = ["query-view", "srd-management-view", "admin-view"];
    let allSrdIds = [];
    let loginSession = null;
    let challengeUsername = null;

    /*
     * Shows a specific main content view by ID and hides all others.
     * @param {string} viewId - The ID of the view to show.
     * This function is used for content views like query, SRD management, admin, etc.
     */
    function showScreen(screenIdToShow) {
        ALL_SCREENS.forEach((id) =>
            document
                .getElementById(id)
                ?.classList.toggle("d-none", id !== screenIdToShow)
        );
    }

    /*
     * Shows a specific main content view by ID and hides all others.
     * @param {string} viewId - The ID of the view to show.
     * This function is used for content views like query, SRD management, admin, etc.
     */
    function showContentView(viewId) {
        CONTENT_VIEWS.forEach((id) =>
            document.getElementById(id)?.classList.add("d-none")
        );
        document.getElementById(viewId)?.classList.remove("d-none");
        navbar
            .querySelectorAll(".nav-link")
            .forEach((link) =>
                link.classList.toggle("active", link.dataset.view === viewId)
            );
    }

    // --- HELPERS ---
    /*
     * Parses a JWT token and returns its payload as a JSON object.
     * @param {string} token - The JWT token to parse.
     * @returns {object|null} The parsed payload or null if parsing fails.
     * This function decodes the base64-encoded payload of the JWT and returns it as an object.
     */
    function parseJwt(token) {
        try {
            return JSON.parse(atob(token.split(".")[1]));
        } catch (e) {
            return null;
        }
    }

    /*
     * Parses FastAPI/Pydantic validation errors into a readable string.
     * @param {object} errorData - The JSON error object from the API.
     * @returns {string} A formatted, human-readable error message.
     */
    function parseApiError(errorData) {
        if (errorData && Array.isArray(errorData.detail)) {
            // This is a Pydantic validation error
            return errorData.detail
                .map((err) => {
                    // loc[1] is usually the field name, e.g., "new_password"
                    const field = err.loc && err.loc.length > 1 ? err.loc[1] : "Input";
                    return `${field}: ${err.msg}`;
                })
                .join("\n");
        }
        // This is a regular HTTPException error
        if (errorData && errorData.detail) {
            return errorData.detail;
        }
        // Fallback for unknown error formats
        return "An unknown error occurred.";
    }

    /**
     * Returns a Bootstrap badge class based on the document processing status.
     * @param {string} status - The processing status string.
     * @returns {string} The corresponding Bootstrap badge class.
     */
    function getStatusBadgeClass(status) {
        switch (status.toLowerCase()) {
            case "completed":
                return "badge text-bg-success";
            case "processing":
                return "badge text-bg-info";
            case "pending":
                return "badge text-bg-warning";
            case "failed":
                return "badge text-bg-danger";
            default:
                return "badge text-bg-secondary";
        }
    }

    // --- EVENT LISTENERS ---
    // Add event listeners for login and query actions
    loginForm.addEventListener("submit", handleLogin);
    newPasswordForm.addEventListener("submit", handleNewPasswordSubmit);
    logoutButton.addEventListener("click", handleLogout);
    queryButton.addEventListener("click", handleQuery);

    // Add event listeners for SRD input elements
    uploadForm.addEventListener("submit", handleUpload);

    // Add listeners for the SRD table
    refreshDocsButton.addEventListener("click", () =>
        handleRefresh(srdIdInput.value.trim())
    );

    // Add listener to filter the dropdown as the user types
    srdIdInput.addEventListener("input", () =>
        filterSrdInputList(srdIdInput.value)
    );

    // Add listeners for the new deletion controls
    selectAllCheckbox.addEventListener("change", handleSelectAll);
    deleteSelectedButton.addEventListener("click", handleDeleteSelected);

    // Add listeners for the admin panel
    createUserForm.addEventListener("submit", handleCreateUser);
    refreshUsersButton.addEventListener("click", populateUsersTable);

    // Add navigation listener to populate dropdown when view is shown
    navbar.addEventListener("click", (e) => {
        if (e.target.matches(".nav-link") && e.target.dataset.view) {
            e.preventDefault();
            const viewId = e.target.dataset.view;
            showContentView(viewId);
            if (viewId === "srd-management-view") {
                // If we are showing the SRD management view, populate the list
                populateSrdInputList();
            } else if (viewId === "query-view") {
                // Populate the SRD dropdown when entering the query view
                populateSrdDropdown();
            } else if (viewId === "admin-view") {
                // Populate the users table when entering the admin view
                populateUsersTable();
            }
        }
    });

    // Add event listeners for the model controls
    numDocsInput.addEventListener("input", () => {
        numDocsInput.value = Math.max(1, Math.min(50, numDocsInput.value));
    });
    invokeLlmSwitch.addEventListener("change", () => {
        const isDisabled = !invokeLlmSwitch.checked;
        genConfigOptions.style.opacity = isDisabled ? "0.5" : "1";
        genConfigOptions
            .querySelectorAll("input")
            .forEach((input) => (input.disabled = isDisabled));
    });
    temperatureSlider.addEventListener("input", () => {
        temperatureValue.textContent = temperatureSlider.value;
    });
    topPSlider.addEventListener("input", () => {
        topPValue.textContent = topPSlider.value;
    });
    maxTokensInput.addEventListener("input", () => {
        maxTokensInput.value = Math.max(1, Math.min(200000, maxTokensInput.value));
    });
    stopSequencesInput.addEventListener("input", () => {
        stopSequencesInput.value = stopSequencesInput.value
            .replace(/[^a-zA-Z0-9, ]/g, "")
            .slice(0, 100);
    });

    // --- MAIN LOGIC FUNCTIONS ---
    async function setupAppForUser(idToken, refreshToken) {
        localStorage.setItem("idToken", idToken);
        if (refreshToken) localStorage.setItem("refreshToken", refreshToken);

        const decodedToken = parseJwt(idToken);
        if (decodedToken) {
            welcomeUser.textContent = `Welcome, ${decodedToken["cognito:username"]}`;
            const groups = decodedToken["cognito:groups"] || [];
            adminNavItem.classList.toggle("d-none", !groups.includes("admins-dev"));
        }

        // Make the main application container visible.
        showScreen("app-view");
        showContentView("query-view"); // Default to the query view

        // Populate the data within the now-visible container.
        try {
            await populateSrdDropdown();
        } catch (error) {
            // Even if this fails, the user is still logged in and can see the app.
            console.error("Initial data load failed:", error);
        }
    }

    // Function to handle login
    async function handleLogin(e) {
        e.preventDefault();
        loginError.textContent = "";
        showScreen("loading-view");

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        try {
            // Make the API call to log in
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            // Check if the response is OK and parse the JSON
            const data = await response.json();
            if (!response.ok) {
                // Pass the raw data to the error parser
                throw new Error(parseApiError(data));
            }

            // Check the response for either tokens or a challenge
            if (data.IdToken) {
                await completeLogin(data.IdToken, data.RefreshToken);
            } else if (data.ChallengeName === "NEW_PASSWORD_REQUIRED") {
                // CHALLENGE: If the challenge is NEW_PASSWORD_REQUIRED, show the new password view
                loginSession = data.Session;
                challengeUsername = data.username;
                showScreen("new-password-view");
            } else {
                // UNEXPECTED: The response was OK but didn't contain tokens or a challenge.
                throw new Error("An unexpected error occurred during login.");
            }
        } catch (error) {
            // Handle errors gracefully
            console.error("Login Error:", error);
            loginError.textContent = `Error: ${error.message}`;
            showScreen("login-view"); // On any failure, return to login view
        }
    }

    // Function to handle new password submission
    async function handleNewPasswordSubmit(e) {
        e.preventDefault();
        newPasswordError.textContent = "";

        const newPassword = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-password").value;

        // Validate new password and confirmation
        if (newPassword !== confirmPassword) {
            newPasswordError.textContent = "Passwords do not match.";
            return;
        }

        // Show spinner
        showScreen("loading-view");

        try {
            // Make the API call to respond to the new password challenge
            const response = await fetch(
                `${API_BASE_URL}/auth/respond-to-challenge`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        username: challengeUsername,
                        session: loginSession,
                        new_password: newPassword,
                    }),
                }
            );

            // Check if the response is OK and parse the JSON
            const data = await response.json();
            if (!response.ok) {
                // Pass the raw data to the error parser
                throw new Error(parseApiError(data));
            }

            // If successful, complete the login with the returned tokens
            await setupAppForUser(data.IdToken, data.RefreshToken);
        } catch (error) {
            // Handle errors gracefully
            console.error("New Password Error:", error);
            newPasswordError.textContent = `Error: ${error.message}`;
            showScreen("new-password-view"); // Show password form again on error
        }
    }

    /*
     * Handles user logout by clearing local storage and updating the UI.
     * This function hides the admin tab, clears the SRD dropdown,
     * and shows the login view again.
     */
    function handleLogout() {
        // 1. Clear all session information from storage
        localStorage.clear();

        // 2. Show the login screen and hide all others
        showScreen("login-view");

        // 3. Hide admin-specific UI elements
        adminNavItem.classList.add("d-none");
        welcomeUser.textContent = "";
    }

    /*
     * Completes the login process by storing tokens and updating the UI.
     * @param {string} idToken - The ID token from Cognito.
     * @param {string} refreshToken - The optional refresh token from Cognito.
     * This function updates the welcome message, checks for admin group membership,
     * populates the SRD dropdown, and shows the main app view.
     */
    async function completeLogin(idToken, refreshToken) {
        // Store tokens in local storage
        localStorage.setItem("idToken", idToken);
        if (refreshToken) localStorage.setItem("refreshToken", refreshToken);

        // Update the UI to show the welcome message
        const decodedToken = parseJwt(idToken);
        if (decodedToken) {
            welcomeUser.textContent = `Welcome, ${decodedToken["cognito:username"]}`;
            // Check for admin group membership
            const groups = decodedToken["cognito:groups"] || [];
            if (groups.includes("admins")) {
                // Match your group name in Cognito
                adminNavItem.classList.remove("d-none");
            }
        }

        // Populate the SRD dropdown
        await populateSrdDropdown();
        showScreen("app-view");
        showContentView("query-view"); // Show the query view by default
    }

    // Function to make authenticated requests
    async function populateSrdDropdown() {
        console.log("1. Starting to populate dropdown. Disabling button.");
        srdDropdownButton.disabled = true;
        srdDropdownButton.textContent = "Loading...";
        srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">Loading SRDs...</span></li>`;

        try {
            console.log("2. Calling makeAuthenticatedRequest for /srd...");
            const srd_ids = await makeAuthenticatedRequest("/srd", "GET");
            console.log("3. Received API response:", srd_ids);

            console.log("4. Clearing dropdown menu HTML.");
            srdDropdownMenu.innerHTML = "";

            // Check if the response is an array and has items
            if (srd_ids && Array.isArray(srd_ids) && srd_ids.length > 0) {
                // Set the default selected SRD to the first one in the list
                srdDropdownButton.textContent = srd_ids[0];
                srdDropdownButton.dataset.selectedSrd = srd_ids[0];

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
                // This case handles a 200 OK with an empty list
                console.log("5b. SRD list is empty.");
                srdDropdownButton.textContent = "No SRDs Found";
                srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">No SRDs found.</span></li>`;
            }
        } catch (error) {
            // Check if the error is the specific "404 Not Found" case for a new user
            console.error("8. [CATCH BLOCK] Failed to populate SRD dropdown:", error);
            if (error.status === 404) {
                console.log("User has no SRDs yet. This is expected.");
                srdDropdownButton.textContent = "No SRDs Found";
                srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text">No SRDs found. Upload a document to begin.</span></li>`;
                // IMPORTANT: We do *not* re-throw the error here, allowing the login to proceed.
            } else {
                // For any other error (like a 500), show an error and re-throw it to fail the login
                console.error("Failed to populate SRD dropdown:", error);
                srdDropdownMenu.innerHTML = `<li><span class="dropdown-item-text text-danger">Error loading SRDs.</span></li>`;
                throw error;
            }
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
            generation_config: {},
        };

        // Get the value from the new input field
        const numDocs = parseInt(numDocsInput.value, 10);
        if (!isNaN(numDocs) && numDocs > 0 && numDocs <= 50) {
            payload.number_of_documents = numDocs;
        } else {
            // Default to 10 if the input is invalid or not provided
            payload.number_of_documents = 10;
        }

        // If the LLM is invoked, add generation config parameters
        if (invokeGenerativeLlm) {
            const temp = parseFloat(temperatureSlider.value);
            if (!isNaN(temp)) payload.generation_config.temperature = temp;

            const topP = parseFloat(topPSlider.value);
            if (!isNaN(topP)) payload.generation_config.topP = topP;

            const maxTokenCount = parseInt(maxTokensInput.value, 10);
            if (!isNaN(maxTokenCount) && maxTokenCount > 0 && maxTokenCount <= 200000) {
                payload.generation_config.maxTokenCount = maxTokenCount;
            } else {
                // Default to 1000 if the input is invalid or not provided
                payload.generation_config.maxTokenCount = 1000;
            }

            const stopSequences = stopSequencesInput.value
                .split(",")
                .map((s) => s.trim())
                .filter((s) => s);
            if (stopSequences.length > 0)
                payload.generation_config.stopSequences = stopSequences;
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
            const responseData = await makeAuthenticatedRequest(
                "/query",
                "POST",
                payload
            );
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
        if (
            data &&
            data.source_documents_content &&
            Array.isArray(data.source_documents_content)
        ) {
            const uniqueSources = new Map();

            data.source_documents_content.forEach((doc) => {
                // Access 'source' and 'page' directly from the 'doc' object,
                // not from a nested 'metadata' object.
                const encodedSourceName = doc.source || "Unknown Document";
                const pageNum = doc.page;

                // Decode the URI component to make it human-readable
                const sourceName = decodeURIComponent(
                    encodedSourceName.replace(/\+/g, "%20").split("/").pop()
                );

                // We check if page is not undefined because page 0 is valid.
                if (sourceName && typeof pageNum !== "undefined") {
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

                uniqueSources.forEach((sourceInfo) => {
                    const badge = document.createElement("span");
                    // Using Bootstrap's badge component for a cleaner look
                    badge.className = "badge text-bg-secondary";
                    badge.textContent = `${sourceInfo.sourceName} (p. ${sourceInfo.pageNum + 1
                        })`; // Add 1 to page for human-readable format

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

        // Check if the user is authenticated and has a valid ID token
        if (!idToken || idToken === "undefined") {
            const error = new Error("Authentication error. Please log in again.");
            showScreen("login-view");
            throw error;
        }

        // Prepare the request headers and options
        const headers = {
            "Content-Type": "application/json",
            Authorization: `Bearer ${idToken}`,
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
                const errorData = await response
                    .json()
                    .catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                // Create a custom error object that includes the status code
                const error = new Error(parseApiError(errorData));
                error.status = response.status;
                throw error;
            }
            const contentType = response.headers.get("content-type");
            // Check if the response is JSON or text
            if (contentType && contentType.includes("application/json")) {
                return response.json();
            }
            const text = await response.text();
            return text ? JSON.parse(text) : []; // Return empty array for empty response
        } catch (error) {
            // Log the error and rethrow it for handling in the calling function
            console.error(`Authenticated request to ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Handles the "Select All" checkbox functionality.
     */
    function handleSelectAll() {
        document
            .querySelectorAll(".document-checkbox")
            .forEach((cb) => (cb.checked = selectAllCheckbox.checked));
    }

    /**
     * Handles the deletion of selected documents.
     */
    async function handleDeleteSelected() {
        const srdId = srdIdInput.value.trim();
        const selectedCheckboxes = document.querySelectorAll(
            ".document-checkbox:checked"
        );

        if (!srdId || selectedCheckboxes.length === 0) {
            alert("Please select an SRD and at least one document to delete.");
            return;
        }

        if (
            !confirm(
                `Are you sure you want to delete ${selectedCheckboxes.length} document(s)? This cannot be undone.`
            )
        ) {
            return;
        }

        // Disable button and show spinner
        deleteSelectedButton.disabled = true;
        deleteButtonSpinner.classList.remove("d-none");
        deleteButtonText.textContent = "Deleting...";
        deleteStatus.innerHTML = "";

        const totalToDelete = selectedCheckboxes.length;
        let deletedCount = 0;
        let hasErrors = false;

        // Loop through and delete each selected document one-by-one
        for (const checkbox of selectedCheckboxes) {
            const documentId = checkbox.value;
            try {
                deleteStatus.innerHTML = `<div class="alert alert-info">Deleting document ${deletedCount + 1
                    } of ${totalToDelete}...</div>`;
                await makeAuthenticatedRequest(
                    `/srd/${srdId}/documents/${documentId}`,
                    "DELETE"
                );
                deletedCount++;
            } catch (error) {
                hasErrors = true;
                console.error(`Failed to delete document ${documentId}:`, error);
                deleteStatus.innerHTML = `<div class="alert alert-danger">Error deleting document ${documentId}: ${error.message}</div>`;
                // Stop on first error
                break;
            }
        }

        // Re-enable button and hide spinner
        deleteSelectedButton.disabled = false;
        deleteButtonSpinner.classList.add("d-none");
        deleteButtonText.textContent = "Delete Selected Documents";

        if (hasErrors) {
            deleteStatus.innerHTML = `<div class="alert alert-warning">Finished with errors. ${deletedCount} of ${totalToDelete} documents were deleted. Please refresh.</div>`;
        } else {
            deleteStatus.innerHTML = `<div class="alert alert-success">Successfully deleted ${deletedCount} document(s). Refreshing list...</div>`;
        }

        // Refresh the document lists after deletion
        await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait for user to read message
        handleRefresh(srdId);
        deleteStatus.innerHTML = "";
    }

    /**
     * Fetches the list of SRD IDs and populates the editable dropdown.
     * This function retrieves the SRD IDs from the API and populates the dropdown list.
     * If no SRD IDs are found, it displays a message indicating that no SRDs
     * are available.
     */
    async function populateSrdInputList() {
        srdIdList.innerHTML = `<li><span class="dropdown-item-text">Loading...</span></li>`;
        try {
            const srd_ids = await makeAuthenticatedRequest("/srd", "GET");
            allSrdIds = srd_ids || []; // Store for filtering

            srdIdList.innerHTML = ""; // Clear loading message

            if (allSrdIds.length > 0) {
                allSrdIds.forEach((id) => {
                    const listItem = document.createElement("li");
                    const link = document.createElement("a");
                    link.className = "dropdown-item";
                    link.href = "#";
                    link.textContent = id;
                    // Add click event to each item
                    link.addEventListener("click", (e) => {
                        e.preventDefault();
                        srdIdInput.value = id; // Set the input field's value
                        // Manually hide the dropdown after selection
                        bootstrap.Dropdown.getInstance(srdIdInput)?.hide();
                        handleRefresh(id);
                    });
                    listItem.appendChild(link);
                    srdIdList.appendChild(listItem);
                });
            } else {
                srdIdList.innerHTML = `<li><span class="dropdown-item-text">No existing SRDs found.</span></li>`;
            }
        } catch (error) {
            if (error.status !== 404) {
                // Ignore 404 for new users
                console.error("Failed to populate SRD input list:", error);
                srdIdList.innerHTML = `<li><span class="dropdown-item-text text-danger">Error loading SRD list.</span></li>`;
            } else {
                srdIdList.innerHTML = `<li><span class="dropdown-item-text">No existing SRDs found.</span></li>`;
            }
        }
    }

    /*
     * Handles the file upload process when the upload form is submitted.
     * This function retrieves the SRD ID and file from the form,
     * requests a pre-signed URL from the API,
     * and uploads the file directly to S3 using that URL.
     */
    async function handleUpload(e) {
        e.preventDefault();

        const srdId = srdIdInput.value.trim();
        const file = fileInput.files[0];

        if (!srdId || !file) {
            alert("Please provide an SRD ID and select a file.");
            return;
        }

        // Disable button and show spinner
        uploadButton.disabled = true;
        uploadButtonSpinner.classList.remove("d-none");
        uploadButtonText.textContent = "Uploading...";
        uploadStatus.innerHTML = `<div class="alert alert-info">Step 1 of 2: Requesting secure upload URL...</div>`;

        try {
            // --- Step 1: Get the Pre-signed URL from our API ---
            const presignedUrlResponse = await makeAuthenticatedRequest(
                `/srd/${srdId}/documents/upload-url`,
                "POST",
                {
                    file_name: file.name,
                    content_type: file.type,
                }
            );

            uploadStatus.innerHTML = `<div class="alert alert-info">Step 2 of 2: Uploading file to S3... This may take a moment.</div>`;

            // --- Step 2: Upload the file directly to S3 using the URL ---
            const s3Url = presignedUrlResponse.presigned_url;

            // Upload the file to S3 using the pre-signed URL
            const uploadResponse = await fetch(s3Url, {
                method: "PUT",
                headers: {
                    "Content-Type": file.type,
                },
                body: file,
            });

            // Check if the upload was successful
            if (!uploadResponse.ok) {
                const errorText = await uploadResponse.text();
                throw new Error(`S3 Upload Failed: ${errorText}`);
            }

            uploadStatus.innerHTML = `<div class="alert alert-success">Upload complete! Your document is now being processed.</div>`;
            fileInput.value = ""; // Clear the file input

            // Refresh the document list after a successful upload
            await new Promise((resolve) => setTimeout(resolve, 1500)); // Wait a moment for consistency
            await handleRefresh(srdId);
        } catch (error) {
            console.error("Upload failed:", error);
            uploadStatus.innerHTML = `<div class="alert alert-danger">Error during upload: ${error.message}</div>`;
        } finally {
            // Re-enable button and hide spinner
            uploadButton.disabled = false;
            uploadButtonSpinner.classList.add("d-none");
            uploadButtonText.textContent = "Upload Document";
        }
    }

    /**
     * Fetches and displays documents for the SRD ID in the input field.
     * This function retrieves documents from the API and displays them in a table.
     * If no SRD ID is provided, it shows a message prompting the user to enter one.
     * If documents are found, they are displayed in a table with their names and processing statuses.
     * If an error occurs, it displays an appropriate error message.
     */
    async function handleRefresh(srdId) {
        if (!srdId) {
            documentsListStatus.textContent = "Enter an SRD ID to see its documents.";
            documentsTable.classList.add("d-none");
            deleteDocumentsTableBody.innerHTML = "";
            return;
        }

        // Show loading state
        documentsListStatus.textContent = "Loading documents...";
        documentsTable.classList.add("d-none");
        documentsTableBody.innerHTML = "";
        deleteDocumentsTableBody.innerHTML = "";
        refreshDocsButton.disabled = true;

        try {
            const documents = await makeAuthenticatedRequest(
                `/srd/${srdId}/documents`,
                "GET"
            );

            // Clear status and tables before populating
            documentsListStatus.textContent = "";
            documentsTableBody.innerHTML = "";
            deleteDocumentsTableBody.innerHTML = "";

            if (documents && Array.isArray(documents) && documents.length > 0) {
                documentsTable.classList.remove("d-none"); // Show status table

                documents.forEach((doc) => {
                    // --- Populate the Status Table (existing logic) ---
                    const statusRow = documentsTableBody.insertRow();
                    statusRow.insertCell(0).textContent = doc.original_file_name;
                    const statusCell = statusRow.insertCell(1);
                    const statusBadge = document.createElement("span");
                    statusBadge.textContent = doc.processing_status;
                    statusBadge.className = getStatusBadgeClass(doc.processing_status);
                    statusCell.appendChild(statusBadge);

                    // --- Populate the Delete Table ---
                    const deleteRow = deleteDocumentsTableBody.insertRow();
                    const cellCheckbox = deleteRow.insertCell(0);
                    const cellName = deleteRow.insertCell(1);

                    // Create a checkbox for deletion
                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.className = "form-check-input document-checkbox";
                    checkbox.value = doc.document_id; // Store the ID to delete
                    cellCheckbox.appendChild(checkbox);

                    cellName.textContent = doc.original_file_name;
                });
            } else {
                documentsListStatus.textContent = `No documents found for SRD: ${srdId}`;
            }
        } catch (error) {
            if (error.status === 404) {
                documentsListStatus.textContent = `No documents found for SRD: ${srdId}`;
            } else {
                documentsListStatus.textContent = `Error loading documents: ${error.message}`;
            }
        } finally {
            refreshDocsButton.disabled = false;
        }
    }

    /**
     * Returns the appropriate Bootstrap badge class based on the processing status.
     * @param {string} status - The processing status of the document.
     * @returns {string} - The Bootstrap badge class for the status.
     * This function maps processing statuses to Bootstrap badge classes for consistent styling.
     * It supports "Processing", "Failed", "Completed", and "Pending" statuses.
     */
    function filterSrdInputList(filterText) {
        const items = srdIdList.querySelectorAll("li a");
        items.forEach((item) => {
            const text = item.textContent.toLowerCase();
            item.parentElement.style.display = text.includes(filterText.toLowerCase())
                ? ""
                : "none";
        });
    }

    /**
     * Handles the new user creation form submission.
     */
    async function handleCreateUser(e) {
        e.preventDefault();
        createUserStatus.innerHTML = "";
        createUserButton.disabled = true;
        createUserSpinner.classList.remove("d-none");

        // Construct the payload from the form inputs
        const payload = {
            username: newUsernameInput.value,
            email: newEmailInput.value,
            temporary_password: newPasswordInput.value,
            user_group: userGroupSelect.value,
        };

        try {
            // API returns a 201 with an empty body, so we don't need the result
            await makeAuthenticatedRequest("/auth/signup", "POST", payload);
            createUserStatus.innerHTML = `<div class="alert alert-success">User '${payload.username}' created successfully.</div>`;
            createUserForm.reset(); // Clear the form on success
            await populateUsersTable(); // Refresh the user list
        } catch (error) {
            createUserStatus.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        } finally {
            createUserButton.disabled = false;
            createUserSpinner.classList.add("d-none");
        }
    }

    /**
     * Fetches the list of all users and populates the admin table.
     */
    async function populateUsersTable() {
        userListStatus.textContent = "Loading users...";
        usersTable.classList.add("d-none");
        usersTableBody.innerHTML = "";
        refreshUsersButton.disabled = true;

        try {
            const users = await makeAuthenticatedRequest("/auth/users", "GET");

            if (users && users.length > 0) {
                userListStatus.textContent = "";
                usersTable.classList.remove("d-none");

                users.forEach((user) => {
                    // Create a new row for each user
                    const row = usersTableBody.insertRow();

                    // Username and Email Cells
                    row.insertCell(0).textContent = user.username;
                    row.insertCell(1).textContent = user.email;

                    // Groups Cell
                    const groupsCell = row.insertCell(2);
                    groupsCell.textContent = user.groups.join(", ") || "N/A";

                    // Actions Cell with Delete Button
                    const actionsCell = row.insertCell(3);
                    actionsCell.className = "text-end";
                    const deleteBtn = document.createElement("button");
                    deleteBtn.className = "btn btn-danger btn-sm";
                    deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
                    deleteBtn.title = `Delete user ${user.username}`;
                    deleteBtn.onclick = (event) =>
                        handleDeleteUser(user.username, event.currentTarget);
                    actionsCell.appendChild(deleteBtn);
                });
            } else {
                userListStatus.textContent = "No users found.";
            }
        } catch (error) {
            userListStatus.textContent = `Error loading users: ${error.message}`;
        } finally {
            refreshUsersButton.disabled = false;
        }
    }

    /**
     * Handles the deletion of a single user.
     */
    async function handleDeleteUser(username, buttonElement) {
        if (
            !confirm(
                `Are you sure you want to permanently delete the user '${username}'? This cannot be undone.`
            )
        ) {
            return;
        }

        buttonElement.disabled = true;
        buttonElement.innerHTML =
            '<span class="spinner-border spinner-border-sm"></span>';

        try {
            await makeAuthenticatedRequest(`/auth/delete-user/${username}`, "DELETE");
            // Find the table row and fade it out for a nice UX
            const row = buttonElement.closest("tr");
            row.style.transition = "opacity 0.5s ease";
            row.style.opacity = "0";
            setTimeout(() => row.remove(), 500); // Remove after fade out
        } catch (error) {
            alert(`Failed to delete user: ${error.message}`);
            buttonElement.disabled = false; // Re-enable button on failure
            buttonElement.innerHTML = '<i class="bi bi-trash"></i> Delete';
        }
    }

    // Initial Check on Page Load
    function initializeApp() {
        const token = localStorage.getItem("idToken");
        if (token) {
            showScreen("loading-view");
            setupAppForUser(token, localStorage.getItem("refreshToken")).catch(
                (err) => {
                    console.error("Failed to initialize app from stored token:", err);
                    handleLogout(); // If setup fails, clear session and show login
                }
            );
        } else {
            showScreen("login-view");
        }
    }

    // Start the application
    initializeApp();
});
