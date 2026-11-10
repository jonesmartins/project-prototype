import typing

from project_prototype.core.base_classes import Settings

AvifQuality = int  # [0..100] (default=75)


## May contain multiple frames
class AvifSettings(Settings):
    subsampling: str = "4:2:0"  # 4:0:0, 4:2:0, 4:2:2, 4:4:4
    speed: int = 6  # [0..10] (default=6)
    yuv_range: typing.Literal["full", "limited"] = "full"


class AvifImage:
    pass
