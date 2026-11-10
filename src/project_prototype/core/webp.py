from project_prototype.core.base_classes import Settings

WebpQuality = int  # 0..100 (default=80)


class WebpSettings(Settings):
    method: int = 4
    exact: bool = False


# May contain multiple frames
class WebpImage:
    def __init__(self) -> None:
        pass
