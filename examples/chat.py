from nebula import Nebula
from pathlib import Path

app = Nebula(__name__, "127.0.0.1", 5000, debug=True)

# Указываем правильный путь к шаблонам
template_dir = Path(__file__).parent / "templates"
app.init_all(template_dir=str(template_dir))

# Хранилище сообщений и подключенных клиентов
messages = []
clients = {}


@app.route("/")
def index():
    return app.render_template("chat.html")


@app.on_connect()
def handle_connect(sid, environ):
    print(f"Client connected: {sid}")
    clients[sid] = environ
    return {"status": "connected", "messages": messages[-50:]}  # Последние 50 сообщений


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

        # Отправляем сообщение всем подключенным клиентам (включая отправителя)
        app.sio.emit("new_message", msg_data)


if __name__ == "__main__":
    app.run()
