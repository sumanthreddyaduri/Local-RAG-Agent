const API_URL = 'http://localhost:8501/api';

// Elements
const connectView = document.getElementById('connect-view');
const chatView = document.getElementById('chat-view');
const tokenInput = document.getElementById('token-input');
const connectBtn = document.getElementById('connect-btn');
const errorMsg = document.getElementById('error-msg');
const statusBadge = document.getElementById('status-display');

// Check if already connected
chrome.storage.local.get(['onyx_api_key'], (result) => {
    if (result.onyx_api_key) {
        showChat();
    } else {
        checkHealth();
    }
});

function showChat() {
    connectView.style.display = 'none';
    chatView.style.display = 'flex';
}

function showConnect() {
    connectView.style.display = 'flex';
    chatView.style.display = 'none';
}

// Health Check
function checkHealth() {
    fetch(`${API_URL}/health`)
        .then(r => r.json())
        .then(data => {
            if (data.status === 'healthy') {
                statusBadge.textContent = 'Server Online 🟡';
                statusBadge.style.background = '#eab308';
                statusBadge.style.color = '#000';
            }
        })
        .catch(err => {
            statusBadge.textContent = 'Server Offline 🔴';
            statusBadge.style.background = '#ef4444';
        });
}

// Connect Handler
connectBtn.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    if (token.length !== 6) {
        errorMsg.textContent = 'Invalid code length';
        return;
    }

    try {
        errorMsg.textContent = 'Verifying...';
        const res = await fetch(`${API_URL}/extension/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });

        const data = await res.json();

        if (data.status === 'success' && data.api_key) {
            chrome.storage.local.set({ onyx_api_key: data.api_key }, () => {
                showChat();
                errorMsg.textContent = '';
            });
        } else {
            errorMsg.textContent = data.error || 'Verification failed';
        }
    } catch (e) {
        errorMsg.textContent = 'Connection error: ' + e.message;
    }
});

document.getElementById('disconnect-btn').addEventListener('click', () => {
    chrome.storage.local.remove('onyx_api_key', showConnect);
});

// Dev Reload
document.getElementById('reload-btn').addEventListener('click', () => {
    location.reload();
});
