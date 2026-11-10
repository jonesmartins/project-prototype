import io

from PIL import Image


def save_loaded_image_to_buffer(
    img: Image.Image,
    buf: io.BytesIO,
    *args,
    **kwargs,
) -> None:
    # Empty buffer
    buf.seek(0)
    buf.truncate()

    # Write to buffer
    img.save(buf, *args, **kwargs)


def save_loaded_image_to_buffer_as_jpeg(
    img: Image.Image,
    buf: io.BytesIO,
    quality: int,
    *args,
    **kwargs,
) -> None:
    save_loaded_image_to_buffer(
        img,
        buf,
        *args,
        quality=quality,
        format="JPEG",
        **kwargs,
    )


def save_image_in_buffer_as_jpeg(
    image_buffer: io.BytesIO,
    quality: int,
) -> None:
    with Image.open(image_buffer) as img:
        img.load()
        save_loaded_image_to_buffer_as_jpeg(
            img,
            image_buffer,
            quality=quality,
        )


def rotate_and_save_jpeg_in_buffer(
    image_buffer: io.BytesIO,
    quality: int,
) -> None:
    with Image.open(image_buffer) as img:
        rotated_img = img.transpose(method=Image.Transpose.ROTATE_90)
        save_loaded_image_to_buffer_as_jpeg(
            rotated_img,
            image_buffer,
            quality=quality,
        )


def remove_from_image(
    image: Image.Image,
    *,
    top_rows: int = 0,
    bottom_rows: int = 0,
    left_columns: int = 0,
    right_columns: int = 0,
) -> Image.Image:
    bounding_box = (
        left_columns,
        top_rows,
        image.width - right_columns,
        image.height - bottom_rows,
    )
    return image.crop(bounding_box)


def remove_from_image_in_buffer(
    image_buffer: io.BytesIO,
    *,
    top_rows: int = 0,
    bottom_rows: int = 0,
    left_columns: int = 0,
    right_columns: int = 0,
) -> None:
    with Image.open(image_buffer) as image:
        cropped_image = remove_from_image(
            image,
            top_rows=top_rows,
            bottom_rows=bottom_rows,
            left_columns=left_columns,
            right_columns=right_columns,
        )
        save_loaded_image_to_buffer(
            cropped_image,
            image_buffer,
            format="PPM",
        )


def add_to_image(
    image: Image.Image,
    *,
    top_rows: int = 0,
    left_columns: int = 0,
    bottom_rows: int = 0,
    right_columns: int = 0,
) -> Image.Image:
    new_size = (
        image.width + left_columns + right_columns,
        image.height + top_rows + bottom_rows,
    )
    # print(f"New Size: {new_size}")
    result = Image.new(image.mode, size=new_size)
    result.paste(image, box=(left_columns, top_rows))
    # print(f"After paste bbox: {result.getbbox()}")
    return result


def add_to_image_in_buffer(
    image_buffer: io.BytesIO,
    *,
    top_rows: int = 0,
    left_columns: int = 0,
    bottom_rows: int = 0,
    right_columns: int = 0,
) -> None:
    with Image.open(image_buffer) as img:
        result = add_to_image(
            img,
            top_rows=top_rows,
            bottom_rows=bottom_rows,
            left_columns=left_columns,
            right_columns=right_columns,
        )
        save_loaded_image_to_buffer(
            result,
            image_buffer,
            format="PPM",
        )
