"""
Utility functions for error handling and API calls.
Extracted from app.js for better modularity.
"""

// Safe API call wrapper with error handling
async function safeAPICall(url, options = {}) {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API call failed: ${url}`, error);

        // Show user-friendly error message
        if (error.message.includes('Failed to fetch')) {
            showToast('Connection error. Please check if the server is running.', 'error');
        } else {
            showToast(`Request failed: ${error.message}`, 'error');
        }

        return null;
    }
}

// Retry wrapper for transient failures
async function retryAPICall(url, options = {}, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        const result = await safeAPICall(url, options);
        if (result !== null) {
            return result;
        }

        // Wait before retry (exponential backoff)
        if (i < maxRetries - 1) {
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
        }
    }

    return null;
}

// Export for use in app.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { safeAPICall, retryAPICall };
}
