import os
import sys
import subprocess
import threading
import time
import webbrowser
import psutil
import pyautogui
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BUNDLE_DIR

load_dotenv(os.path.join(APP_DIR, ".env"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LITELLM_URL = "http://127.0.0.1:4000/v1/chat/completions"
gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=60000)
) if GEMINI_API_KEY else None

SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's AI assistant.
Address the user as 'Sir'. Keep responses concise, sharp, witty, and natural for voice synthesis (no markdown symbols like *, #, or bullet points).
If the user asks to perform a PC action, append ONE action tag at the very end of your response:
- Open Chrome: [ACTION:OPEN_CHROME]
- Open Notepad: [ACTION:OPEN_NOTEPAD]
- Open Calculator: [ACTION:OPEN_CALC]
- Open YouTube: [ACTION:OPEN_YOUTUBE]
- Take Screenshot: [ACTION:SCREENSHOT]
- System Diagnostics: [ACTION:SYS_STATUS]
"""

class ChatRequest(BaseModel):
    message: str
    mode: str = "gemini-model"

def execute_pc_action(reply: str) -> str:
    if "[ACTION:OPEN_CHROME]" in reply:
        os.system("start chrome")
        return reply.replace("[ACTION:OPEN_CHROME]", "")
    elif "[ACTION:OPEN_NOTEPAD]" in reply:
        subprocess.Popen(["notepad.exe"])
        return reply.replace("[ACTION:OPEN_NOTEPAD]", "")
    elif "[ACTION:OPEN_CALC]" in reply:
        subprocess.Popen(["calc.exe"])
        return reply.replace("[ACTION:OPEN_CALC]", "")
    elif "[ACTION:OPEN_YOUTUBE]" in reply:
        webbrowser.open("https://www.youtube.com")
        return reply.replace("[ACTION:OPEN_YOUTUBE]", "")
    elif "[ACTION:SCREENSHOT]" in reply:
        path = os.path.join(os.path.expanduser("~"), "Desktop", "jarvis_capture.png")
        pyautogui.screenshot(path)
        return reply.replace("[ACTION:SCREENSHOT]", " Screenshot saved to your Desktop, Sir.")
    elif "[ACTION:SYS_STATUS]" in reply:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f"Battery is at {battery.percent} percent." if battery else ""
        clean = reply.replace("[ACTION:SYS_STATUS]", "")
        return f"{clean} CPU load is at {cpu} percent, memory utilization is {ram} percent. {bat_str}"
    return reply

@app.get("/")
def serve_hud():
    return FileResponse(os.path.join(BUNDLE_DIR, "index.html"))

@app.get("/stats")
def get_stats():
    bat = psutil.sensors_battery()
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "battery": bat.percent if bat else 100
    }

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        if req.mode == "gemini-model":
            if not gemini_client:
                return {"reply": "Apologies Sir, GEMINI_API_KEY is missing in your .env file.", "model_used": "offline"}
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=req.message,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7
                    )
                )
                used_model = "gemini-1.5-flash"
            except Exception:
                response = gemini_client.models.generate_content(
                    model="gemini-1.5-pro",
                    contents=req.message,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7
                    )
                )
                used_model = "gemini-1.5-pro"

            raw_reply = response.text or "Apologies Sir, Gemini returned an empty response."
        else:
            payload = {
                "model": req.mode,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": req.message}
                ],
                "temperature": 0.7
            }
            res = requests.post(
                LITELLM_URL,
                json=payload,
                headers={"Authorization": "Bearer dummy_key"},
                timeout=45
            )
            data = res.json()
            if "error" in data:
                err_msg = data["error"].get("message", str(data["error"]))
                return {"reply": f"Apologies Sir, neural link reported: {err_msg}", "model_used": "error"}
            raw_reply = data["choices"][0]["message"]["content"]
            used_model = data.get("model", req.mode)

        final_reply = execute_pc_action(raw_reply).strip()
        return {"reply": final_reply, "model_used": used_model}
    except Exception as e:
        return {"reply": f"Apologies Sir, neural link encountered an error: {str(e)}", "model_used": "offline"}

def open_hud():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=open_hud, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)