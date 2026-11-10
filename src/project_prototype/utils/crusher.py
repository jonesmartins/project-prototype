import io
import typing

from PIL import Image
from PIL.Image import Transpose

MIN_QUALITY = 1
MAX_QUALITY = 100


def save_loaded_image_as_jpeg_to_buffer(
    image: Image.Image,
    image_buffer: io.BytesIO,
    quality: int,
) -> None:
    """Save loaded image to buffer.

    Note:
    PIL lazy-loads images.
    Since we empty the buffer the image was in before calling `image.save()`,
    calling `image.save()` on an unloaded image raises an exception.
    One must ensure the image has been loaded
    into memory (maybe with a `image.load()` call) before calling this function.

    Args:
        image (Image.Image): Image object
        image_buffer (io.BytesIO): Image buffer (possibly occupied)
        quality (int): JPEG encoding MAX_QUALITY
    """
    # Empty image buffer
    image_buffer.seek(0)
    image_buffer.truncate()

    # Fill buffer with encoded JPEG
    image.save(
        image_buffer,
        format="JPEG",
        quality=quality,
    )


def crush_with_rotations(
    image_buffer: io.BytesIO,
    qualities: typing.Sequence[int],
) -> io.BytesIO:
    """Rotate by 90º, save as JPEG, repeat.

    Note: Rotating by 90 degrees yields images with more entropy (good...?).
    I tried rotating the image by 180 with a huge list of qualities, but for little to no effect.

    Args:
        image_buffer (io.BytesIO): JPEG image buffer
        qualities (Sequence[int]): Sequence of JPEG qualities
    Returns:
        Crushed JPEG image in buffer
    """
    result_buffer = io.BytesIO()

    # 1) Save repeatedly.
    # 1.1) First `img.save(...)` fills result_buffer with encoded image in image_buffer.
    with Image.open(image_buffer) as img:
        rotated_img = img.transpose(
            Transpose.ROTATE_90,
        )
        rotated_img.save(
            image_buffer,
            format="JPEG",
            quality=qualities[0],
        )

    # 1.2) Subsequent `img.save(...)` are applied on result_buffer.
    for quality in qualities[1:]:
        with Image.open(result_buffer) as img:
            rotated_img = img.transpose(
                Transpose.ROTATE_90,
            )
            save_loaded_image_as_jpeg_to_buffer(
                rotated_img,
                result_buffer,
                quality=quality,
            )

    # 2) Undo rotation, if necessary
    # If the image was rotated by 90º, we rotate it by (360 - 90)º
    # Instead of using angles, we use len(qualities) as a proxy.
    methods = (
        None,
        Transpose.ROTATE_270,
        Transpose.ROTATE_180,
        Transpose.ROTATE_90,
    )
    method = methods[len(qualities) % len(methods)]
    if method is None:
        return result_buffer

    with Image.open(result_buffer) as img:
        rotated_img = img.transpose(
            method,
        )
        save_loaded_image_as_jpeg_to_buffer(
            rotated_img,
            result_buffer,
            quality=qualities[-1],
        )
    return result_buffer


def crush(
    image_buffer: io.BytesIO,
    qualities: typing.Sequence[int],
) -> io.BytesIO:
    """Save as JPEG repeatedly.

    Args:
        image_buffer (io.BytesIO): JPEG image buffer
        qualities (Sequence[int]): Sequence of JPEG qualities
    Returns
        Crushed JPEG image in buffer
    """
    result_buffer = io.BytesIO()

    with Image.open(image_buffer) as img:
        img.save(
            result_buffer,
            format="JPEG",
            quality=qualities[0],
        )

    for quality in qualities[1:]:
        with Image.open(result_buffer) as img:
            img.load()

            save_loaded_image_as_jpeg_to_buffer(
                img,
                result_buffer,
                quality=quality,
            )

    return result_buffer
