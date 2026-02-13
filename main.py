import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import bot  # Import the bot module

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"----- SYSTEM INFO -----")
    print(f"Python Version: {sys.version}")
    print(f"-----------------------")
    # Start the bot as a background task
    asyncio.create_task(bot.start_bot())
    bot.logger.info("Web Dashboard Started")
    yield
    # Shutdown logic
    await bot.stop_bot()

app = FastAPI(title="Hinata Bot Dashboard", lifespan=lifespan)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ControlAction(BaseModel):
    action: str

class BroadcastMsg(BaseModel):
    target: str
    message: str



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/data")
async def get_data():
    """Returns all users and groups with full metadata."""
    users = bot.read_json("users.json", [])
    groups = bot.read_json("groups.json", [])
    
    # Ensure backward compatibility/formatting
    formatted_users = []
    for u in users:
        if isinstance(u, dict): formatted_users.append(u)
        else: formatted_users.append({"id": u, "name": "Legacy User", "username": "unknown"})
        
    formatted_groups = []
    for g in groups:
        if isinstance(g, dict): formatted_groups.append(g)
        else: formatted_groups.append({"id": g, "title": "Legacy Group"})

    return {
        "stats": {
            "users_count": len(users),
            "groups_count": len(groups),
            "broadcasts": bot.STATS.get("broadcasts", 0),
            "uptime": bot.get_uptime(),
            "status": bot.STATS.get("status", "online")
        },
        "users": formatted_users,
        "groups": formatted_groups
    }


@app.get("/api/logs")
async def get_logs():
    # Read last 50 lines from log file
    if os.path.exists(bot.LOG_FILE):
        with open(bot.LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-50:]
    return ["Log file not found."]

@app.post("/api/control")
async def control_bot(data: ControlAction):
    if data.action == "restart":
        # In a real cloud environment, a restart might just mean restarting the process
        # Here we just stop and start the bot instance
        await bot.stop_bot()
        asyncio.create_task(bot.start_bot())
        return {"success": True}
    elif data.action == "clear_logs":
        if os.path.exists(bot.LOG_FILE):
            open(bot.LOG_FILE, "w").close()
        return {"success": True}
    return {"success": False, "error": "Unknown action"}

@app.post("/api/broadcast")
async def api_broadcast(data: BroadcastMsg):
    try:
        if not bot.app:
            return {"success": False, "error": "Bot not initialized"}
        
        # We need a proper context/app to send messages
        # Here we use the bot's global app object
        if data.target == "all" or data.target == "users":
            users = bot.read_json("users.json", [])
            for uid in users:
                try: await bot.app.bot.send_message(chat_id=uid, text=data.message)
                except: pass
        
        if data.target == "all" or data.target == "groups":
            groups = bot.read_json("groups.json", [])
            for gid in groups:
                try: await bot.app.bot.send_message(chat_id=gid, text=data.message)
                except: pass
                
        bot.STATS["broadcasts"] += 1
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use environment variables for port (Render uses PORT env)
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
