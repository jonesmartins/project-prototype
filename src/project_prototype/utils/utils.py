from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal


class CrushMethod(StrEnum):
    DEFAULT = "DEFAULT"
    ROTATE = "ROTATE"
    CROP = "CROP"
    CROP_AND_ROTATE = "CROP_AND_ROTATE"
    # CROP_TOP = "CROP_TOP"
    # CROP_LEFT = "CROP_LEFT"


def generate_jpeg_basename(
    input_path: Path,
    *,
    qualities: Sequence[JpegQuality],
    repeat: int,
    method: CrushMethod,
) -> str:
    """Generate JPEG basename with crusher parameters.

    Args:

    Returns:
        str: Output filename with some information about its configuration.
    """
    qualities_str = ",".join(str(q) for q in qualities)
    method_str = {
        CrushMethod.DEFAULT: "default",
        CrushMethod.ROTATE: "rotate",
        CrushMethod.CROP: "crop",
        CrushMethod.CROP_AND_ROTATE: "crop_and_rotate",
    }[method]
    return f"{input_path.stem}_r{repeat}_q{qualities_str}_{method_str}.jpg"
