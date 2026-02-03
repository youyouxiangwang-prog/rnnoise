import asyncio
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

APP = FastAPI(title="rnnoise-http")

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))
RNNOISE_BIN = os.getenv("RNNOISE_BIN", "rnnoise_wrapper_demo")
DEFAULT_MODEL = os.getenv("RNNOISE_MODEL", "/opt/rnnoise/models/weights_blob.bin")

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)


def _run_rnnoise(input_path: str, output_path: str, model_path: Optional[str]) -> None:
    args = [RNNOISE_BIN, input_path, output_path]
    if model_path:
        args.append(model_path)
    result = os.spawnvp(os.P_WAIT, args[0], args)
    if result != 0:
        raise RuntimeError(f"rnnoise failed with code {result}")


@APP.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@APP.post("/denoise")
async def denoise(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")
    if "application/octet-stream" not in content_type:
        raise HTTPException(status_code=415, detail="Use application/octet-stream")

    model_param = request.query_params.get("model")
    model_path = model_param if model_param else (DEFAULT_MODEL if os.path.exists(DEFAULT_MODEL) else None)

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    async with _semaphore:
        loop = asyncio.get_running_loop()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.pcm")
            output_path = os.path.join(temp_dir, "output.pcm")
            with open(input_path, "wb") as input_file:
                input_file.write(body)

            try:
                await loop.run_in_executor(None, _run_rnnoise, input_path, output_path, model_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            with open(output_path, "rb") as output_file:
                output_bytes = output_file.read()

    return Response(content=output_bytes, media_type="application/octet-stream")
