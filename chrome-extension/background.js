// Background Service Worker for Local RAG Agent Extension
// Handles communication between content script and RAG backend

const RAG_API_BASE = "http://127.0.0.1:8501";

// Sync content to RAG agent
async function syncToRAG(tabId) {
  try {
    // Get the active tab's content
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        // Extract meaningful text content
        const body = document.body;
        const clone = body.cloneNode(true);
        
        // Remove script and style elements
        clone.querySelectorAll('script, style, noscript, iframe').forEach(el => el.remove());
        
        // Get text content
        let text = clone.innerText || clone.textContent;
        
        // Clean up whitespace
        text = text.replace(/\s+/g, ' ').trim();
        
        return {
          url: window.location.href,
          title: document.title,
          content: text.substring(0, 10000) // Limit to 10KB
        };
      }
    });

    if (result && result.result) {
      const response = await fetch(`${RAG_API_BASE}/api/browser/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result.result)
      });
      
      if (response.ok) {
        console.log("RAG Agent: Synced page content successfully");
        return { success: true, url: result.result.url };
      } else {
        console.error("RAG Agent: Sync failed", response.status);
        return { success: false, error: `Server error: ${response.status}` };
      }
    }
  } catch (error) {
    console.error("RAG Agent: Error syncing", error);
    return { success: false, error: error.message };
  }
}

// Check if RAG server is running
async function checkServerHealth() {
  try {
    const response = await fetch(`${RAG_API_BASE}/health`, { 
      method: "GET",
      signal: AbortSignal.timeout(3000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Get current browser context from RAG
async function getBrowserContext() {
  try {
    const response = await fetch(`${RAG_API_BASE}/api/browser/context`);
    if (response.ok) {
      return await response.json();
    }
  } catch {
    return null;
  }
}

// Clear browser context
async function clearContext() {
  try {
    await fetch(`${RAG_API_BASE}/api/browser/clear`, { method: "POST" });
    return true;
  } catch {
    return false;
  }
}

// Message handler for popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "sync") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (tabs[0]) {
        const result = await syncToRAG(tabs[0].id);
        sendResponse(result);
      } else {
        sendResponse({ success: false, error: "No active tab" });
      }
    });
    return true; // Keep channel open for async response
  }
  
  if (message.action === "checkHealth") {
    checkServerHealth().then(healthy => {
      sendResponse({ healthy });
    });
    return true;
  }
  
  if (message.action === "getContext") {
    getBrowserContext().then(context => {
      sendResponse(context);
    });
    return true;
  }
  
  if (message.action === "clearContext") {
    clearContext().then(success => {
      sendResponse({ success });
    });
    return true;
  }
});

console.log("Local RAG Agent Extension loaded");
