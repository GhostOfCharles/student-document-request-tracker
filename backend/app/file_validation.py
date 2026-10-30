"""Bounded subprocess inspection: no document parser runs inside a web worker."""

import sys
import warnings
from pathlib import Path
from PIL import Image
from pypdf import PdfReader


def inspect(path, mime):
    if mime == "application/pdf":
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 100:
            raise ValueError("Encrypted or oversized PDF structure")
        # Walk the bounded page tree without extracting arbitrary content streams.
        for page in reader.pages:
            _ = page.mediabox
    else:
        Image.MAX_IMAGE_PIXELS = 20_000_000
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as im:
            if im.format != {"image/png": "PNG", "image/jpeg": "JPEG"}[mime]:
                raise ValueError("Image signature does not match format")
            if im.width * im.height > 20_000_000:
                raise ValueError("Image exceeds pixel limit")
            im.verify()
        with Image.open(path) as im:
            im.load()


if __name__ == "__main__":
    try:
        inspect(sys.argv[1], sys.argv[2])
    except Exception:
        sys.exit(1)
