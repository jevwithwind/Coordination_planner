from fastapi import FastAPI, HTTPException, Request, File, UploadFile, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import time
import json
from datetime import datetime
import mimetypes
from .recommend import get_recommendations
from .preferences import enrich_wardrobe_with_preferences, record_decision
from .decision_log import log_decision, get_decision_count

# Create the FastAPI app
app = FastAPI(title="Wardrobe Coordination Planner")

# Add CORS middleware to allow access from other devices on the LAN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the frontend directory
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Create users directory if it doesn't exist
os.makedirs("../users", exist_ok=True)

# Create profiles.json if it doesn't exist
profiles_path = "../users/profiles.json"
if not os.path.exists(profiles_path):
    with open(profiles_path, 'w') as f:
        json.dump({}, f)


class UserCreateRequest(BaseModel):
    display_name: str

class ChatRequest(BaseModel):
    message: str
    username: str

class DecideRequest(BaseModel):
    scenario: str
    scenario_breakdown: dict
    chosen_outfit_index: int = None  # 0, 1, 2 for chosen outfit, or None for "none of the above"
    all_outfits: list

class CatalogProgress:
    def __init__(self):
        self.generators = {}

    def add_generator(self, username, generator):
        self.generators[username] = generator

    def remove_generator(self, username):
        if username in self.generators:
            del self.generators[username]

progress_manager = CatalogProgress()

def generate_catalog_progress(username: str, photos_dir: str, wardrobe_path: str):
    """Generator function to yield cataloging progress updates."""
    import asyncio
    from cataloging.utils import scan_image_files, process_single_image, load_wardrobe, save_wardrobe
    import time
    
    # Load existing wardrobe
    wardrobe = load_wardrobe(wardrobe_path)
    existing_files = set(wardrobe.keys())
    
    # Get all image files
    image_files = scan_image_files(photos_dir)
    new_files = [f for f in image_files if f not in existing_files]
    
    total_new = len(new_files)
    
    if total_new == 0:
        yield f"data: {json.dumps({'status': 'complete', 'current': 0, 'total': 0, 'message': 'No new photos to catalog'})}\n\n"
        return
    
    yield f"data: {json.dumps({'status': 'started', 'current': 0, 'total': total_new, 'message': f'Found {total_new} new photos to catalog'})}\n\n"
    
    processed = 0
    for filename in new_files:
        processed += 1
        try:
            image_path = os.path.join(photos_dir, filename)
            result = process_single_image(image_path)
            
            if result:
                try:
                    item_data = json.loads(result)
                    wardrobe[filename] = item_data
                    save_wardrobe(wardrobe, wardrobe_path)
                    yield f"data: {json.dumps({'status': 'processing', 'current': processed, 'total': total_new, 'message': f'Processed {filename}'})}\n\n"
                except json.JSONDecodeError as e:
                    yield f"data: {json.dumps({'status': 'error', 'current': processed, 'total': total_new, 'message': f'Error parsing result for {filename}: {str(e)}'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'current': processed, 'total': total_new, 'message': f'Failed to analyze {filename}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'current': processed, 'total': total_new, 'message': f'Error processing {filename}: {str(e)}'})}\n\n"
        
        # Add delay to avoid rate limiting
        time.sleep(1)
    
    yield f"data: {json.dumps({'status': 'complete', 'current': total_new, 'total': total_new, 'message': f'Cataloging complete! Added {total_new} items.'})}\n\n"

@app.get("/api/users")
async def get_users():
    """List all user profiles."""
    try:
        profiles_path = "../users/profiles.json"
        if not os.path.exists(profiles_path):
            return {}
        
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        return profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading user profiles: {str(e)}")

