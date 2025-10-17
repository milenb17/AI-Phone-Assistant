
# app_hardcoded.py
"""
Minimal FastAPI server that connects Twilio Voice calls to ConversationRelay
with *no* environment variables. Replace the PUBLIC_HOST below with your public URL.

Quickstart:
  1) pip install fastapi uvicorn
  2) Edit PUBLIC_HOST to your https host (e.g., your ngrok URL like https://abc123.ngrok.io)
  3) uvicorn app_hardcoded:app --host 0.0.0.0 --port 8000
  4) In Twilio Console, set your phone number (or TwiML App) Voice URL to: https://<host>/voice

Flow:
  - /voice: returns TwiML with <Connect><ConversationRelay url="wss://<host>/ws" .../></Connect>
  - /ws: WebSocket endpoint that receives 'prompt' messages and replies with 'text' tokens.
"""

import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, Response

# -------------------- Hardcoded config (edit these) --------------------
PUBLIC_HOST = "https://prosodic-reflectively-golden.ngrok-free.dev"  # e.g., "https://abc123.ngrok.io"
WELCOME_GREETING = "Hi! I'm your AI host. Lets make money and fuck some bitches I can take reservations and orders. How can I help?"
# ----------------------------------------------------------------------

app = FastAPI()

# --- Helpers -----------------------------------------------------------

def build_twiml_conversationrelay(ws_url: str, welcome: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
    <Connect>
    <ConversationRelay url="{ws_url}" welcomeGreeting="{welcome}"/>
    </Connect>
    </Response>"""

def respond_to_prompt(text: str) -> str:
    lower = text.strip().lower()
    if any(word in lower for word in ["reservation", "book", "table"]):
        return (
            "Absolutely. For a reservation, please tell me the date, time, "
            "number of guests, and your name."
        )
    if any(word in lower for word in ["order", "pickup", "deliver", "delivery", "takeout"]):
        return (
            "Sure — what would you like to order? You can say something like: "
            "two margherita pizzas and one Caesar salad."
        )
    if any(word in lower for word in ["hello", "hi", "hey"]):
        return "Hi! I can take reservations and phone orders. What would you like to do?"
    if "help" in lower:
        return "You can say 'make a reservation' or 'place an order' to get started."
    return "Got it. Tell me if this is for a reservation or an order."

# --- HTTP: TwiML webhook ----------------------------------------------

@app.post("/voice")
async def voice_webhook(request: Request) -> Response:
    if not (PUBLIC_HOST.startswith("https://") or PUBLIC_HOST.startswith("http://")):
        return PlainTextResponse(
            "Server misconfigured: set PUBLIC_HOST to a public https base URL.", status_code=500
        )
    ws_url = PUBLIC_HOST.replace("http://", "wss://").replace("https://", "wss://") + "/ws"
    twiml = build_twiml_conversationrelay(ws_url, WELCOME_GREETING)
    return Response(content=twiml, media_type="application/xml")

# --- WebSocket: ConversationRelay -------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "setup":
                # Twilio connected; you can inspect metadata if needed.
                pass

            elif mtype == "prompt":
                # Caller said something; Twilio provides STT as voicePrompt.
                user_text = msg.get("voicePrompt", "")
                reply = respond_to_prompt(user_text)

                await ws.send_text(json.dumps({
                    "type": "text",
                    "token": reply,
                    "last": True
                }))

            elif mtype == "interrupt":
                # Caller barge-in. In a real app, cancel any running LLM task.
                pass

            elif mtype == "dtmf":
                digit = msg.get("digit")
                await ws.send_text(json.dumps({
                    "type": "text",
                    "token": f"You pressed {digit}. Say 'reservation' or 'order' to continue.",
                    "last": True
                }))

            elif mtype == "error":
                # Twilio reports an error. Log and decide whether to close.
                print("Twilio error:", msg)

            else:
                # Unknown type; helpful during development.
                print("Unknown message:", msg)

    except WebSocketDisconnect:
        # Call ended / socket closed.
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({
                "type": "text",
                "token": "Sorry, something went wrong. Please call back later.",
                "last": True
            }))
        except Exception:
            pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
