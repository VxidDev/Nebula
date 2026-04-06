from nebula import Nebula

app = Nebula()
app.make_current()

import current_app_func # after app.make_current()

if __name__ == "__main__":
    app.run()