@app.post("/api/users")
async def create_user(request: UserCreateRequest):
    """Create a new user profile."""
    try:
        # Sanitize username (convert to lowercase, replace spaces with underscores)
        username = request.display_name.lower().replace(" ", "_").replace("-", "_")
        
        # Ensure uniqueness by appending a number if needed
        original_username = username
        counter = 1
        while os.path.exists(f"../users/{username}"):
            username = f"{original_username}{counter}"
            counter += 1
        
        # Create user directory structure
        user_dir = f"../users/{username}"
        photos_dir = f"{user_dir}/wardrobe_photos"
        os.makedirs(photos_dir, exist_ok=True)
        
        # Create empty wardrobe.json
        wardrobe_path = f"{user_dir}/wardrobe.json"
        with open(wardrobe_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        # Add to profiles
        profiles_path = "../users/profiles.json"
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        profiles[username] = {
            "display_name": request.display_name,
            "created": datetime.now().strftime("%Y-%m-%d")
        }
        
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2)
        
        return {"username": username, "display_name": request.display_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.delete("/api/users/{username}")
async def delete_user(username: str):
    """Delete a user profile and all their data."""
    try:
        user_dir = f"../users/{username}"
        if not os.path.exists(user_dir):
            raise HTTPException(status_code=404, detail="User not found")
        
        # Remove user directory
        shutil.rmtree(user_dir)
        
        # Remove from profiles
        profiles_path = "../users/profiles.json"
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        if username in profiles:
            del profiles[username]
        
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2)
        
        return {"message": f"User {username} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle chat requests and return outfit recommendations."""
    try:
        # Get recommendations using the recommend module
        wardrobe_path = f"../users/{request.username}/wardrobe.json"
        
        # Load wardrobe and enrich with preferences
        from .preferences import enrich_wardrobe_with_preferences
        import os
        import json
        
        if not os.path.exists(wardrobe_path):
            return {"outfits": [], "scenario_breakdown": {}, "styling_tips": "No wardrobe items found. Please upload and catalog some clothing items first.", "scenario": request.message}
        
        with open(wardrobe_path, 'r', encoding='utf-8') as f:
            wardrobe = json.load(f)
        
        # Extract scenario features from the user message for preference calculation
        # This is a simplified approach - in a real implementation you'd have more sophisticated NLP
        scenario_features = []
        msg_lower = request.message.lower()
        if any(word in msg_lower for word in ["golf", "tennis", "sport", "athletic", "exercise", "workout", "run", "hike"]):
            scenario_features.append("athletic")
        if any(word in msg_lower for word in ["formal", "wedding", "event", "ceremony", "gala"]):
            scenario_features.append("formal")
        if any(word in msg_lower for word in ["office", "work", "business", "meeting", "interview"]):
            scenario_features.append("business")
        if any(word in msg_lower for word in ["casual", "hangout", "friend", "relaxed"]):
            scenario_features.append("casual")
        
        # Enrich wardrobe with preferences
        enriched_wardrobe = enrich_wardrobe_with_preferences(wardrobe, request.username, scenario_features)
        
        # Temporarily save enriched wardrobe for get_recommendations to use
        temp_path = f"../users/{request.username}/wardrobe_enriched_temp.json"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_wardrobe, f, indent=2, ensure_ascii=False)
        
        recommendations = get_recommendations(
            user_message=request.message,
            wardrobe_path=temp_path
        )
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Add the original scenario to the response
        recommendations["scenario"] = request.message
        
        return JSONResponse(content=recommendations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/api/decide/{username}")
async def decide_outfit(username: str, request: DecideRequest):
    """Record user decision on outfit recommendations."""
    try:
        if request.chosen_outfit_index is not None:
            # User chose an outfit - update preferences
            chosen_outfit = request.all_outfits[request.chosen_outfit_index]
            
            # Extract items from the chosen outfit layers
            chosen_items = []
            for layer_key, filename in chosen_outfit.get("layers", {}).items():
                if filename and filename != "null":  # Check for explicit null string
                    chosen_items.append(filename)
            
            # Extract scenario features from scenario breakdown
            scenario_features = []
            scenario_breakdown = request.scenario_breakdown
            if scenario_breakdown.get("activity"):
                scenario_features.append(scenario_breakdown["activity"])
            if scenario_breakdown.get("season"):
                scenario_features.append(scenario_breakdown["season"])
            if scenario_breakdown.get("formality"):
                scenario_features.append(scenario_breakdown["formality"])
            
            # Record the decision
            from .preferences import record_decision
            record_decision(username, chosen_items, scenario_features)
        
        # Log the decision regardless of whether an outfit was chosen
        from .decision_log import log_decision
        log_decision(
            username=username,
            scenario=request.scenario,
            scenario_breakdown=request.scenario_breakdown,
            outfits_presented=request.all_outfits,
            user_choice=request.chosen_outfit_index
        )
        
        # If user chose "none of the above", return new recommendations
        if request.chosen_outfit_index is None:
            wardrobe_path = f"../users/{username}/wardrobe.json"
            
            # Load wardrobe and enrich with preferences
            from .preferences import enrich_wardrobe_with_preferences
            import os
            import json
            
            if not os.path.exists(wardrobe_path):
                return {"outfits": [], "scenario_breakdown": {}, "styling_tips": "No wardrobe items found.", "scenario": request.scenario}
            
            with open(wardrobe_path, 'r', encoding='utf-8') as f:
                wardrobe = json.load(f)
            
            # Extract scenario features from the scenario for preference calculation
            scenario_features = []
            msg_lower = request.scenario.lower()
            if any(word in msg_lower for word in ["golf", "tennis", "sport", "athletic", "exercise", "workout", "run", "hike"]):
                scenario_features.append("athletic")
            if any(word in msg_lower for word in ["formal", "wedding", "event", "ceremony", "gala"]):
                scenario_features.append("formal")
            if any(word in msg_lower for word in ["office", "work", "business", "meeting", "interview"]):
                scenario_features.append("business")
            if any(word in msg_lower for word in ["casual", "hangout", "friend", "relaxed"]):
                scenario_features.append("casual")
            
            # Enrich wardrobe with preferences
            enriched_wardrobe = enrich_wardrobe_with_preferences(wardrobe, username, scenario_features)
            
            # Temporarily save enriched wardrobe for get_recommendations to use
            temp_path = f"../users/{username}/wardrobe_enriched_temp.json"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_wardrobe, f, indent=2, ensure_ascii=False)
            
            recommendations = get_recommendations(
                user_message=request.scenario,
                wardrobe_path=temp_path
            )
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Add the original scenario to the response
            recommendations["scenario"] = request.scenario
            
            return JSONResponse(content=recommendations)
        else:
            # User chose an outfit, return success response
            return {"status": "success", "message": "Decision recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing decision: {str(e)}")

