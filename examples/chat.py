from nebula import Nebula
from nebula.request import Request

app = Nebula("0.0.0.0", 5000, debug=True)
app.init_all()

# Storage for messages and connected clients
messages = []
clients = {}

@app.get("/")
async def index():
    return await app.render_template_async("chat.html")

@app.on_connect()
async def handle_connect(sid, *args, **kwargs):
    print(f"Client connected: {sid}")
    clients[sid] = {} # Store client info if needed
    # The return value is not directly sent as HTTP response in ASGI,
    # but the client can receive initial messages via emit.
    await app.sio.emit("initial_messages", messages[-50:], to=sid)

@app.on_disconnect()
async def handle_disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in clients:
        del clients[sid]

@app.on_event("message")
async def handle_message(sid, data):
    username = data.get("username", "Anonymous")
    message = data.get("message", "")

    if message:
        msg_data = {"username": username, "message": message}
        messages.append(msg_data)
        if len(messages) > 100:
            messages.pop(0)

        await app.sio.emit("new_message", msg_data)

if __name__ == "__main__":
    app.run()
