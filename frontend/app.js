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
    const topPSlider = document.getElementById("top-p-slider");
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

    // --- API Configuration ---
    const apiSuffix = "/api/v1";
    const isLocal =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname === "arcane-scribe-dev.thatsmidnight.com";
    const DEV_API_URL = "https://arcane-scribe-dev.thatsmidnight.com";
    const API_BASE_URL = isLocal ? `${DEV_API_URL}${apiSuffix}` : apiSuffix;

    // --- STATE MANAGEMENT ---
    const APP_VIEWS = ["query-view", "srd-management-view", "admin-view"];

    /*
     * Shows a specific view by ID and hides all others.
     * @param {string} viewId - The ID of the view to show.
     * This function updates the visibility of main content views and highlights the active nav link.
     */
    function showMainView(viewId) {
        // Hide all main content views
        APP_VIEWS.forEach((id) => {
            document.getElementById(id)?.classList.add("d-none");
        });
        // Show the target view
        document.getElementById(viewId)?.classList.remove("d-none");

        // Update active class on nav links
        navbar.querySelectorAll(".nav-link").forEach((link) => {
            if (link.dataset.view === viewId) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });
    }

    /*
     * Shows a specific screen by ID and hides all others.
     * @param {string} screenId - The ID of the screen to show.
     * This function is used for top-level screens like login, app, loading, etc.
     */
    function showScreen(screenId) {
        // Screens are the top-level containers: login, app, loading, etc.
        const SCREENS = [
            "login-view",
            "logging-in-view",
            "new-password-view",
            "app-view",
        ];
        SCREENS.forEach((id) => {
            document.getElementById(id)?.classList.toggle("d-none", id !== screenId);
        });
    }

    // --- EVENT LISTENERS ---
    // Add event listeners for login and query actions
    loginForm.addEventListener("submit", handleLogin);
    queryButton.addEventListener("click", handleQuery);
    newPasswordForm.addEventListener("submit", handleNewPasswordSubmit);

    // Add event listeners for the model controls
    invokeLlmSwitch.addEventListener("change", () => {
        // Disable generation config options if the LLM is not invoked
        genConfigOptions.style.opacity = invokeLlmSwitch.checked ? "1" : "0.5";
        genConfigOptions.querySelectorAll("input").forEach((input) => {
            input.disabled = !invokeLlmSwitch.checked;
        });
    });

    // Add event listeners for SRD input elements
    uploadForm.addEventListener("submit", handleUpload);

    // Add listeners for the SRD table
    refreshDocsButton.addEventListener("click", handleRefresh);
    srdIdInput.addEventListener("input", () => {
        // Automatically refresh the list when the user types a new SRD ID
        handleRefresh();
    });

    // --- JWT HELPER ---
    function parseJwt(token) {
        try {
            return JSON.parse(atob(token.split(".")[1]));
        } catch (e) {
            return null;
        }
    }

    // --- EVENT LISTENERS ---
    loginForm.addEventListener("submit", handleLogin);
    newPasswordForm.addEventListener("submit", handleNewPasswordSubmit);
    queryButton.addEventListener("click", handleQuery);
    logoutButton.addEventListener("click", handleLogout);

    // Add navigation listeners
    navbar.addEventListener("click", (e) => {
        if (e.target.matches(".nav-link") && e.target.dataset.view) {
            e.preventDefault();
            showMainView(e.target.dataset.view);
        }
    });

    // --- LOGIC ---
    // Global vars to hold challenge state
    let loginSession = null;
    let challengeUsername = null;

    // --- FUNCTIONS ---
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

    // Function to handle login
    async function handleLogin(e) {
        e.preventDefault();
        loginError.textContent = "";
        showScreen("logging-in-view");

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
        showScreen("logging-in-view");

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
            await completeLogin(data.IdToken, data.RefreshToken);
        } catch (error) {
            // Handle errors gracefully
            console.error("New Password Error:", error);
            newPasswordError.textContent = `Error: ${error.message}`;
            showScreen("new-password-view"); // Show password form again on error
        }
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
        showMainView("query-view"); // Show the query view by default
    }

    /*
     * Handles user logout by clearing local storage and updating the UI.
     * This function hides the admin tab, clears the SRD dropdown,
     * and shows the login view again.
     */
    function handleLogout() {
        localStorage.clear();
        adminNavItem.classList.add("d-none"); // Hide admin tab on logout
        showScreen("login-view");
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

        // Add it to the payload if it's a valid number
        if (!isNaN(numDocs) && numDocs > 0) {
            payload.number_of_documents = numDocs;
        }

        // If the LLM is invoked, add generation config parameters
        if (invokeGenerativeLlm) {
            const temp = parseFloat(temperatureSlider.value);
            if (!isNaN(temp)) payload.generation_config.temperature = temp;

            const topP = parseFloat(topPSlider.value);
            if (!isNaN(topP)) payload.generation_config.topP = topP;

            const maxTokenCount = parseInt(maxTokensInput.value, 10);
            if (!isNaN(maxTokenCount) && maxTokenCount > 0)
                payload.generation_config.maxTokenCount = maxTokenCount;

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
     * Fetches and displays documents for the SRD ID in the input field.
        * This function retrieves documents from the API and displays them in a table.
        * If no SRD ID is provided, it shows a message prompting the user to enter one.
        * If documents are found, they are displayed in a table with their names and processing statuses.
        * If an error occurs, it displays an appropriate error message.
    */
    async function handleRefresh() {
        const srdId = srdIdInput.value.trim();
        if (!srdId) {
            documentsListStatus.textContent = "Enter an SRD ID to see its documents.";
            documentsTable.classList.add("d-none"); // Hide table
            return;
        }

        // Show loading state
        documentsListStatus.textContent = "Loading documents...";
        documentsTable.classList.add("d-none");
        documentsTableBody.innerHTML = "";
        refreshDocsButton.disabled = true;

        try {
            const documents = await makeAuthenticatedRequest(`/srd/${srdId}/documents`, "GET");
            
            if (documents && Array.isArray(documents) && documents.length > 0) {
                documentsListStatus.textContent = ""; // Clear status message
                documentsTable.classList.remove("d-none"); // Show table

                documents.forEach(doc => {
                    const row = documentsTableBody.insertRow();
                    const cellName = row.insertCell(0);
                    const cellStatus = row.insertCell(1);

                    cellName.textContent = doc.original_file_name;
                    
                    // Add a styled badge for the status
                    const statusBadge = document.createElement("span");
                    statusBadge.textContent = doc.processing_status;
                    statusBadge.className = getStatusBadgeClass(doc.processing_status);
                    cellStatus.appendChild(statusBadge);
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
     * Returns a Bootstrap badge class based on the document processing status.
     * @param {string} status - The processing status string.
     * @returns {string} The corresponding Bootstrap badge class.
     */
    function getStatusBadgeClass(status) {
        switch (status.toLowerCase()) {
            case 'completed':
                return 'badge text-bg-success';
            case 'processing':
                return 'badge text-bg-info';
            case 'pending':
                return 'badge text-bg-warning';
            case 'failed':
                return 'badge text-bg-danger';
            default:
                return 'badge text-bg-secondary';
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
                    content_type: file.type
                }
            );

            uploadStatus.innerHTML = `<div class="alert alert-info">Step 2 of 2: Uploading file to S3... This may take a moment.</div>`;

            // --- Step 2: Upload the file directly to S3 using the URL ---
            const s3Url = presignedUrlResponse.presigned_url_data.url;

            // Upload the file to S3 using the pre-signed URL
            const uploadResponse = await fetch(s3Url, {
                method: 'PUT',
                headers: {
                    'Content-Type': file.type,
                },
                body: file
            });

            // Check if the upload was successful
            if (!uploadResponse.ok) {
                const errorText = await uploadResponse.text();
                throw new Error(`S3 Upload Failed: ${errorText}`);
            }

            uploadStatus.innerHTML = `<div class="alert alert-success">Upload complete! Your document is now being processed.</div>`;
            fileInput.value = ""; // Clear the file input

            // Refresh the document list after a successful upload
            await new Promise(resolve => setTimeout(resolve, 1500)); // Wait a moment for consistency
            await handleRefresh();

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

    // Initial view state
    showScreen("login-view");
});
