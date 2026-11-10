import dataclasses
import rich
import io
import typing
from collections.abc import Iterable, Sequence

from PIL import Image
from rich.table import dataclass

T = typing.TypeVar("T")


class Quality:
    def __init__(self, value: int | str) -> None:
        self.value = value


@dataclasses.dataclass(frozen=True)
class Settings:
    format: str

    def as_dict(self) -> dict[str, typing.Any]:
        return {
            field.name: value
            for field in dataclasses.fields(self)
            if (value := self.__getattribute__(field.name)) is not None
        }


def compress_repeatedly(
    image_buffer: io.BytesIO,
    qualities: Sequence[Quality],
    settings: Settings,
) -> None:
    kwargs = settings.as_dict()
    rich.print(kwargs)

    previous_size = -1
    for i, quality in enumerate(qualities):
        with Image.open(image_buffer) as img:
            img.load()

            size = image_buffer.getbuffer().nbytes
            assert size > 0, (
                size,
                i,
                quality.value,
            )
            assert size != previous_size, (
                size,
                previous_size,
                i,
                quality.value,
            )

            image_buffer.seek(0)
            image_buffer.truncate()
            img.save(
                image_buffer,
                quality=quality.value,
                **kwargs,
            )
            previous_size = size


class SomeProtocol(typing.Protocol):
    @classmethod
    def from_file(cls, fp: typing.IO[bytes]) -> typing.Self: ...

    def save_to(self, fp: typing.IO[bytes]) -> int: ...
