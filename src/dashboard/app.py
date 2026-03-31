"""FastAPI web dashboard for message-to-iaac."""

import os
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import httpx
import hashlib
import secrets

load_dotenv()

from ..config import (
    PipelineConfig,
    SUPPORTED_CLOUDS,
    SUPPORTED_IAC_TOOLS,
    SUPPORTED_PROVIDERS,
    DEFAULT_REGIONS,
    DEFAULT_MODELS,
    DEFAULT_OLLAMA_URL,
    CLOUD_SERVICE_MAP,
)
from ..engine import PipelineEngine

BASE_DIR = Path(__file__).parent
app = FastAPI(title="IaCraft", version="2.0.0")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---- Auth System ----
# Default users (stored in .env or defaults)
USERS = {
    "admin": os.getenv("ADMIN_PASSWORD", "admin123"),
    "guest": "guest",
}
# Active sessions
_sessions = {}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _check_session(request: Request) -> bool:
    token = request.cookies.get("session_token")
    return token in _sessions

# Global state for pipeline progress (with lock for thread safety)
_state_lock = threading.Lock()
pipeline_state = {
    "running": False,
    "logs": [],
    "step": 0,
    "status": "idle",
    "results": None,
    "error": None,
}


def reset_state():
    with _state_lock:
        pipeline_state["running"] = False
        pipeline_state["logs"] = []
        pipeline_state["step"] = 0
        pipeline_state["status"] = "idle"
        pipeline_state["results"] = None
        pipeline_state["error"] = None


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login or dashboard."""
    if _check_session(request):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    if _check_session(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/login")
async def login(request: Request):
    """Authenticate user."""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    remember = body.get("remember", False)

    if username in USERS and USERS[username] == password:
        token = secrets.token_hex(32)
        _sessions[token] = {"user": username}
        response = JSONResponse({"success": True, "user": username})
        max_age = 30 * 24 * 3600 if remember else None  # 30 days or session
        response.set_cookie("session_token", token, max_age=max_age, httponly=True, samesite="lax")
        return response
    return JSONResponse({"success": False, "error": "Invalid username or password"})


@app.get("/api/logout")
async def logout(request: Request):
    """Logout and clear session."""
    token = request.cookies.get("session_token")
    if token in _sessions:
        del _sessions[token]
    response = RedirectResponse("/login")
    response.delete_cookie("session_token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard (protected)."""
    if not _check_session(request):
        return RedirectResponse("/login")
    provider_names = {
        "groq": "Groq", "gemini": "Gemini", "openai": "OpenAI",
        "claude": "Claude", "bedrock": "AWS Bedrock", "azure_openai": "Azure OpenAI",
        "mistral": "Mistral", "deepseek": "DeepSeek", "cohere": "Cohere",
        "together": "Together AI", "ollama": "Ollama",
    }
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "clouds": SUPPORTED_CLOUDS,
        "iac_tools": SUPPORTED_IAC_TOOLS,
        "providers": SUPPORTED_PROVIDERS,
        "provider_names": provider_names,
        "default_regions": DEFAULT_REGIONS,
        "default_models": DEFAULT_MODELS,
        "default_ollama_url": DEFAULT_OLLAMA_URL,
    })


@app.post("/api/save-key")
async def save_key(request: Request):
    """Save an API key to .env file and set in environment."""
    body = await request.json()
    key_name = body.get("key_name", "").strip()
    key_value = body.get("key_value", "").strip()

    if not key_name or not key_value:
        return JSONResponse({"error": "key_name and key_value required"}, status_code=400)

    # Set in current process environment
    os.environ[key_name] = key_value

    # Save to .env file
    env_path = Path(".env")
    lines = []
    found = False
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{key_name}="):
                lines.append(f"{key_name}={key_value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key_name}={key_value}")

    env_path.write_text("\n".join(lines) + "\n")
    return {"status": "saved", "key": key_name}


@app.get("/api/keys")
async def get_keys():
    """Get which API keys are configured (without revealing values)."""
    from ..llm_client import PROVIDER_ENV_KEYS
    result = {}
    for provider, env_key in PROVIDER_ENV_KEYS.items():
        if env_key is None:
            result[provider] = {"configured": True, "env_key": None}
        else:
            val = os.getenv(env_key, "")
            result[provider] = {
                "configured": bool(val),
                "env_key": env_key,
                "masked": val[:8] + "..." if len(val) > 8 else ("set" if val else ""),
            }
    return result


