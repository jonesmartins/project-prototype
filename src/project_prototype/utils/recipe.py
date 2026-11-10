import io
import typing


class Recipe:
    def __init__(self) -> None:
        pass


class JpegBuilder:
    def __init__(self) -> None:
        pass

    def compress(self, image_buffer: io.BytesIO, quality: int):
        pass


class RecipeBuilder:
    def __init__(self) -> None:
        pass

    jpeg = JpegBuilder()

    def with_whatever(self, whatever: typing.Any) -> "RecipeBuilder":
        return self
