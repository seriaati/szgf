from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Self

import aiofiles
import aiofiles.os
import aiohttp
from loguru import logger
from yarl import URL

from szgf.schemas.parsed import ParsedGuide


class SZGFClient:
    """Client for interacting with the SZGF guides repository."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._guides_url = URL("https://api.github.com/repos/seriaati/szgf/contents/guides")
        self._guides_dir = Path(".zzz_guides/")

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            msg = "Client session has not been started. Use 'await start()' first."
            raise RuntimeError(msg)
        return self._session

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        await self.close()

    async def _fetch_txt(self, url: URL | str) -> str:
        logger.debug(f"Fetching text from {url}")

        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    @staticmethod
    def _parse_json(content: str) -> dict:
        return json.loads(content)

    async def download_guides(self) -> None:
        """Download all guides from the GitHub repository and store them locally."""
        logger.debug("Downloading guides...")

        async with self.session.get(self._guides_url / "parsed") as response:
            response.raise_for_status()
            data = await response.json()

        await aiofiles.os.makedirs(self._guides_dir, exist_ok=True)

        async with aiofiles.open(
            self._guides_dir / ".gitignore", mode="w", encoding="utf-8"
        ) as gitignore:
            await gitignore.write("*\n")

        async with asyncio.TaskGroup() as tg:
            for item in data:
                if item["type"] == "file" and item["name"].endswith(".json"):
                    tg.create_task(self._download_guide_file(item))

    async def _download_guide_file(self, item: dict) -> None:
        file_url = item["download_url"]
        content = await self._fetch_txt(file_url)

        async with aiofiles.open(
            self._guides_dir / item["name"], mode="w", encoding="utf-8"
        ) as file:
            await file.write(content)

    async def read_guides(self) -> dict[str, ParsedGuide]:
        """Read all locally stored guides and parse them into ParsedGuide objects.

        Returns:
            A dictionary mapping character IDs to ParsedGuide objects.
        """
        logger.debug("Reading guides from local storage...")

        guides: dict[str, ParsedGuide] = {}
        guide_dir = self._guides_dir

        if not guide_dir.exists():
            logger.warning("Guides have not been downloaded. Use 'await download_guides()' first.")
            return guides

        entries = await aiofiles.os.scandir(guide_dir)

        for entry in entries:
            if entry.is_file() and entry.name.endswith(".json"):
                async with aiofiles.open(guide_dir / entry.name, encoding="utf-8") as file:
                    content = await file.read()
                    guide_dict = self._parse_json(content)
                    parsed = ParsedGuide.model_validate(guide_dict)
                    guides[str(parsed.character.id)] = parsed

        return guides

    async def start(self) -> None:
        """Start the client session."""
        self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the client session."""
        if self._session is not None:
            await self._session.close()
