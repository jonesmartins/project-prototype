# noqa: INP001
import hashlib
import io
import os
import re
import signal
import threading
import time
import types
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path

import requests
from loguru import logger
from PIL import Image
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    UrlConstraints,
    ValidationError,
    field_validator,
)
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
from rich.table import Column

# Files assumed to exist
PROJECT_DIR_PATH = Path(__file__).parent.parent
RESOURCES_DIR_PATH = PROJECT_DIR_PATH.joinpath("tests", "resources")

# Files that may not exist
IMAGES_DIR_PATH = RESOURCES_DIR_PATH.joinpath("images")
IMAGES_TO_DOWNLOAD_PATH = RESOURCES_DIR_PATH / "images_to_download.json"
CREDITS_PATH = RESOURCES_DIR_PATH / "IMAGE_CREDITS.md"

# Download constants
USER_AGENT = "project-prototype/0.1.0 (https://github.com/jonesmartins/project-prototype)"
MAX_WORKERS = 2  # As recommended in Wikimedia's robot policy
MAX_DOWNLOAD_SPEED = "25 Mbps"  # TODO: Implement.
MAX_CHUNK_SIZE = 8192  # 8 KiB
MAX_IMAGE_SIZE = 50 * (2**20)  # 50 MiB

ALLOWED_IMAGE_HOSTS = {"upload.wikimedia.org"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

console = Console()
done_event = threading.Event()

S = t.TypeVar("S")


@dataclass(frozen=True, slots=True)
class Success(t.Generic[S]):
    value: S


@dataclass(frozen=True, slots=True)
class Failure:
    message: str


@dataclass(frozen=True, slots=True)
class Skipped:
    reason: str


Outcome = Success[S] | Failure | Skipped

Hash = t.NewType("Hash", str)


class ImageData(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        frozen=True,
        validate_by_name=True,
    )

    image_url: t.Annotated[
        HttpUrl,
        UrlConstraints(
            allowed_schemes=["https"],
            host_required=True,
        ),
    ]
    sha256: Hash = Field(pattern=r"^[0-9a-f]{64}$")
    author: t.Annotated[str, StringConstraints(min_length=1)]
    file_name: t.Annotated[str, StringConstraints(min_length=1)]
    license_name: t.Annotated[str, StringConstraints(min_length=1)]
    data_url: HttpUrl | None = None
    license_url: HttpUrl | None = None

    @field_validator("image_url")
    @classmethod
    def check_image_url(cls, v: HttpUrl) -> HttpUrl:
        if v.host not in ALLOWED_IMAGE_HOSTS:
            msg = (
                f"URL host ({v.host}) must be in {sorted(ALLOWED_IMAGE_HOSTS)}"
            )
            raise ValidationError(msg)

        return v

    @field_validator("file_name")
    @classmethod
    def check_file_name(cls, v: str) -> str:
        path = Path(v)
        if path.name != v or v.startswith("."):
            msg = "file_name must be in format `<name>.<extension>`"
            raise ValidationError(msg)

        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            msg = f"extension must be one of {sorted(ALLOWED_EXTENSIONS)}"
            raise ValidationError(msg)

        return v


def download_image(
    image_data: ImageData,
    session: requests.Session,
    progress_bar: Progress,
    task_id: TaskID,
) -> Outcome[tuple[io.BytesIO, Hash]]:
    image_url = image_data.image_url.encoded_string()

    with session.get(
        image_url,
        allow_redirects=False,
        stream=True,
        timeout=(5, 30),
    ) as response:
        if response.status_code != HTTPStatus.OK:
            progress_bar.update(
                task_id,
                description=f"[red]status code {response.status_code}",
            )
            msg = f"image URL request failed with status code {response.status_code}"
            return Failure(msg)

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            progress_bar.update(
                task_id,
                description=f"[red]wrong content type: {content_type}",
            )
            msg = f"image URL request did not return an image: {content_type}"
            return Failure(msg)

        image_size = int(response.headers.get("Content-Length", -1))

        if image_size < 0 or image_size > MAX_IMAGE_SIZE:
            progress_bar.update(
                task_id,
                description="[red]image size out of bounds",
            )
            msg = f"image size is out of bounds [0..{MAX_IMAGE_SIZE} B]: {image_size} B"
            return Failure(msg)

        progress_bar.update(task_id, total=image_size)

        image_buffer = io.BytesIO()

        progress_bar.start_task(task_id)

        sha256_hash = hashlib.sha256()
        total_bytes = 0

        # For (bad) debugging purposes:
        # last_chunk = 0
        # for chunk in range(0, image_size, MAX_CHUNK_SIZE):
        #     chunk_size = chunk - last_chunk
        #     total_bytes += chunk_size
        #     if total_bytes > MAX_IMAGE_SIZE:
        #         progress_bar.update(
        #             task_id,
        #             description="[red]image size out of bounds",
        #         )
        #         msg = f"image size is out of bounds [0..{MAX_IMAGE_SIZE} B]: {total_bytes} B"
        #         return Failure(msg)
        #
        #     progress_bar.update(task_id, advance=chunk_size)
        #     last_chunk = chunk
        #     time.sleep(1)

        for chunk in response.iter_content(MAX_CHUNK_SIZE):
            chunk_size = image_buffer.write(chunk)
            total_bytes += chunk_size
            if total_bytes > MAX_IMAGE_SIZE:
                progress_bar.update(
                    task_id,
                    description="[red]image size out of bounds",
                )
                msg = f"image size is out of bounds [0..{MAX_IMAGE_SIZE} B]: {total_bytes} B"
                return Failure(msg)

            sha256_hash.update(chunk)
            progress_bar.update(task_id, advance=chunk_size)

    # Confirm file was downloaded completely
    if total_bytes < image_size:
        progress_bar.update(task_id, description="[red]incomplete download")
        msg = f"image download was incomplete: {image_data.file_name}"
        return Failure(msg)

    progress_bar.update(
        task_id,
        description="[green]download completed",
        completed=total_bytes,
    )

    return Success((image_buffer, Hash(sha256_hash.hexdigest())))


def thread(
    progress_bar: Progress,
    session: requests.Session,
    task_id: TaskID,
    image_data: ImageData,
) -> Outcome[Path]:
    if done_event.is_set():
        msg = "interrupted before download"
        return Skipped(msg)

    outcome = download_image(
        image_data=image_data,
        session=session,
        progress_bar=progress_bar,
        task_id=task_id,
    )
    match outcome:
        case Success((image_buffer, sha256_hex)):
            pass
        case _:
            return outcome

    # TODO: SHA-256 not matching.
    console.log(
        f"({image_data.file_name}) Expected SHA256:  {image_data.sha256}"
    )
    console.log(f"({image_data.file_name}) Image SHA256:  {sha256_hex}")

    if image_data.sha256 != sha256_hex:
        progress_bar.update(
            task_id,
            description="[red]SHA-256 hashes don't match",
        )
        msg = "downloaded image's SHA-256 doesn't match expected SHA-256"
        return Failure(msg)

    progress_bar.update(
        task_id,
        description="[green]SHA-256 hashes match",
    )

    # Save image to temporary file before renaming it
    # in case something goes wrong.
    target_path = IMAGES_DIR_PATH / image_data.file_name
    partial_image_path = target_path.with_suffix(".part")
    try:
        partial_image_path.write_bytes(image_buffer.getbuffer())
    except OSError as e:
        partial_image_path.unlink(missing_ok=True)
        progress_bar.update(
            task_id,
            description="[red]error writing to .part file",
        )
        msg = f"error writing to .part file: {e}"
        return Failure(msg)
    else:
        progress_bar.update(
            task_id,
            description="[green]saved to file",
        )
        partial_image_path.replace(target_path)

    return Success(target_path)


# -------- Main --------


def handle_sigint(signum: int, frame: types.FrameType | None) -> None:  # noqa: ARG001
    """
    1st Ctrl+C: Stop future downloads;
    2nd Ctrl+C: Stop all downloads;
    """
    if done_event.is_set():
        os._exit(130)

    done_event.set()
    console.log(
        "[yellow]Finishing current downloads... Ctrl+C again to force quit",
    )


def load_image_data(path: Path) -> list[ImageData]:
    type_adapter = TypeAdapter(list[ImageData])
    all_images_data = type_adapter.validate_json(path.read_bytes())
    logger.info(f"Found {len(all_images_data)} image data.")

    # All file_names are unique, otherwise they'd overwrite each other.
    names = [i.file_name for i in all_images_data]

    if len(names) != len(set(names)):
        duplicates = sorted({n for n in names if names.count(n) > 1})
        msg = f"duplicate file_name entries: {duplicates}"
        raise ValueError(msg)

    return all_images_data


def select_images_to_download(
    image_data_list: list[ImageData],
) -> list[ImageData]:
    images_to_download: list[ImageData] = []
    for image_data in image_data_list:
        dest_path = IMAGES_DIR_PATH / image_data.file_name
        if not dest_path.exists():
            images_to_download.append(image_data)
        else:
            file_sha256 = hashlib.sha256(dest_path.read_bytes())

            if file_sha256.hexdigest() != image_data.sha256:
                images_to_download.append(image_data)
    return images_to_download


def download_images(images_to_download: list[ImageData]) -> list[Path]:
    download_progress_bar = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        TextColumn(
            "[bold blue]{task.description}",
            justify="left",
            table_column=Column(ratio=2),
        ),
    )

    with download_progress_bar, requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures: dict[Future[Outcome[Path]], ImageData] = {}

            for image_data in images_to_download:
                task_id = download_progress_bar.add_task(
                    "downloading",
                    start=False,
                    total=None,
                    filename=image_data.file_name,  # custom field
                )

                future = pool.submit(
                    thread,
                    download_progress_bar,
                    session,
                    task_id,
                    image_data,
                )
                futures[future] = image_data

        successes: list[Path] = []
        errors: list[str] = []
        for future, image_data in futures.items():
            try:
                match future.result():
                    case Success(path):
                        successes.append(path)
                    case Failure(msg) | Skipped(msg):
                        errors.append(msg)
            except Exception as e:  # noqa :BLE001
                errors.append(
                    f"{image_data.file_name}: unexpected {type(e).__name__}: {e}",
                )

        return successes


