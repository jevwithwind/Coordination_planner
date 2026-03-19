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
├── wardrobe_photos/          # User drops clothing photos here
├── cataloging/
│   ├── catalog.py            # One-time script to label all clothes via Claude Vision API
│   └── add_item.py           # Script to add a single new item without re-processing all
├── data/
│   └── wardrobe.json         # Generated clothing database
├── backend/
│   ├── app.py                # FastAPI server (chat endpoint + static file serving)
│   ├── recommend.py          # Recommendation logic: pre-filter → Qwen API → structured JSON
│   └── config.py             # API key loading, constants
├── frontend/
│   └── index.html            # Single-page chat UI with image display
├── requirements.txt
├── .env                      # API keys go here
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Anthropic API Key (for image analysis)
- DashScope API Key (for recommendation engine)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
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

## Usage

The system operates in three main stages:

### 1. Catalog Your Wardrobe

Place all your clothing photos in the `wardrobe_photos/` directory. Supported formats: JPG, JPEG, PNG, WEBP, HEIC.

Run the cataloging script to analyze all images:
```bash
python cataloging/catalog.py
```

This will create `data/wardrobe.json` with detailed information about each clothing item.

To add a single new item without reprocessing all photos:
```bash
python cataloging/add_item.py <filename.jpg>
```

### 2. Start the Server

Launch the FastAPI server:
```bash
uvicorn backend.app:app --reload
```

The application will be available at `http://localhost:8000`

### 3. Use the Application

Visit `http://localhost:8000` in your browser to interact with the chat interface. Describe your plans, occasion, or weather conditions, and the AI will suggest coordinated outfits from your cataloged wardrobe.

## API Keys Configuration

This project uses two different AI services:

- **Anthropic Claude API** (via `anthropic` Python SDK): Used exclusively for image analysis during cataloging
  - Model: `claude-sonnet-4-20250514`
  - Environment variable: `ANTHROPIC_API_KEY`

- **Qwen API** (via `openai` Python SDK with custom base URL): Used for recommendation logic, season detection, and chat functionality
  - Model: `qwen3-coder-plus`
  - Base URL: `https://coding.dashscope.aliyuncs.com/v1`
  - Environment variable: `DASHSCOPE_API_KEY`

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