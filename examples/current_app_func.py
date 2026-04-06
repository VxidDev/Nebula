from nebula import current_app

@current_app.get("/")
def home():
    return "<h1>Welcome to Nebula!</h1>"