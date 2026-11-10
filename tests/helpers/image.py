import io
import pathlib
import typing

from PIL import Image

TEST_IMAGES_DIRECTORY = pathlib.Path(__file__).parent.joinpath("images")
SMALL_TEST_IMAGES_DIRECTORY = TEST_IMAGES_DIRECTORY.joinpath("small")


def create_img_from_brightness_list(
    image_size: tuple[int, int],
    brightnesses: list[int],
) -> Image.Image:
    img = Image.new(mode="L", size=image_size)
    img.putdata(brightnesses)
    return img


def create_img_buffer_from_brightness_list(
    image_size: tuple[int, int],
    brightnesses: list[int],
    fmt: str,
) -> io.BytesIO:
    img_buffer = io.BytesIO()
    with create_img_from_brightness_list(image_size, brightnesses) as img:
        img.save(
            img_buffer,
            format=fmt,
        )
    return img_buffer


def compare_images(
    i1: Image.Image,
    i2: Image.Image,
) -> bool:
    return list(i1.getdata()) == list(i2.getdata())


def open_and_compare_images(
    p1: str | bytes | pathlib.Path | io.BytesIO,
    p2: str | bytes | pathlib.Path | io.BytesIO,
) -> bool:
    with (
        Image.open(p1) as i1,
        Image.open(p2) as i2,
    ):
        return compare_images(i1, i2)


def get_img_data_from_path(p: pathlib.Path) -> list[typing.Any]:
    with Image.open(p) as img:
        return list(img.getdata())
