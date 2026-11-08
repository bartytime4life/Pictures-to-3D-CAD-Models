"""Same-origin local development API; no third-party reconstruction services."""

import asyncio
import json
import os
import re
import shutil
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from .models import BuildRequest, Detail
from .tracing import MAX_BYTES, TraceError, trace_image

ROOT = Path(__file__).resolve().parent.parent
JOB_ROOT = Path(os.environ.get("PICTURES_CAD_JOB_DIR", ROOT / ".local" / "jobs")).resolve()
TTL_SECONDS = 3600
MAX_JOBS = 20
BUILD_TIMEOUT = 60
DOWNLOADS = {
    "step": ("model.step", "application/step"),
    "stl": ("model.stl", "model/stl"),
    "dxf": ("profile.dxf", "application/dxf"),
    "project": ("project.json", "application/json"),
}
UUID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def cleanup_jobs():
    JOB_ROOT.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for path in JOB_ROOT.iterdir():
        if (
            UUID_PATTERN.fullmatch(path.name)
            and path.is_dir()
            and now - path.stat().st_mtime >= TTL_SECONDS
        ):
            shutil.rmtree(path)


@asynccontextmanager
async def lifespan(app):
    cleanup_jobs()
    app.state.cad_lock = asyncio.Lock()
    app.state.trace_lock = asyncio.Lock()

    async def expire_jobs():
        while True:
            await asyncio.sleep(60)
            cleanup_jobs()

    reaper = asyncio.create_task(expire_jobs())
    try:
        yield
    finally:
        reaper.cancel()
        try:
            await reaper
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Pictures to CAD", version="0.1.0", lifespan=lifespan)


class BodyTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, "Upload exceeds the 10 MiB limit.")


class BodyLimitMiddleware:
    """Bound multipart parsing as well as the decoded upload checked in tracing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = MAX_BYTES + 64 * 1024
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length:
            try:
                too_large = int(length) > limit or int(length) < 0
            except ValueError:
                too_large = True
            if too_large:
                return await JSONResponse({"detail": "Upload exceeds the 10 MiB limit."}, 413)(
                    scope, receive, send
                )
        count = 0

        async def bounded_receive():
            nonlocal count
            message = await receive()
            count += len(message.get("body", b""))
            if count > limit:
                raise BodyTooLarge()
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            await JSONResponse({"detail": "Upload exceeds the 10 MiB limit."}, 413)(
                scope, receive, send
            )


app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    messages = []
    for error in exc.errors()[:3]:
        field = ".".join(str(v) for v in error["loc"] if v != "body")
        messages.append(f"{field}: {error['msg']}")
    return JSONResponse({"detail": "; ".join(messages)}, status_code=422)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "workflow": "measured-profile-extrusion"}


@app.post("/api/trace")
async def trace(
    file: Annotated[UploadFile, File()],
    threshold: Annotated[int, Form()] = -1,
    inverted: Annotated[bool, Form()] = False,
    detail: Annotated[Detail, Form()] = "standard",
):
    lock = app.state.trace_lock
    if lock.locked():
        await file.close()
        raise HTTPException(
            429,
            "Another photo is being traced. Wait a moment and try again.",
            headers={"Retry-After": "3"},
        )
    async with lock:
        try:
            data = await file.read(MAX_BYTES + 1)
        finally:
            await file.close()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Choose an image under 10 MiB.")
        # A cancelled request cannot terminate a native decode thread. Keep its
        # concurrency slot until the actual operation finishes, including repeated
        # cancellation; otherwise reconnecting clients could start unbounded work.
        worker = asyncio.create_task(
            asyncio.to_thread(trace_image, data, threshold, inverted, detail)
        )
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except TraceError:
                    break
            if not worker.cancelled():
                worker.exception()  # Consume a completed error before preserving cancellation.
            raise
        except TraceError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/api/build")
async def build(request: BuildRequest):
    lock = app.state.cad_lock
    if lock.locked():
        raise HTTPException(
            429,
            "Another model is being built. Wait a moment and try again.",
            headers={"Retry-After": "3"},
        )
    async with lock:
        cleanup_jobs()
        jobs = [p for p in JOB_ROOT.iterdir() if UUID_PATTERN.fullmatch(p.name) and p.is_dir()]
        if len(jobs) >= MAX_JOBS:
            # Capacity is bounded; prior downloads stay valid until their TTL instead of disappearing silently.
            raise HTTPException(
                429,
                "Temporary model storage is full. Delete older models or wait for expiry, then try again.",
                headers={"Retry-After": "60"},
            )
        job_id = uuid.uuid4().hex
        job_dir = JOB_ROOT / job_id
        job_dir.mkdir(mode=0o700)
        (job_dir / "input.json").write_text(request.model_dump_json())
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "backend.worker",
                str(job_dir),
                cwd=ROOT,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(process.wait(), timeout=BUILD_TIMEOUT)
            except TimeoutError as exc:
                process.kill()
                await process.wait()
                raise HTTPException(
                    504, "CAD generation exceeded 60 seconds. Reduce outline detail and try again."
                ) from exc
            if process.returncode != 0 or not (job_dir / "result.json").is_file():
                raise HTTPException(
                    422,
                    "This outline could not be converted to a solid. Reduce detail or remove very narrow features and try again.",
                )
            result = json.loads((job_dir / "result.json").read_text())
            (job_dir / "input.json").unlink(missing_ok=True)
            return result
        except BaseException:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            shutil.rmtree(job_dir, ignore_errors=True)
            raise


def resolve_job(job_id: str):
    if not UUID_PATTERN.fullmatch(job_id):
        raise HTTPException(404, "Model not found. Rebuild it to create new exports.")
    directory = JOB_ROOT / job_id
    if not directory.is_dir() or not (directory / "result.json").is_file():
        raise HTTPException(404, "Model not found. Rebuild it to create new exports.")
    if time.time() - directory.stat().st_mtime >= TTL_SECONDS:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(410, "This model has expired. Rebuild it to create fresh exports.")
    return directory


@app.get("/api/download/{job_id}/{kind}")
async def download(job_id: str, kind: str):
    if kind not in DOWNLOADS:
        raise HTTPException(404, "Export format not found.")
    directory = resolve_job(job_id)
    name, media_type = DOWNLOADS[kind]
    return FileResponse(
        directory / name,
        media_type=media_type,
        filename=name,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.delete("/api/models/{job_id}", status_code=204)
async def delete_model(job_id: str):
    directory = resolve_job(job_id)
    shutil.rmtree(directory)


@app.delete("/api/models")
async def clear_models():
    lock = app.state.cad_lock
    if lock.locked():
        raise HTTPException(
            409, "A model is being built. Wait for it to finish before clearing exports."
        )
    async with lock:
        deleted = 0
        for directory in JOB_ROOT.iterdir():
            if (
                UUID_PATTERN.fullmatch(directory.name)
                and directory.is_dir()
                and (directory / "result.json").is_file()
            ):
                shutil.rmtree(directory)
                deleted += 1
        return {"deleted": deleted}


@app.get("/{path:path}")
async def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "API route not found.")
    dist = (ROOT / "frontend" / "dist").resolve()
    target = (dist / path).resolve()
    if not target.is_relative_to(dist):
        raise HTTPException(404, "File not found.")
    if target.is_file():
        return FileResponse(target)
    if path:
        raise HTTPException(404, "File not found.")
    if (dist / "index.html").is_file():
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
    raise HTTPException(
        404, "Frontend not built. Run npm run build, or use the Vite development server."
    )
