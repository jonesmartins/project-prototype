from __future__ import annotations

import dataclasses
import io
import pathlib
from tempfile import mkstemp, mktemp

from PIL import Image
from PIL.ImageShow import show
import pytest
import rich
from hypothesis import given
from hypothesis import strategies as st

from project_prototype.core.jpeg import JpegImage, JpegQuality, JpegSettings
from tests.helpers.image import TEST_IMAGES_DIRECTORY

# def test_copy_input_image_to_output_path():
#     pass


# def copy_input_image_to_output_path(input_path: Path, output_path: Path) -> None:


# def test_generate_compression_qualities():
#     pass


# def test_compress():
#     pass


# def compress(
#     image_path: Path,
#     qualities: list[int],
#     extra: int,
# ) -> None:


# def same_image_data(p1: Path, p2: Path) -> bool:
#     data1 = get_image_data(p1)
#     data2 = get_image_data(p2)
#     is_same = data1 == data2
#     if not is_same:
#         show_diff(data1, data2)
#     #     print(data1)
#     #     print(data2)
#     return is_same


# @pytest.mark.skip
# @pytest.mark.parametrize(
#     "input_path",
#     SMALL_TEST_IMAGES_DIRECTORY.iterdir(),
# )
# def test_1(input_path: pathlib.Path):
#     input_path
#     qualities = [95, 95]
#
#     jpeg_image = JpegImage.from_path(input_path)
#
#     settings = JpegSettings()
#     jpeg_image.compress_repeatedly(qualities=qualities, settings=settings)


@given(st.lists(st.integers(1, 100), min_size=1))
def test_valid_jpeg_qualities(qualities: list[int]) -> None:
    jpeg_qualities = [JpegQuality(q) for q in qualities]

    assert all(
        q == jq.value for q, jq in zip(qualities, jpeg_qualities, strict=True)
    )


@pytest.mark.parametrize(
    "path",
    list(pathlib.Path(__file__).parent.joinpath("images", "small").iterdir()),
)
def test_create_jpeg_image(
    path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    jpeg_image = JpegImage.from_path(path)

    assert jpeg_image.size > 0

    with tmp_path.joinpath("foo.jpeg").open("wb") as fp:
        jpeg_image.save_to(fp)


@pytest.mark.parametrize(
    "path",
    list(pathlib.Path(__file__).parent.joinpath("images", "small").iterdir()),
)
def test_compress_jpeg_image_not_once(
    path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    jpeg_image = JpegImage.from_path(path)

    settings = JpegSettings()
    jpeg_image.compress_repeatedly(
        qualities=[],
        settings=settings,
    )

    # with pathlib.Path.cwd().joinpath("poo.jpeg").open(mode="wb") as fp:
    #     jpeg_image.save_to(fp)


@pytest.mark.skip
@pytest.mark.parametrize(
    "path",
    list(pathlib.Path(__file__).parent.joinpath("images", "small").iterdir()),
)
def test_compress_jpeg(
    path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    jpeg_image = JpegImage.from_path(path)
    original_size = jpeg_image._image_buffer.getbuffer().nbytes

    settings = JpegSettings()
    jpeg_image.compress_repeatedly(
        qualities=[JpegQuality(25)] * 10,
        settings=settings,
    )

    final_size = jpeg_image._image_buffer.getbuffer().nbytes
    assert original_size != final_size

    with Image.open(jpeg_image._image_buffer) as img:
        # show(img)
        assert img.format is not None
        assert img.format.lower() == "jpeg"

    # with pathlib.Path.cwd().joinpath("poo.jpeg").open(mode="wb") as fp:
    #     jpeg_image.save_to(fp)
    #


@pytest.mark.skip
@pytest.mark.parametrize(
    "path",
    list(pathlib.Path(__file__).parent.joinpath("images", "small").iterdir()),
)
def test_compress_jpeg_with_flips(
    path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    jpeg_image = JpegImage.from_path(path)
    settings = JpegSettings()
    jpeg_image.compress_repeatedly_with_flips(
        qualities=[JpegQuality(25)] * 100,
        settings=settings,
    )
    with Image.open(jpeg_image._image_buffer) as img:
        show(img)
        assert img.format is not None
        assert img.format.lower() == "jpeg"


@pytest.mark.parametrize(
    "path",
    list(pathlib.Path(__file__).parent.joinpath("images", "small").iterdir()),
)
def test_compress_jpeg_with_crop(
    path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    jpeg_image = JpegImage.from_path(path)
    settings = JpegSettings()
    jpeg_image.compress_repeatedly_with_crop(
        qualities=[JpegQuality(25)] * 100,
        settings=settings,
    )
    with Image.open(jpeg_image._image_buffer) as img:
        show(img)
        assert img.format is not None
        assert img.format.lower() == "jpeg"
