from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
from .recommend import get_recommendations
import json

# Create the FastAPI app
app = FastAPI(title="Wardrobe Coordination Planner")

# Serve static files from the frontend directory
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Serve photos from the wardrobe_photos directory
app.mount("/photos", StaticFiles(directory="../wardrobe_photos"), name="photos")


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle chat requests and return outfit recommendations."""
    try:
        # Get recommendations using the recommend module
        recommendations = get_recommendations(
            user_message=request.message,
            wardrobe_path="../data/wardrobe.json"
        )
        return JSONResponse(content=recommendations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/api/wardrobe")
async def get_wardrobe():
    """Return the current wardrobe data."""
    try:
        wardrobe_path = "../data/wardrobe.json"
        if not os.path.exists(wardrobe_path):
            return {}
        
        with open(wardrobe_path, 'r', encoding='utf-8') as f:
            wardrobe = json.load(f)
        return wardrobe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading wardrobe: {str(e)}")


@app.get("/")
async def serve_index():
    """Serve the main index.html file."""
    index_path = "../frontend/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        # If index.html doesn't exist, return a simple message
        return {"message": "Welcome to Wardrobe Coordination Planner! Please add your frontend files to the frontend directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)