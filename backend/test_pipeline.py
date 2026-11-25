"""Self-check for reference-image validation. Run: python -m backend.test_pipeline"""

import base64
from io import BytesIO

from PIL import Image

from .constants import MAX_REFERENCE_IMAGE_BYTES
from .pipeline import decode_reference_image, fit_reference_image


def _b64(fmt: str, size=(64, 32), mode="RGB") -> str:
    buf = BytesIO()
    Image.new(mode, size, "red").save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


def _rejects(data: str, needle: str) -> None:
    try:
        decode_reference_image(data)
    except ValueError as exc:
        assert needle in str(exc), exc
    else:
        raise AssertionError(f"expected rejection: {needle}")


def main() -> None:
    # accepted: plain base64, data-URL prefix, RGBA converted to RGB
    assert decode_reference_image(_b64("PNG")).size == (64, 32)
    assert decode_reference_image("data:image/jpeg;base64," + _b64("JPEG")).mode == "RGB"
    assert decode_reference_image(_b64("WEBP", mode="RGBA")).mode == "RGB"

    # rejected at the trust boundary
    _rejects("not base64!!", "not valid base64")
    _rejects(base64.b64encode(b"hello").decode(), "could not be decoded")
    _rejects(_b64("GIF"), "Unsupported")
    _rejects(base64.b64encode(b"\0" * (MAX_REFERENCE_IMAGE_BYTES + 1)).decode(), "10 MB")

    # crop to target aspect
    assert fit_reference_image(Image.new("RGB", (100, 50)), (40, 40)).size == (40, 40)

    print("ok")


if __name__ == "__main__":
    main()
