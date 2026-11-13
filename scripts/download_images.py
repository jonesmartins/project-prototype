# noqa: INP001

#   - Parse tests/images_to_download.json
#   - Download image from url
#   - Confirm image's checksum matches SHA-1 from json
#   - Save image to tests/resources/images/ directory
#   - Add author and license information to tests/resources/IMAGE_CREDITS.md

import hashlib
import io
import json
import signal
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import types
import typing

from PIL import Image
import requests
import pydantic
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

# Files assumed to exist
PROJECT_DIR_PATH = Path(__file__).parent.parent
RESOURCES_DIR_PATH = PROJECT_DIR_PATH.joinpath("tests", "resources")

# Files that may not exist
IMAGES_DIR_PATH = RESOURCES_DIR_PATH.joinpath("images")
IMAGES_TO_DOWNLOAD_PATH = RESOURCES_DIR_PATH / "images_to_download.json"

# Download constants
USER_AGENT = "project-prototype/0.1.0 (https://github.com/jonesmartins/project-prototype)"
MAX_WORKERS = 2  # As recommended in Wikimedia's robot policy
MAX_DOWNLOAD_SPEED = "25 Mbps"  # TODO: Implement.
MAX_CHUNK_SIZE = 8192  # 8 KiB
MAX_IMAGE_SIZE = 50 * (2**20)  # 50 MiB

console = Console()

done_event = threading.Event()

ALLOWED_HOSTS = {"upload.wikimedia.org"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class ImageData(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        frozen=True,
        validate_by_name=True,
    )

    sha256: str = pydantic.Field(pattern=f"^[0-9a-fA-F]{40}$")
    image_url: pydantic.HttpUrl
    data_url: pydantic.HttpUrl
    author: str
    license_name: str
    license_url: str
    file_name: str

    @pydantic.field_validator("image_url")
    @classmethod
    def check_image_url(cls, v: pydantic.HttpUrl) -> pydantic.HttpUrl:
        if v.scheme != "https":
            msg = f"URL scheme is not https: {v}"
            raise ValueError(msg)

        if v.host not in ALLOWED_HOSTS:
            msg = f"URL host ({v.host}) must be in {ALLOWED_HOSTS}"
            raise ValueError(msg)
        return v

    @pydantic.field_validator("file_name")
    @classmethod
    def check_file_name(cls, v: str) -> str:
        if Path(v).name != v or v.startswith("."):
            msg = f""
            raise ValueError(msg)
        if Path(v).suffix.lower() not in ALLOWED_EXTENSIONS:
            msg = f""
            raise ValueError(msg)
        return v


progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)


def download_image(
    session: requests.Session,
    task_id: TaskID,
    image_data: ImageData,
) -> bool:
    image_url = image_data["image_url"]

    # TODO: Allowlist of hosts
    # TODO:Path traversal: a file_name like ../../x or an absolute path escapes IMAGES_DIR_PATH. Require Path(name).name == name, or check (IMAGES_DIR_PATH / name).resolve().is_relative_to(IMAGES_DIR_PATH.resolve()).
    with session.get(
        image_url,
        allow_redirects=False,
        stream=True,
        timeout=30,
    ) as response:
        response.raise_for_status()

        image_size = int(response.headers.get("Content-Length", -1))

        if image_size < 0 or image_size > MAX_IMAGE_SIZE:
            raise
            # TODO:
        # size_in_kib = image_size / 2**10
        # console.print(f"Image size: {size_in_kib:.2f} KiB")

        progress.update(task_id, total=image_size)

        image_buffer = io.BytesIO()
        progress.start_task(task_id)

        sha256_hash = hashlib.sha256()
        total_bytes = 0
        last_chunk = 0
        for chunk in range(0, image_size, MAX_CHUNK_SIZE):
            if done_event.is_set():
                break
            chunk_size = chunk - last_chunk
            total_bytes += chunk_size
            if total_bytes > MAX_IMAGE_SIZE:
                console.print(f"[red]")
                # TODO:
            # sha256_hash.update(chunk)
            progress.update(task_id, advance=chunk_size)
            last_chunk = chunk

        # for chunk in response.iter_content(MAX_CHUNK_SIZE):
        #     if done_event.is_set():
        #         break
        #     chunk_size = image_buffer.write(chunk)
        #     total_bytes += chunk_size
        #     sha256_hash.update(chunk)
        #     progress.update(task_id, advance=chunk_size)

        progress.update(task_id, completed=total_bytes)

        if image_data["sha256"].lower() != sha256_hash.hexdigest():
            return False

        img_path = IMAGES_DIR_PATH / image_data["file_name"]
        img_path.write_bytes(image_buffer.getbuffer())
        return True
        # console.print(
        #     f"[green]Saved {size_in_kib:.2f} KiB to {img_path}[/green]",
        # )
        # console.print(
        #     f"[red]Error: SHA-1 does not match[/red]: {image_data['image_url']}",
        # )


def handle_sigint(signum: int, frame: types.FrameType | None) -> None:
    done_event.set()


def parse_image_data(image_data_path: Path) -> list[ImageData]:
    console.print(f"Reading {image_data_path}")
    all_images_data = [
        ImageData(data) for data in json.loads(image_data_path.read_text())
    ]

    # All file_names are unique
    if len(all_images_data) != len({d["file_name"] for d in all_images_data}):
        console.print("[red]All `file_name` fields must be unique.")
        raise SystemExit(1)

    # All URLs are unique
    if len(all_images_data) == len({d["image_url"] for d in all_images_data}):
        console.print("[red]All `image_url` fields must be unique.")
        raise SystemExit(1)

    console.print(f"Found {len(all_images_data)} image data.")
    return all_images_data


def main() -> None:
    signal.signal(signal.SIGINT, handle_sigint)

    all_images_data = parse_image_data(IMAGES_TO_DOWNLOAD_PATH)

    images_to_download_data = [
        img_data
        for img_data in all_images_data
        if not (IMAGES_DIR_PATH / img_data["file_name"]).exists()
    ]

    console.print(f"Images to download: {len(images_to_download_data)}")
    for idx, img_data in enumerate(images_to_download_data, start=1):
        console.print(f"  {idx}. {img_data['file_name']}")

    IMAGES_DIR_PATH.mkdir(exist_ok=True)

    with (
        ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool,
        requests.Session() as session,
        progress,
    ):
        session.headers.update({"User-Agent": USER_AGENT})

        try:
            futures: list[Future[bool]] = []

            for img_data in images_to_download_data:
                task_id = progress.add_task(
                    f"Downloading {img_data['file_name']}",
                    start=False,
                    total=None,
                    filename=img_data["file_name"],  # custom field
                )

                future = pool.submit(download_image, session, task_id, img_data)
                futures.append(future)

            for f in futures:
                f.result()
        except KeyboardInterrupt:
            done_event.set()
            raise


if __name__ == "__main__":
    main()
