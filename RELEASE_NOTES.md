# Nebula v1.0.0 Release Notes

This release marks a major milestone for Nebula, as we've completed the migration to Werkzeug for core functionalities. This change brings significant improvements in performance, stability, and standardization.

## Breaking Changes

This release introduces several breaking changes. Please review them carefully before upgrading.

### 1. Migration to Werkzeug's Request and Response Objects

The custom `nebula.core.Request` and `nebula.core.Response` classes have been removed in favor of Werkzeug's native `werkzeug.wrappers.Request` and `werkzeug.wrappers.Response` objects. This means you'll need to update your code to use the new objects.

**Old Code:**

```python
from nebula import Nebula, Response

app = Nebula("localhost", 8000)

@app.route("/")
def index():
    return Response("<h1>Hello, World!</h1>", 200)
```

**New Code:**

```python
from werkzeug.wrappers import Response
from nebula import Nebula

app = Nebula("localhost", 8000)

@app.route("/")
def index(request):
    return Response("<h1>Hello, World!</h1>", 200)
```

### 2. View Function Signatures

View functions now receive the `werkzeug.wrappers.Request` object as the first argument. Any URL parameters are passed as keyword arguments.

### 3. Removal of `app.request`

The `app.request` attribute is no longer available. You should access the request object directly in your view functions.

**Old Code:**

```python
@app.route("/")
def index():
    if app.request.method == "POST":
        # ...
```

**New Code:**

```python
@app.route("/")
def index(request):
    if request.method == "POST":
        # ...
```

### 4. Removal of `before_request` and `after_request` Hooks

The `before_request` and `after_request` hooks have been temporarily removed. We are working on a new implementation for these hooks and they will be re-introduced in a future release.

## New Features

*   **Improved Performance and Stability:** By leveraging Werkzeug's battle-tested components, Nebula is now faster and more reliable than ever.
*   **Standardization:** Adopting Werkzeug's interfaces makes Nebula more compliant with WSGI standards and easier to integrate with other tools in the Python web ecosystem.

## Upgrade Instructions

1.  **Update your view function signatures:** Add `request` as the first argument to all your view functions.
2.  **Replace `Response` objects:** Replace all instances of `nebula.Response` with `werkzeug.wrappers.Response`.
3.  **Remove `app.request`:** Update your code to use the `request` object passed to your view functions instead of `app.request`.
4.  **Remove `before_request` and `after_request` hooks:** Remove any `before_request` and `after_request` decorators from your code.