@app.get("/api/wardrobe/{username}")
async def get_wardrobe(username: str):
    """Return the wardrobe data for a specific user."""
    try:
        wardrobe_path = f"../users/{username}/wardrobe.json"
        if not os.path.exists(wardrobe_path):
            return {}
        
        with open(wardrobe_path, 'r', encoding='utf-8') as f:
            wardrobe = json.load(f)
        return wardrobe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading wardrobe: {str(e)}")

@app.get("/photos/{username}/{filename}")
async def get_photo(username: str, filename: str):
    """Serve a photo for a specific user."""
    try:
        photo_path = f"../users/{username}/wardrobe_photos/{filename}"
        if not os.path.exists(photo_path):
            raise HTTPException(status_code=404, detail="Photo not found")
        
        # Determine content type based on file extension
        content_type, _ = mimetypes.guess_type(photo_path)
        if content_type is None:
            content_type = "application/octet-stream"
        
        return FileResponse(photo_path, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving photo: {str(e)}")

@app.post("/api/upload/{username}")
async def upload_photos(username: str, files: list[UploadFile] = File(...)):
    """Upload photos for a specific user."""
    try:
        user_dir = f"../users/{username}"
        photos_dir = f"{user_dir}/wardrobe_photos"
        
        if not os.path.exists(user_dir):
            raise HTTPException(status_code=404, detail="User not found")
        
        uploaded_files = []
        for file in files:
            # Check file size (max 20MB)
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Seek back to beginning
            
            if file_size > 20 * 1024 * 1024:  # 20MB
                continue  # Skip oversized files
            
            # Check file extension
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.heic']:
                continue  # Skip unsupported files
            
            # Generate unique filename
            timestamp = int(time.time())
            original_name = os.path.splitext(file.filename)[0]
            safe_original = "".join(c for c in original_name if c.isalnum() or c in "._- ")
            new_filename = f"{username}_{timestamp}_{safe_original}{ext}"
            
            # Save file
            file_location = os.path.join(photos_dir, new_filename)
            with open(file_location, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            uploaded_files.append(new_filename)
        
        return {"uploaded_files": uploaded_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading photos: {str(e)}")

@app.post("/api/catalog/{username}")
async def start_catalog(request: Request, username: str):
    """Start cataloging process for unprocessed photos."""
    try:
        user_dir = f"../users/{username}"
        photos_dir = f"{user_dir}/wardrobe_photos"
        wardrobe_path = f"{user_dir}/wardrobe.json"
        
        if not os.path.exists(user_dir):
            raise HTTPException(status_code=404, detail="User not found")
        
        def event_generator():
            yield from generate_catalog_progress(username, photos_dir, wardrobe_path)
        
        progress_manager.add_generator(username, event_generator())
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting catalog: {str(e)}")

@app.get("/api/wardrobe/{username}")
async def get_wardrobe(username: str):
    """Return the wardrobe data for a specific user."""
    try:
        wardrobe_path = f"../users/{username}/wardrobe.json"
        if not os.path.exists(wardrobe_path):
            return {}
        
        with open(wardrobe_path, 'r', encoding='utf-8') as f:
            wardrobe = json.load(f)
        return wardrobe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading wardrobe: {str(e)}")

@app.delete("/api/wardrobe/{username}/{filename}")
async def delete_wardrobe_item(username: str, filename: str):
    """Remove an item from the wardrobe."""
    try:
        user_dir = f"../users/{username}"
        wardrobe_path = f"{user_dir}/wardrobe.json"
        photo_path = f"{user_dir}/wardrobe_photos/{filename}"
        
        if not os.path.exists(user_dir):
            raise HTTPException(status_code=404, detail="User not found")
        
        # Remove from wardrobe.json
        if os.path.exists(wardrobe_path):
            with open(wardrobe_path, 'r', encoding='utf-8') as f:
                wardrobe = json.load(f)
            
            if filename in wardrobe:
                del wardrobe[filename]
                
                with open(wardrobe_path, 'w', encoding='utf-8') as f:
                    json.dump(wardrobe, f, indent=2, ensure_ascii=False)
        
        # Remove photo file if it exists
        if os.path.exists(photo_path):
            os.remove(photo_path)
        
        return {"message": f"Item {filename} removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing item: {str(e)}")

@app.get("/api/preferences/{username}")
async def get_preferences_stats(username: str):
    """Get preference learning statistics for a user."""
    try:
        from .decision_log import get_decision_count
        from .preferences import load_preferences
        
        decision_count = get_decision_count(username)
        preferences = load_preferences(username)
        
        # Determine learning status based on decision count
        if decision_count == 0:
            learning_status = "Cold start"
        elif decision_count <= 5:
            learning_status = "Building"
        else:
            learning_status = "Well-trained"
        
        return {
            "decisions_logged": decision_count,
            "learning_status": learning_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting preferences stats: {str(e)}")

@app.post("/api/preferences/{username}/reset")
async def reset_preferences(username: str):
    """Reset user preferences (but keep decision log)."""
    try:
        from .preferences import save_preferences
        
        # Create default preferences
        default_prefs = {
            "item_scores": {},
            "decisions_since_last_decay": 0
        }
        save_preferences(username, default_prefs)
        
        return {"message": "Preferences reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting preferences: {str(e)}")

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