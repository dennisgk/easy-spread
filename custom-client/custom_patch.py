import asyncio
import pyodide
from js import globalThis, console, fetch
import sys
import json
from pathlib import Path
import base64

# request ID system
_next_id = 1
_pending = {}

VIRTUAL_ROOT = "/custom_pkgs"

def _on_message(event):
    try:
        data = event.data.to_py()
        request_id = data.get("request_id")

        if request_id in _pending:
            fut = _pending.pop(request_id)
            fut.set_result(data)
    except Exception as e:
        console.log(f"Error in _on_message: {e}")

# connect worker events

async def post_and_wait(message: dict):
    global _next_id

    request_id = _next_id
    _next_id += 1

    message = message.copy()
    message["request_id"] = request_id

    fut = asyncio.get_event_loop().create_future()
    _pending[request_id] = fut

    try:
        js_msg = pyodide.ffi.to_js(message, dict_converter=globalThis.Object.fromEntries)
        globalThis.postMessage(js_msg)
    except Exception as e:
        console.log(f"[Worker] postMessage failed: {e}")

    result = await fut
    return result

async def get_ory_token():
    res = await post_and_wait({ "type": "ory_tmp_auth_header" })
    token = res.get("value")
    return token

async def get_data(token):
    response = await fetch("https://quadraticapi.kountouris.org/v0/customCode", pyodide.ffi.to_js({
        "method": "GET",
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }, dict_converter=globalThis.Object.fromEntries))
    
    data = await response.json()
    return data.to_py()

def _ensure_virtual_root():
    """Create /custom_pkgs and add it to sys.path if needed."""
    root = Path(VIRTUAL_ROOT)

    # Create directory if missing
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)

    # Ensure Python can import from it
    if VIRTUAL_ROOT not in sys.path:
        sys.path.append(VIRTUAL_ROOT)


def install_virtual_package(files: dict[str, str]):
    """
    files: mapping of relative paths (e.g. 'my_pkg/__init__.py')
           to Python source code strings.
    """
    _ensure_virtual_root()

    for relpath, src in files.items():
        abs_path = Path(VIRTUAL_ROOT) / relpath

        # Make parent directories
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file content
        abs_path.write_text(base64.b64decode(src).decode("utf-8"), encoding="utf-8")

async def apply_custom_patch():
    if VIRTUAL_ROOT in sys.path:
        return

    listener = pyodide.ffi.create_proxy(_on_message)
    globalThis.addEventListener("message", listener)
    token = await get_ory_token()
    globalThis.removeEventListener("message", listener)
    if(isinstance(token, str) and token):
        data = await get_data(token)
        console.log(json.dumps(data))

        _ensure_virtual_root()
        install_virtual_package(data["code"])

