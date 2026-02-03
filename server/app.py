import asyncio
import os
import tempfile
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

APP = FastAPI(title="rnnoise-http")

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))
RNNOISE_BIN = os.getenv("RNNOISE_BIN", "/opt/rnnoise/bin/rnnoise_wrapper_demo")
DEFAULT_MODEL = os.getenv("RNNOISE_MODEL", "/opt/rnnoise/models/weights_blob.bin")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
_active_requests = 0
_s3_client = boto3.client("s3", region_name=AWS_REGION)


class DenoiseRequest(BaseModel):
    input_s3_uri: str
    output_s3_uri: str
    model_s3_uri: Optional[str] = None


def _parse_s3_uri(s3_uri: str) -> tuple:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    parts = s3_uri[5:].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")
    return parts[0], parts[1]


def _run_rnnoise(input_path: str, output_path: str, model_path: Optional[str]) -> None:
    args = [RNNOISE_BIN, input_path, output_path]
    if model_path:
        args.append(model_path)
    result = os.spawnvp(os.P_WAIT, args[0], args)
    if result != 0:
        raise RuntimeError(f"rnnoise failed with code {result}")


@APP.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "active_requests": _active_requests,
        "max_concurrency": MAX_CONCURRENCY,
    }


@APP.post("/denoise")
async def denoise_direct(request: Request) -> Response:
    """Direct binary upload/download (legacy support)"""
    global _active_requests
    
    if _active_requests >= MAX_CONCURRENCY:
        raise HTTPException(
            status_code=503,
            detail=f"Service busy: {_active_requests}/{MAX_CONCURRENCY} slots in use"
        )
    
    content_type = request.headers.get("content-type", "")
    if "application/octet-stream" not in content_type:
        raise HTTPException(status_code=415, detail="Use application/octet-stream")

    model_param = request.query_params.get("model")
    model_path = model_param if model_param else (DEFAULT_MODEL if os.path.exists(DEFAULT_MODEL) else None)

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    async with _semaphore:
        _active_requests += 1
        try:
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
        finally:
            _active_requests -= 1


@APP.post("/denoise/s3")
async def denoise_s3(req: DenoiseRequest) -> dict:
    """S3-based denoise: read from S3, process, write back to S3"""
    global _active_requests
    
    if _active_requests >= MAX_CONCURRENCY:
        raise HTTPException(
            status_code=503,
            detail=f"Service busy: {_active_requests}/{MAX_CONCURRENCY} slots in use"
        )
    
    try:
        input_bucket, input_key = _parse_s3_uri(req.input_s3_uri)
        output_bucket, output_key = _parse_s3_uri(req.output_s3_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with _semaphore:
        _active_requests += 1
        try:
            loop = asyncio.get_running_loop()
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, "input.pcm")
                output_path = os.path.join(temp_dir, "output.pcm")
                model_path = None

                try:
                    await loop.run_in_executor(
                        None, _s3_client.download_file, input_bucket, input_key, input_path
                    )

                    if req.model_s3_uri:
                        model_bucket, model_key = _parse_s3_uri(req.model_s3_uri)
                        model_path = os.path.join(temp_dir, "model.bin")
                        await loop.run_in_executor(
                            None, _s3_client.download_file, model_bucket, model_key, model_path
                        )
                    elif os.path.exists(DEFAULT_MODEL):
                        model_path = DEFAULT_MODEL

                    await loop.run_in_executor(None, _run_rnnoise, input_path, output_path, model_path)

                    await loop.run_in_executor(
                        None, _s3_client.upload_file, output_path, output_bucket, output_key
                    )

                except ClientError as exc:
                    raise HTTPException(status_code=500, detail=f"S3 error: {exc}") from exc
                except Exception as exc:
                    raise HTTPException(status_code=500, detail=str(exc)) from exc

            return {
                "status": "success",
                "input": req.input_s3_uri,
                "output": req.output_s3_uri,
            }
        finally:
            _active_requests -= 1
