"""Pydantic schemas for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrintJsonRequest(BaseModel):
    image: str = Field(..., description="Image as data URL or bare base64 PNG/JPEG.")
    cut: bool = True
    feed: int | None = Field(default=None, ge=0, le=20)
    partial_cut: bool = False


class PrintResponse(BaseModel):
    ok: bool = True
    width: int
    height: int


class CutRequest(BaseModel):
    partial: bool = False


class FeedRequest(BaseModel):
    lines: int = Field(default=3, ge=0, le=64)


class RawPrintRequest(BaseModel):
    bytes_b64: str = Field(..., description="Base64-encoded ESC/POS byte stream.")


class OkResponse(BaseModel):
    ok: bool = True


class RawResponse(BaseModel):
    ok: bool = True
    bytes_written: int


class HealthResponse(BaseModel):
    ok: bool
    printer: str
    kind: str
    target: str


class StatusResponse(BaseModel):
    ok: bool
    kind: str
    target: str
    last_error: str | None = None
    print_width: int
    bottom_pad_rows: int
    feed_before_cut: int
