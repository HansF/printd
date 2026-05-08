"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PrinterKind = Literal["usb", "network", "serial", "dummy"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRINTD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8080

    printer_kind: PrinterKind = "usb"
    device: str = "/dev/usb/lp0"

    print_width: int = Field(default=576, ge=8, le=1024)
    bottom_pad_rows: int = Field(default=24, ge=0, le=128)
    feed_before_cut: int = Field(default=4, ge=0, le=20)

    cors_origins: str = "*"
    max_image_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


def load_settings() -> Settings:
    return Settings()
