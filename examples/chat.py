from nebula import Nebula
from pathlib import Path

app = Nebula(__file__, "0.0.0.0", 5000, debug=True)
app.init_all()

# Storage for messages and connected clients
messages = []
clients = {}


@app.route("/")
def index():
    return app.render_template("chat.html")


@app.on_connect()
def handle_connect(sid, environ):
    print(f"Client connected: {sid}")
    clients[sid] = environ
    return {"status": "connected", "messages": messages[-50:]}  # Last 50 messages


@app.on_disconnect()
def handle_disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in clients:
        del clients[sid]


@app.on_event("message")
def handle_message(sid, data):
    username = data.get("username", "Аноним")
    message = data.get("message", "")

    if message:
        msg_data = {"username": username, "message": message}
        messages.append(msg_data)
        if len(messages) > 100:
            messages.pop(0)

        # Send message to all connected clients (including sender)
        app.sio.emit("new_message", msg_data)

wsgi = app.wsgi_app

if __name__ == "__main__":
    app.run()
