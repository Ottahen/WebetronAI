"""
Image generation for Atlas mode.

This calls Perchance's AI Text-to-Image Generator
(https://perchance.org/ai-text-to-image-generator) and is credited to
Perchance in the API response and in the UI every time it's used —
Clued doesn't have its own image model, and doesn't pretend to.

IMPORTANT / HONEST CAVEAT: Perchance's generator is a client-side plugin
with no official, documented, stable REST API. The endpoints below are
the ones its own web page calls under the hood, reverse-engineered the
same way several open-source "perchance API" wrappers on GitHub have
done it: fetch a short-lived user key, then poll a generate endpoint
with that key. Perchance can change this at any time without notice,
which will break this connector. When that happens we fail loudly and
say so — we never fabricate a placeholder image or claim a generation
succeeded when it didn't.

Two images per request, per the product spec.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import List, Optional

import requests

USER_KEY_URL = "https://image-generation.perchance.org/api/getUserKey"
GENERATE_URL = "https://image-generation.perchance.org/api/generate"
DOWNLOAD_URL_TEMPLATE = "https://image-generation.perchance.org/api/downloadTemporaryImage"


def _default_headers() -> dict:
    contact = os.environ.get("CONTACT_EMAIL", "set CONTACT_EMAIL in .env")
    return {
        "User-Agent": f"Mozilla/5.0 (compatible; CluedAtlas/1.0; +https://github.com/Ottahen; contact: {contact})",
        "Referer": "https://perchance.org/ai-text-to-image-generator",
    }

IMAGES_PER_REQUEST = 2
REQUEST_TIMEOUT = 25
POLL_ATTEMPTS = 20
POLL_DELAY_SECONDS = 1.0


@dataclass
class GeneratedImage:
    url: str
    seed: int


@dataclass
class ImageGenResult:
    ok: bool
    images: List[GeneratedImage]
    provider: str = "Perchance (perchance.org/ai-text-to-image-generator)"
    error: Optional[str] = None


class PerchanceImageGenerator:
    """Best-effort client for Perchance's image generator. See module
    docstring: this is unofficial and may stop working without warning."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(_default_headers())
        self._user_key: Optional[str] = None

    def generate(self, prompt: str, negative_prompt: str = "") -> ImageGenResult:
        prompt = prompt.strip()
        if not prompt:
            return ImageGenResult(ok=False, images=[], error="Empty prompt.")

        try:
            key = self._get_user_key()
            images = []
            for _ in range(IMAGES_PER_REQUEST):
                seed = random.randint(1, 2_147_483_647)
                image = self._generate_one(prompt, negative_prompt, key, seed)
                if image:
                    images.append(image)

            if not images:
                return ImageGenResult(
                    ok=False,
                    images=[],
                    error=(
                        "Perchance didn't return an image this time. Their "
                        "generator has no official API, so this can happen "
                        "when they change something on their end — you can "
                        "also try the prompt directly at "
                        "perchance.org/ai-text-to-image-generator."
                    ),
                )
            return ImageGenResult(ok=True, images=images)

        except Exception as exc:  # noqa: BLE001 - surface as a clear, honest failure
            return ImageGenResult(
                ok=False,
                images=[],
                error=(
                    "Image generation via Perchance failed "
                    f"({exc.__class__.__name__}). Perchance's generator isn't a "
                    "documented public API, so this connector can break when "
                    "they change it. Try again, or generate directly at "
                    "perchance.org/ai-text-to-image-generator."
                ),
            )

    def _get_user_key(self) -> str:
        if self._user_key:
            return self._user_key
        resp = self._session.get(USER_KEY_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        key = data.get("userKey") or data.get("key")
        if not key:
            raise RuntimeError("no userKey in Perchance response")
        self._user_key = key
        return key

    def _generate_one(
        self, prompt: str, negative_prompt: str, user_key: str, seed: int
    ) -> Optional[GeneratedImage]:
        params = {
            "prompt": prompt,
            "negativePrompt": negative_prompt,
            "userKey": user_key,
            "seed": seed,
            "resolution": "512x512",
            "guidanceScale": 7,
            "channel": "ai-text-to-image-generator",
        }
        resp = self._session.get(GENERATE_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        image_id = data.get("imageId")
        if not image_id:
            return None

        # The generator renders asynchronously; poll briefly for readiness.
        for _ in range(POLL_ATTEMPTS):
            status_resp = self._session.get(
                DOWNLOAD_URL_TEMPLATE,
                params={"imageId": image_id, "userKey": user_key},
                timeout=REQUEST_TIMEOUT,
            )
            if status_resp.status_code == 200 and status_resp.headers.get(
                "content-type", ""
            ).startswith("image"):
                url = f"{DOWNLOAD_URL_TEMPLATE}?imageId={image_id}&userKey={user_key}"
                return GeneratedImage(url=url, seed=seed)
            time.sleep(POLL_DELAY_SECONDS)

        return None