@app.get("/api/ollama/status")
async def ollama_status(url: str = None):
    """Check if Ollama is reachable and list available models."""
    ollama_url = url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    try:
        # BUG FIX #1 #3: Use separate timeouts — short for ping, longer for tags
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ollama_url}/", timeout=5.0)
            if resp.status_code == 200:
                try:
                    tags = await client.get(f"{ollama_url}/api/tags", timeout=30.0)
                    models = [m["name"] for m in tags.json().get("models", [])]
                    return {"status": "connected", "url": ollama_url, "models": models}
                except Exception:
                    # BUG FIX #7: Ollama is reachable but tags failed
                    return {"status": "connected", "url": ollama_url, "models": [], "message": "Connected but could not load model list"}
            return {"status": "error", "message": f"Status {resp.status_code}"}
    except Exception as e:
        return {"status": "disconnected", "url": ollama_url, "message": str(e), "models": []}


@app.get("/api/ollama/pull")
async def ollama_pull_model(model: str, url: str = None):
    """Pull a model from Ollama."""
    ollama_url = url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{ollama_url}/api/pull", json={"name": model, "stream": False})
            return {"status": "success", "model": model}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/generate")
async def generate(request: Request):
    """Start the IaC generation pipeline."""
    if pipeline_state["running"]:
        return JSONResponse({"error": "Pipeline already running"}, status_code=409)

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    reset_state()
    with _state_lock:
        pipeline_state["running"] = True
        pipeline_state["status"] = "starting"

    def status_callback(step: int, msg: str):
        with _state_lock:
            pipeline_state["step"] = step
            pipeline_state["status"] = msg
            pipeline_state["logs"].append({"step": step, "message": msg})

    def run_pipeline():
        try:
            config = PipelineConfig(
                user_message=message,
                cloud=body.get("cloud", "aws"),
                iac_tool=body.get("iac_tool", "terraform"),
                region=body.get("region") or None,
                output_dir=body.get("output_dir", "output"),
                provider=body.get("provider", "ollama"),
                model=body.get("model") or None,
                ollama_url=body.get("ollama_url") or None,
                doc_level=body.get("doc_level", "standard"),
            )
            engine = PipelineEngine(config, on_status=status_callback)
            results = engine.run()
            # BUG FIX #4: Set all state BEFORE setting running=False
            with _state_lock:
                pipeline_state["results"] = {
                    "analysis": results.get("analysis", {}),
                    "architecture": results.get("architecture", {}),
                    "mapping": results.get("mapping", {}),
                    "diagram": results.get("diagram", ""),
                    "security": results.get("security", ""),
                    "compliance": results.get("compliance", ""),
                    "cost": results.get("cost", ""),
                    "validation": results.get("validation", ""),
                    "autofix": results.get("autofix", ""),
                    "deployment_guide": results.get("deployment_guide", ""),
                    "iac_files": [str(f) for f in results.get("iac_files", [])],
                }
                pipeline_state["status"] = "complete"
                pipeline_state["running"] = False  # Last!
        except Exception as e:
            with _state_lock:
                pipeline_state["error"] = str(e)
                pipeline_state["status"] = "error"
                pipeline_state["running"] = False  # Last!

    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()

    return {"status": "started"}


@app.get("/api/progress")
async def progress():
    """SSE endpoint for real-time pipeline progress."""
    async def event_stream():
        # BUG FIX #6: Wrap entire stream in try/except
        try:
            last_count = 0
            while True:
                with _state_lock:
                    logs = list(pipeline_state["logs"])
                    running = pipeline_state["running"]
                    error = pipeline_state["error"]

                if len(logs) > last_count:
                    for log in logs[last_count:]:
                        data = json.dumps(log)
                        yield f"data: {data}\n\n"
                    last_count = len(logs)

                if not running:
                    if error:
                        yield f"data: {json.dumps({'step': -1, 'message': error, 'type': 'error'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'step': 12, 'message': 'Pipeline complete!', 'type': 'done'})}\n\n"
                    break

                await asyncio.sleep(0.5)
        except Exception as e:
            yield f"data: {json.dumps({'step': -1, 'message': f'Stream error: {str(e)}', 'type': 'error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/results")
async def results():
    """Get pipeline results."""
    with _state_lock:
        if pipeline_state["running"]:
            return {"status": "running", "step": pipeline_state["step"]}
        if pipeline_state["error"]:
            return {"status": "error", "error": pipeline_state["error"]}
        if pipeline_state["results"]:
            return {"status": "complete", "results": pipeline_state["results"]}
    return {"status": "idle"}


# Simulator state
simulator_state = {
    "running": False,
    "logs": [],
    "report": None,
    "error": None,
}


