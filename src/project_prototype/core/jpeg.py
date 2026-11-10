from collections.abc import Iterable, Sequence
import io
import pathlib
import typing
from dataclasses import dataclass, field

from PIL import Image, ImageOps
from loguru import logger

from project_prototype.core.base_classes import (
    Quality,
    Settings,
    SomeProtocol,
    compress_repeatedly,
)
from project_prototype.utils.image_utils import (
    add_to_image_in_buffer,
    remove_from_image_in_buffer,
)

MIN_JPEG_QUALITY = 1
MAX_JPEG_QUALITY = 100

QUALITY_STRINGS = { "keep", "low", "web_low", "medium", "web_medium", "high", "web_high", "web_very_high", "maximum", "web_maximum" }  # fmt: off

QualityStrings = typing.Literal["keep", "low", "web_low", "medium", "web_medium", "high", "web_high", "web_very_high", "maximum", "web_maximum"]  # fmt: off


class JpegQuality(Quality):
    def __init__(self, value: int | str) -> None:
        if isinstance(value, str) and value not in QUALITY_STRINGS:
            msg = f"JPEG quality string is invalid: {value}"
            raise ValueError(msg)

        if isinstance(value, int) and (
            value < MIN_JPEG_QUALITY or value > MAX_JPEG_QUALITY
        ):
            msg = f"JPEG quality number not in [1..100]: {value}"
            raise ValueError(msg)

        super().__init__(value)


JpegSubsampling = QualityStrings | typing.Literal["4:4:4", "4:2:2", "4:2:0"]
JpegQtables = QualityStrings | list[list[int]]


@dataclass(frozen=True, slots=True, kw_only=True)
class JpegSettings(Settings):
    format: str = field(default="JPEG", init=False)
    qtables: JpegQtables | None = None
    # subsampling: JpegSubsampling | None = None


class PoopyPoo(SomeProtocol):
    format: str

    def __init__(self, image_buffer: io.BytesIO) -> None:
        self._image_buffer = image_buffer

        with Image.open(self._image_buffer) as img:
            img.verify()
            logger.success("Image is not corrupted")
            # File is not corrupted

        # # NOTE: probably shouldn't save image already...
        #
        # with Image.open(self._image_buffer) as img:
        #     if img.mode != "RGB":
        #         img = img.convert("RGB")  # noqa: PLW2901
        #
        #     img.save(
        #         self._image_buffer,
        #         format=LossyFormat.JPEG,
        #         quality="keep",
        #     )

    @classmethod
    def from_file(cls, fp: typing.IO[bytes]) -> typing.Self:
        buf = io.BytesIO(fp.read())
        return cls(buf)

    @classmethod
    def from_path(cls, path: pathlib.Path) -> typing.Self:
        with path.open(mode="rb") as fp:
            return cls.from_file(fp)

    def save_to(self, fp: typing.IO[bytes]) -> int:
        return fp.write(self._image_buffer.getvalue())

    @property
    def size(self) -> int:
        last_byte = self._image_buffer.seek(0, io.SEEK_END)
        self._image_buffer.seek(0)

        return last_byte

    # def _convert(self, fmt: str) -> io.BytesIO:
    #     result_buffer = io.BytesIO()
    #     with Image.open(self._image_buffer) as img:
    #         img.save(
    #             result_buffer,
    #             format=fmt,
    #         )
    #
    #     return result_buffer

    # @classmethod
    # def from_image(cls, image: SomeProtocol) -> "JpegImage":
    #
    #     image.format
    #     return cls(image._image_buffer)

    def compress_repeatedly(
        self,
        qualities: Sequence[JpegQuality],
        settings: JpegSettings,
    ) -> None:
        compress_repeatedly(
            self._image_buffer,
            qualities=qualities,
            settings=settings,
        )

    def compress_repeatedly_with_flips(
        self,
        qualities: Sequence[JpegQuality],
        settings: JpegSettings,
    ) -> None:

        kwargs = settings.as_dict()

        # 1) Compress repeatedly
        _qualities = qualities[:-1] if len(qualities) % 2 else qualities
        for quality in _qualities:
            with Image.open(self._image_buffer) as img:
                mirror_img = ImageOps.mirror(img)

                self._image_buffer.seek(0)
                self._image_buffer.truncate()

                mirror_img.save(
                    self._image_buffer,
                    quality=quality.value,
                    **kwargs,
                )

        # 2) If there's no need to un-flip, return early.
        if len(qualities) % 2 == 0:
            return

        # Un-flip
        with Image.open(self._image_buffer) as img:
            unflipped_image = ImageOps.mirror(img)

            self._image_buffer.seek(0)
            self._image_buffer.truncate()

            try:
                unflipped_image.save(
                    self._image_buffer,
                    format="JPEG",
                    quality="keep",
                    **kwargs,
                )
            except ValueError:
                unflipped_image.save(
                    self._image_buffer,
                    quality=100,
                    **kwargs,
                )

    def compress_repeatedly_with_crop(
        self,
        qualities: Sequence[JpegQuality],
        settings: JpegSettings,
    ) -> None:
        kwargs = settings.as_dict()
        # This -1 offset happens because we want to ensure
        # the last encoded image is JPEG, instead of PPM.

        add_to_image_in_buffer(
            self._image_buffer,
            top_rows=len(qualities) - 1,
        )

        for quality in qualities[:-1]:
            with Image.open(self._image_buffer) as img:
                img.load()

                self._image_buffer.seek(0)
                self._image_buffer.truncate()

                img.save(
                    self._image_buffer,
                    quality=quality.value,
                    **kwargs,
                )

            remove_from_image_in_buffer(
                self._image_buffer,
                top_rows=1,
            )

        with Image.open(self._image_buffer) as img:
            img.load()

            self._image_buffer.seek(0)
            self._image_buffer.truncate()

            img.save(
                self._image_buffer,
                quality=qualities[-1].value,
                **kwargs,
            )


class JpegImage(PoopyPoo):
    format: str = "jpeg"
