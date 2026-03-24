# Wardrobe Coordination Planner

A smart wardrobe management system that uses AI to help you coordinate outfits based on your existing clothing items, weather conditions, and occasions.

## Features

- **Image-based Clothing Cataloging**: Automatically analyze and categorize your clothing items using AI vision technology
- **Smart Outfit Recommendations**: Get personalized outfit suggestions based on weather, occasion, and season
- **Interactive Chat Interface**: Natural language interaction to get styling advice
- **Visual Wardrobe Browser**: See your clothing items displayed in recommended outfits

## Architecture

```
Coordination_planner/
├── users/
│   ├── Kevin/
│   │   ├── wardrobe_photos/    # Kevin's clothing photos
│   │   └── wardrobe.json       # Kevin's catalog
│   ├── NIU/
│   │   ├── wardrobe_photos/
│   │   └── wardrobe.json
│   └── ...
├── backend/
│   ├── app.py                # FastAPI server (chat endpoint + static file serving)
│   ├── recommend.py          # Recommendation logic: pre-filter → Qwen API → structured JSON
│   └── config.py             # API key loading, constants
├── frontend/
│   └── index.html            # Single-page app UI with image display
├── cataloging/
│   └── utils.py              # Shared cataloging logic
├── requirements.txt
├── .env                      # API keys go here
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Anthropic API Key (for image analysis)
- OpenAI-compatible API Key (for recommendation engine, lower cost per use)

### Installation

1. Clone the repository:
   ```bash
   git clone <https://github.com/jevwithwind/Coordination_planner>
   cd Coordination_planner
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

## How It Works

### Clothing Categorization Schema
The system uses a detailed categorization schema to understand your wardrobe:
- **6 primary categories**: outerwear, layered_wear, inner_wear, bottoms, shoes, accessories
- Each item is tagged with color, material, thickness, occasion, silhouette, and season
- AI vision (Claude Sonnet) analyzes each photo once to generate these detailed tags

### Outfit Recommendations
- Each recommendation presents 3 complete outfits following a layering structure
- Outfits are displayed top-to-bottom: outerwear → layered wear → inner wear → bottoms → shoes
- Users choose their preferred fit or request new options
- The system learns from choices to improve future recommendations

### Preference Learning
- System learns which items you prefer for specific scenarios (activity, season, formality)
- Scores increase gradually with a diminishing returns formula for stability
- Scores decay mildly over time to prevent stale preferences from dominating
- "None of the above" does not penalize any items
- All decisions are logged for transparency (decision_log.jsonl)
- Preferences can be reset without losing the decision log

### Decision Log
- Every recommendation event is logged to `users/{username}/decision_log.jsonl`
- Logs include: scenario, AI's interpretation, all 3 outfits presented, user's choice
- Log is append-only and survives preference resets
- Useful for debugging and analyzing recommendation patterns

## Usage

The system now supports multiple users in a household:

### 1. Install Dependencies and Set Up

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Run the Server

Launch the FastAPI server to make it accessible on your local network:
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access from Any Device

On any device connected to the same network, open `http://<your-mac-ip>:8000`

To find your Mac's local IP address:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### 4. Create User Profiles

1. Create a profile for each household member through the web UI
2. Upload photos of clothing items using the "Upload Photos" button
3. The system will automatically catalog the new items
4. Start chatting for outfit recommendations

## API Architecture

This project uses TWO separate API providers for different purposes:

- **Cataloging (Vision)**: Requires a model with strong image understanding. Currently uses Anthropic Claude Sonnet via the `anthropic` SDK. This runs once when you catalog your wardrobe.
  - Model: `claude-sonnet-4-20250514`
  - Environment variable: `ANTHROPIC_API_KEY`

- **Recommendation (Chat)**: Requires a model with good text reasoning. Currently uses Qwen3 via an OpenAI-compatible endpoint. This runs every time you ask for outfit advice.
  - Model: `qwen3-coder-plus`
  - Base URL: `https://coding.dashscope.aliyuncs.com/v1`
  - Environment variable: `CHAT_API_KEY`

These are intentionally decoupled — users can swap either one independently.

## Switching API Providers

### To use OpenAI for recommendations instead of Qwen:
- In `.env`: replace `CHAT_API_KEY` with your OpenAI key
- In `backend/config.py`: change `QWEN_BASE_URL` to `https://api.openai.com/v1` and `QWEN_MODEL` to `gpt-4o` (or your preferred model)
- No other code changes needed since it already uses the `openai` SDK

### To use a different OpenAI-compatible provider (Groq, Together, local Ollama, etc.):
- In `.env`: set your provider's API key as `CHAT_API_KEY`
- In `backend/config.py`: change `QWEN_BASE_URL` to your provider's endpoint and `QWEN_MODEL` to your model name
- For Ollama (local): base_url is `http://localhost:11434/v1`, no API key needed

### To use OpenAI or another vision-capable model for cataloging:
- This requires code changes in `cataloging/catalog.py` and `add_item.py` since they use the `anthropic` SDK directly
- You would need to replace the Anthropic client with the `openai` SDK and adjust the message format for image inputs
- The system prompt and expected JSON output format can stay the same

## API Keys Configuration

This project uses two different AI services:

- **Anthropic Claude API** (via `anthropic` Python SDK): Used exclusively for image analysis during cataloging
  - Model: `claude-sonnet-4-20250514`
  - Environment variable: `ANTHROPIC_API_KEY`

- **Qwen API** (via `openai` Python SDK with custom base URL): Used for recommendation logic, season detection, and chat functionality
  - Model: `qwen3-coder-plus`
  - Base URL: `https://coding.dashscope.aliyuncs.com/v1`
  - Environment variable: `CHAT_API_KEY`

## How It Works

1. **Cataloging Phase**: The `catalog.py` script scans all images in `wardrobe_photos/`, resizes them to optimize API costs, and sends them to the Anthropic Claude API for analysis. Each item is categorized with properties like category, color, material, season, and formality.

2. **Recommendation Logic**: When you submit a request through the chat interface, the system:
   - Determines the current season based on temperature mentioned in your message or the current month
   - Filters your wardrobe to show only seasonally appropriate items
   - Sends your request and the filtered wardrobe to the Qwen API
   - Parses the response to display outfit recommendations with images

3. **Frontend Display**: The web interface displays your conversation and renders outfit recommendations as visual cards with the actual clothing images.

## Customization

You can customize the system by modifying:
- System prompts in `cataloging/catalog.py` and `backend/recommend.py`
- Season determination logic in `backend/recommend.py`
- UI elements in `frontend/index.html`
- Clothing categories and attributes in the cataloging system

## Troubleshooting

- If images aren't loading, ensure they're placed in the `wardrobe_photos/` directory and have been processed by the cataloging script
- If recommendations aren't appearing, verify your API keys are correctly set in the `.env` file
- Check that the server is running when accessing the web interface