@app.post("/api/simulate")
async def simulate(request: Request):
    """Run the code simulator: validate → fix → re-validate loop."""
    if simulator_state["running"]:
        return JSONResponse({"error": "Simulator already running"}, status_code=409)

    body = await request.json()
    terraform_dir = os.path.abspath(os.path.join(body.get("output_dir", "output"), "terraform"))

    if not os.path.exists(terraform_dir):
        return JSONResponse({"error": "No terraform files found. Generate IaC first."}, status_code=400)

    simulator_state["running"] = True
    simulator_state["logs"] = []
    simulator_state["report"] = None
    simulator_state["error"] = None

    provider = body.get("provider", "groq")
    model = body.get("model")
    ollama_url = body.get("ollama_url")

    def sim_status(msg):
        simulator_state["logs"].append(msg)

    def run_sim():
        try:
            from ..llm_client import LLMClient
            from ..file_writer import FileWriter
            from ..validator import CodeSimulator

            llm = LLMClient(provider=provider, model=model, ollama_url=ollama_url)
            writer = FileWriter(body.get("output_dir", "output"))
            sim = CodeSimulator(terraform_dir, llm, writer, on_status=sim_status)
            report = sim.run()
            simulator_state["report"] = {
                "rounds": report.rounds,
                "final_passed": report.final_passed,
                "total_errors_found": report.total_errors_found,
                "total_errors_fixed": report.total_errors_fixed,
                "summary": report.summary,
            }
        except Exception as e:
            simulator_state["error"] = str(e)
        finally:
            simulator_state["running"] = False

    thread = threading.Thread(target=run_sim, daemon=True)
    thread.start()
    return {"status": "started"}


@app.get("/api/simulate/status")
async def simulate_status():
    """Get simulator progress."""
    return {
        "running": simulator_state["running"],
        "logs": simulator_state["logs"],
        "report": simulator_state["report"],
        "error": simulator_state["error"],
    }


# Multi-cloud comparison state
compare_state = {
    "running": False,
    "logs": [],
    "report": None,
    "error": None,
}


@app.post("/api/compare")
async def compare(request: Request):
    """Run multi-cloud comparison: AWS vs Azure vs GCP."""
    if compare_state["running"]:
        return JSONResponse({"error": "Comparison already running"}, status_code=409)

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    compare_state["running"] = True
    compare_state["logs"] = []
    compare_state["report"] = None
    compare_state["error"] = None

    def compare_status(cloud, msg):
        compare_state["logs"].append({"cloud": cloud, "message": msg})

    def run_compare():
        try:
            from ..multi_cloud import MultiCloudEngine

            engine = MultiCloudEngine(
                user_message=message,
                iac_tool=body.get("iac_tool", "terraform"),
                provider=body.get("provider", "groq"),
                model=body.get("model"),
                ollama_url=body.get("ollama_url"),
                output_dir=body.get("output_dir", "output"),
                on_status=compare_status,
            )
            report = engine.run()

            clouds_data = {}
            for cloud, result in report.clouds.items():
                clouds_data[cloud] = {
                    "status": result.status,
                    "time": result.time_taken,
                    "services": [m.get("service", "") for m in result.mapping.get("mappings", [])],
                    "files": result.iac_files,
                    "cost": result.cost[:1000] if result.cost else "",
                    "diagram": result.diagram[:1000] if result.diagram else "",
                    "error": result.error_msg,
                }

            compare_state["report"] = {
                "clouds": clouds_data,
                "comparison": report.comparison_table,
                "recommendation": report.recommendation,
                "total_time": report.total_time,
            }
        except Exception as e:
            compare_state["error"] = str(e)
        finally:
            compare_state["running"] = False

    thread = threading.Thread(target=run_compare, daemon=True)
    thread.start()
    return {"status": "started"}


@app.get("/api/compare/status")
async def compare_status_endpoint():
    """Get multi-cloud comparison progress."""
    return {
        "running": compare_state["running"],
        "logs": compare_state["logs"],
        "report": compare_state["report"],
        "error": compare_state["error"],
    }


@app.get("/api/files/{path:path}")
async def read_file(path: str):
    """Read a generated output file."""
    filepath = Path("output") / path
    if filepath.exists() and filepath.is_file():
        return {"content": filepath.read_text(encoding="utf-8"), "path": str(filepath)}
    return JSONResponse({"error": "File not found"}, status_code=404)


@app.get("/api/download")
async def download_all():
    """Download all generated files as a zip."""
    import zipfile
    import io
    from fastapi.responses import Response

    output_dir = Path("output")
    if not output_dir.exists():
        return JSONResponse({"error": "No output files"}, status_code=404)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath in output_dir.rglob("*"):
            if filepath.is_file():
                zf.write(filepath, filepath.relative_to(output_dir))

    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=message-to-iaac-output.zip"},
    )
