import enum
import io
import os
import pathlib
import typing
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from io import BytesIO, FileIO

from PIL import Image, ImageEnhance, ImageOps, JpegPresets
from PIL.Image import Transpose

from project_prototype.core.base_classes import (
    Quality,
    Settings,
    _compress_repeatedly,
)
from project_prototype.utils.image_utils import (
    add_to_image_in_buffer,
    remove_from_image_in_buffer,
)
from project_prototype.utils.utils import CrushMethod

fp = pathlib.Path()


# JpegQuality = (
#     int  # Assumed to be in [0..100]
#     | typing.Literal[
#         "keep",
#         "low",
#         "web_low",
#         "medium",
#         "web_medium",
#         "high",
#         "web_high",
#         "web_very_high",
#         "maximum",
#         "web_maximum",
#     ]
# )


# class LossyFormat(enum.StrEnum):
#     JPEG = "jpeg"
#     JPEG2000 = "jpeg2000"  # j2k, jp2
#     JPEGXL = "jpegxl"
#     AVIF = "avif"
#     WEBP = "webp"


# F = typing.TypeVar("F", bound=LossyFormat)


# TODO: splitting and merging bands


# TODO: Remember that crusher with crop(left,right) == crusher with crop(right,left)
# def crush(
#     input_path: pathlib.Path,
#     qualities: typing.Sequence[int],
#     method: CrushMethod,
#     output_path: pathlib.Path,
# ) -> None:
#     with input_path.open(mode="rb") as fp:
#         jpeg_img = JpegImage.from_file(fp)

# ImageEnhance.Contrast
# ImageEnhance.Brightness
# ImageEnhance.Color
# ImageEnhance.Sharpness
# ImageEnhance.ImageStat.Stat
# ImageEnhance.ImageFilter.Filter
# ImageEnhance.ImageFilter.__annotations__

# if method == CrushMethod.DEFAULT:
#     func = jpeg_img.compress_repeatedly
# elif method == CrushMethod.ROTATE:
#     func = jpeg_img.compress_repeatedly_with_flips
# elif method == CrushMethod.CROP:
#     func = jpeg_img.compress_repeatedly_with_crop
# elif method == CrushMethod.CROP_AND_ROTATE:
#     func = jpeg_img.compress_repeatedly_with_crop_and_flips
# else:
#     raise NotImplementedError
#
# func(
#     qualities=qualities,
#     settings=JpegSettings(),
# )
#
# with output_path.open(mode="wb") as fd:
#     jpeg_img.save_to(fd)


# TODO: Maybe GIFs as lossy format???
# TODO: Downsample, upsample


# lossy_format_to_class = {
#     LossyFormat.JPEG: JpegImage,
#     LossyFormat.JPEG2000: Jpeg2000Image,
#     LossyFormat.JPEGXL: JpegXlImage,
#     LossyFormat.AVIF: AvifImage,
#     LossyFormat.WEBP: WebpImage,
# }

if __name__ == "__main__":
    import sys

    from loguru import logger

    path = pathlib.Path(sys.argv[1])

    with Image.open(path) as img:
        img.verify()

    # with Image.open(path, formats=tuple(LossyFormat)) as img:
    #     if img.format is None:
    #         msg = f"img.format is None: {path}"
    #         raise ValueError(msg)
    #
    #     match lossy_format_to_class[img.format]:  # pyright: ignore[reportArgumentType]
    #         case LossyFormat.JPEG:
    #             cls = JpegImage
    #         case LossyFormat.JPEG2000:
    #             cls = Jpeg2000Image
    #         case LossyFormat.JPEGXL:
    #             cls = JpegXlImage
    #         case LossyFormat.AVIF:
    #             cls = AvifImage
    #         case LossyFormat.WEBP:
    #             cls = WebpImage
    #         case _:
    #             raise NotImplementedError
    #
    #     logger.info("Path: {}", path)
    #     logger.info("Format: {}", img.format)
    #     logger.info("Mode: {}", img.mode)
    #     logger.info("Dimensions: {}", img.size)
    #
    #     lossy_img = cls(io.BytesIO(img.tobytes()))  # pyright: ignore[reportCallIssue]

    # Mitigations: log the filename/hash, detected format, and dimensions of every image processed;
    # log and alert on Image.DecompressionBombWarning, Image.DecompressionBombError, and PIL.UnidentifiedImageError.
    # Mitigations: treat all values from image.info, image._getexif(), image.getexif(), and image.text as untrusted; sanitise before storing or rendering; strip metadata when it is not required.
    # Mitigations: to guarantee a clean output when saving, create a new image instance via image.copy() and delete the image.info contents.
    # Mitigations: validate MIME type and magic bytes independently before calling Image.open(); pass the formats argument with an allowlist of accepted formats.
