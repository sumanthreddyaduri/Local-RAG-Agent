chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error(error));

// Listen for connection status requests from sidepanel
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'check_connection') {
        // Future: Check if localhost:5000 is reachable?
        sendResponse({ status: 'unknown' });
    }
});