def md_escape(v: str) -> str:
    characters_to_escape = re.compile(r"([\\`*_{}\[\]()<>#+!|~&])")
    return characters_to_escape.sub(r"\\\1", v)


def write_credits(
    all_images_data: list[ImageData],
    credits_path: Path,
) -> None:
    if not all_images_data:
        return

    lines = [
        "| File | Author | License |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {md_escape(i.file_name)} | {md_escape(i.author)} | [{md_escape(i.license_name)}]({i.license_url}) |"
        for i in all_images_data
        if (IMAGES_DIR_PATH / i.file_name).exists()
    ]
    credits_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_resized_versions(
    paths: t.Sequence[Path],
    resizes: t.Sequence[float],
) -> None:
    resize_progress_bar = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TextColumn(
            "[bold blue]{task.description}",
            justify="left",
            table_column=Column(ratio=2),
        ),
    )

    with resize_progress_bar:
        for path in paths:
            task_id = resize_progress_bar.add_task(
                "resizing...",
                start=False,
                total=len(resizes),
                filename=path.name,
            )
            with Image.open(
                path,
                formats=list(ALLOWED_EXTENSIONS),
            ) as image:
                (curr_width, curr_height) = image.size
                for resize in resizes:
                    progress_bar.update(
                        task_id,
                        description=f"[green]resizing {100 * resize}%",
                    )
                    new_width = int(curr_width * resize)
                    new_height = int(curr_height * resize)
                    resized_image = image.resize((new_width, new_height))  # pyright: ignore[reportUnknownMemberType]
                    resized_image_path = path.with_name(
                        f"{path.stem}_resized_{100 * resize}%.{path.suffix}",
                    )
                    resized_image.save(resized_image_path)


def main(image_data_path: Path) -> None:
    signal.signal(signal.SIGINT, handle_sigint)

    logger.info(f"Loading image data from {image_data_path}")
    all_images_data = load_image_data(image_data_path)

    logger.info(f"Writing credits markdown file: {CREDITS_PATH}")
    write_credits(all_images_data, credits_path=CREDITS_PATH)

    logger.info(f"Selecting images to download from {image_data_path}")
    images_to_download = (
        all_images_data
        if not IMAGES_DIR_PATH.exists()
        else select_images_to_download(all_images_data)
    )

    logger.info(f"Images to download: {len(images_to_download)}")
    for idx, image_data in enumerate(images_to_download, start=1):
        logger.info(f"  {idx}. {image_data.file_name}")

    IMAGES_DIR_PATH.mkdir(exist_ok=True)

    logger.info(f"Downloading {len(images_to_download)} images")
    image_paths = download_images(images_to_download)

    logger.info(f"Saving {len(image_paths)} resized versions")
    save_resized_versions(image_paths, resizes=(0.5, 0.25, 0.125, 0.0675))


if __name__ == "__main__":
    main(IMAGES_TO_DOWNLOAD_PATH)
