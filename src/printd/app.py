"""FastAPI application factory."""

from __future__ import annotations

import base64
import io
import logging

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from . import escpos_session
from .auth import make_auth_dependency
from .config import Settings, load_settings
from .connectors import Connector, make_connector
from .models import (
    CutRequest,
    FeedRequest,
    HealthResponse,
    OkResponse,
    PrintJsonRequest,
    PrintResponse,
    RawPrintRequest,
    RawResponse,
    StatusResponse,
)

log = logging.getLogger("printd")


def _decode_image(raw: str | bytes, max_bytes: int) -> Image.Image:
    if isinstance(raw, str):
        s = raw
        if s.startswith("data:"):
            _, _, s = s.partition(",")
        try:
            data = base64.b64decode(s, validate=False)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 image: {e}",
            ) from e
    else:
        data = raw

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds {max_bytes} bytes",
        )
    try:
        return Image.open(io.BytesIO(data))
    except UnidentifiedImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode image bytes",
        ) from e


def create_app(settings: Settings | None = None, connector: Connector | None = None) -> FastAPI:
    cfg = settings or load_settings()
    conn = connector or make_connector(cfg)

    if not cfg.api_key:
        log.warning("PRINTD_API_KEY is unset — running in dev mode with no auth!")

    app = FastAPI(
        title="printd",
        version="0.1.0",
        summary="HTTP API for ESC/POS thermal receipt printers.",
        description=(
            "USB, network, and serial ESC/POS printers behind a clean REST API. "
            "Send a PNG, get a receipt. See https://github.com/HansF/printd."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = cfg
    app.state.connector = conn
    app.state.last_error = None

    require_bearer = make_auth_dependency(cfg)
    auth = APIRouter(dependencies=[Depends(require_bearer)])

    def _capture(exc: Exception) -> None:
        app.state.last_error = f"{type(exc).__name__}: {exc}"

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse(ok=True, printer="online", kind=conn.kind, target=conn.target)

    @auth.get("/status", response_model=StatusResponse)
    def status_() -> StatusResponse:
        return StatusResponse(
            ok=True,
            kind=conn.kind,
            target=conn.target,
            last_error=app.state.last_error,
            print_width=cfg.print_width,
            bottom_pad_rows=cfg.bottom_pad_rows,
            feed_before_cut=cfg.feed_before_cut,
        )

    @auth.post("/print", response_model=PrintResponse)
    def print_json(req: PrintJsonRequest) -> PrintResponse:
        img = _decode_image(req.image, cfg.max_image_bytes)
        try:
            w, h = escpos_session.print_image(
                conn,
                img,
                print_width=cfg.print_width,
                pad_rows=cfg.bottom_pad_rows,
                cut=req.cut,
                feed_before_cut=req.feed if req.feed is not None else cfg.feed_before_cut,
                partial_cut=req.partial_cut,
            )
            return PrintResponse(ok=True, width=w, height=h)
        except Exception as e:
            _capture(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @auth.post("/print/upload", response_model=PrintResponse)
    async def print_upload(
        image: UploadFile = File(...),
        cut: bool = True,
        feed: int | None = None,
        partial_cut: bool = False,
    ) -> PrintResponse:
        body = await image.read()
        img = _decode_image(body, cfg.max_image_bytes)
        try:
            w, h = escpos_session.print_image(
                conn,
                img,
                print_width=cfg.print_width,
                pad_rows=cfg.bottom_pad_rows,
                cut=cut,
                feed_before_cut=feed if feed is not None else cfg.feed_before_cut,
                partial_cut=partial_cut,
            )
            return PrintResponse(ok=True, width=w, height=h)
        except Exception as e:
            _capture(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @auth.post("/print/raw", response_model=RawResponse)
    def print_raw(req: RawPrintRequest) -> RawResponse:
        try:
            data = base64.b64decode(req.bytes_b64, validate=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
        if len(data) > cfg.max_image_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")
        try:
            n = escpos_session.write_raw(conn, data)
            return RawResponse(ok=True, bytes_written=n)
        except Exception as e:
            _capture(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @auth.post("/cut", response_model=OkResponse)
    def cut_(req: CutRequest) -> OkResponse:
        try:
            escpos_session.cut(conn, partial=req.partial)
            return OkResponse(ok=True)
        except Exception as e:
            _capture(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @auth.post("/feed", response_model=OkResponse)
    def feed_(req: FeedRequest) -> OkResponse:
        try:
            escpos_session.feed(conn, req.lines)
            return OkResponse(ok=True)
        except Exception as e:
            _capture(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    app.include_router(auth)
    return app
