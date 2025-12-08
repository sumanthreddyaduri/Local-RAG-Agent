// Popup script for Local RAG Agent Extension

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const syncBtn = document.getElementById('syncBtn');
const clearBtn = document.getElementById('clearBtn');
const contextInfo = document.getElementById('contextInfo');
const syncedUrl = document.getElementById('syncedUrl');
const messageEl = document.getElementById('message');

// Check server health on popup open
async function checkHealth() {
    chrome.runtime.sendMessage({ action: "checkHealth" }, (response) => {
        if (response && response.healthy) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected to RAG Agent';
            syncBtn.disabled = false;
            loadContext();
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'RAG Agent not running';
            syncBtn.disabled = true;
            showMessage('Start python app.py first', 'error');
        }
    });
}

// Load current context
function loadContext() {
    chrome.runtime.sendMessage({ action: "getContext" }, (response) => {
        if (response && response.url) {
            contextInfo.style.display = 'block';
            syncedUrl.textContent = response.url || 'None';
        } else {
            contextInfo.style.display = 'none';
        }
    });
}

// Sync current page
syncBtn.addEventListener('click', async () => {
    syncBtn.disabled = true;
    syncBtn.textContent = '⏳ Syncing...';

    chrome.runtime.sendMessage({ action: "sync" }, (response) => {
        if (response && response.success) {
            showMessage('Page synced successfully!', 'success');
            syncedUrl.textContent = response.url;
            contextInfo.style.display = 'block';
        } else {
            showMessage(response?.error || 'Sync failed', 'error');
        }
        syncBtn.disabled = false;
        syncBtn.textContent = '🔄 Sync Current Page';
    });
});

// Clear context
clearBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: "clearContext" }, (response) => {
        if (response && response.success) {
            showMessage('Context cleared', 'success');
            contextInfo.style.display = 'none';
            syncedUrl.textContent = 'None';
        }
    });
});

// Show message helper
function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    messageEl.style.display = 'block';

    setTimeout(() => {
        messageEl.style.display = 'none';
    }, 3000);
}

// Initialize
checkHealth();
