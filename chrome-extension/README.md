# Local RAG Agent - Chrome Extension

This Chrome extension syncs your active browser tab content with your Local RAG Agent, enabling context-aware AI responses based on what you're viewing.

## Features

- 🔄 **One-click sync** - Send current page content to RAG Agent
- 🌐 **Context-aware AI** - Get answers based on the page you're viewing
- 🔒 **Fully local** - All data stays on your machine
- ✨ **Clean UI** - Simple, modern popup interface

## Installation

### Step 1: Make sure RAG Agent is running
```bash
cd f:\RAG_Agent\local-rag-agent
python app.py
```

### Step 2: Load the extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder from this project

### Step 3: Use the extension

1. Navigate to any webpage you want to analyze
2. Click the extension icon in your toolbar
3. Click **"🔄 Sync Current Page"**
4. Switch to the RAG Agent UI and ask questions about the page!

## How It Works

1. The extension extracts text content from your active tab
2. Content is sent to `http://127.0.0.1:8501/api/browser/sync`
3. When you chat in "Browser Mode", the synced content is injected into the prompt
4. The AI responds with context-aware answers

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/browser/sync` | POST | Send page content to RAG |
| `/api/browser/context` | GET | Get currently synced content |
| `/api/browser/clear` | POST | Clear synced content |
| `/health` | GET | Check if server is running |

## Troubleshooting

### "RAG Agent not running"
- Make sure `python app.py` is running on port 8501

### Extension not syncing
- Check that the page has finished loading
- Some pages block content scripts (e.g., chrome:// pages)

### Content not appearing in chat
- Ensure you've switched to **Browser Mode** in the RAG Agent settings
- The synced content should show in the extension popup

## Privacy

- All data is processed locally on your machine
- No external servers are contacted
- Page content is only sent to `localhost:8501`

## File Structure

```
chrome-extension/
├── manifest.json      # Extension configuration
├── background.js      # Service worker (content extraction)
├── popup.html         # Popup UI
├── popup.js           # Popup logic
└── icons/             # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```
