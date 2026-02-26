from __future__ import annotations

import asyncio
import io
import pathlib
from dataclasses import dataclass

import aiofiles.os
import anyio
import hb_data
import httpx
from loguru import logger
from PIL import Image


@dataclass
class Item:
    id: str
    icon: str
    rank: int
    name: str


async def fetch_drive_discs() -> list[hb_data.zzz.DriveDisc]:
    async with hb_data.ZZZClient() as client:
        return client.get_drive_discs()


async def download_image(url: str, path: pathlib.Path) -> None:
    logger.info(f"Downloading image from {url} to {path}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "wb") as file:
            await file.write(response.content)


async def download_drive_disc_images() -> None:
    drive_discs = await fetch_drive_discs()

    async with asyncio.TaskGroup() as tg:
        for disc in drive_discs:
            image_url = disc.icon
            set_id = str(disc.id)[:3] + "00"
            save_path = pathlib.Path("assets/drive_discs/single") / f"{set_id}.webp"

            if save_path.exists():
                logger.info(f"Image for item {disc.id} already exists at {save_path}, skipping.")
                continue

            tg.create_task(download_image(image_url, save_path))

    logger.info("Downloaded all drive disc images.")


def _sync_combine_discs(disc1: io.BytesIO, disc2: io.BytesIO) -> io.BytesIO:
    im = Image.new("RGBA", (235, 222))

    image1_pos = (0, 0)
    image2_pos = (70, 57)

    im2 = Image.open(disc1)
    im.paste(im2, image2_pos, im2)
    im1 = Image.open(disc2)
    im.paste(im1, image1_pos, im1)

    buffer = io.BytesIO()
    im.save(buffer, format="WEBP")
    return buffer


async def combine_drive_disc_images() -> None:
    single_dir = anyio.Path("assets/drive_discs/single")
    combined_dir = anyio.Path("assets/drive_discs/combined")
    await aiofiles.os.makedirs(combined_dir, exist_ok=True)

    async with asyncio.TaskGroup() as tg:
        async for disc_file1 in single_dir.glob("*.webp"):
            async for disc_file2 in single_dir.glob("*.webp"):
                if disc_file1.name == disc_file2.name:
                    continue

                disc_id1 = disc_file1.stem
                disc_id2 = disc_file2.stem
                combined_path = combined_dir / f"{disc_id1}_{disc_id2}.webp"

                async def _combine_and_save(
                    disc_id1: str, disc_id2: str, save_path: anyio.Path
                ) -> None:
                    disc1_path = single_dir / f"{disc_id1}.webp"
                    disc2_path = single_dir / f"{disc_id2}.webp"
                    async with (
                        await anyio.open_file(disc1_path, "rb") as f1,
                        await anyio.open_file(disc2_path, "rb") as f2,
                    ):
                        disc1_data = await f1.read()
                        disc2_data = await f2.read()

                    combined_image = await asyncio.to_thread(
                        _sync_combine_discs, io.BytesIO(disc1_data), io.BytesIO(disc2_data)
                    )

                    combined_image.seek(0)
                    async with await anyio.open_file(save_path, "wb") as out_file:
                        await out_file.write(combined_image.read())

                tg.create_task(_combine_and_save(disc_id1, disc_id2, combined_path))

    logger.info("Combined all drive disc images.")


if __name__ == "__main__":
    asyncio.run(download_drive_disc_images())
    asyncio.run(combine_drive_disc_images())
