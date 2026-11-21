"""Optional CPU-only visual metrics for local dataset review.

Perceptual matches and blur scores are *review suggestions*, not evidence of
identity or a reason to delete data. Never writes the source image.
"""
from pathlib import Path

MAX_PIXELS = 40_000_000
NEAR_HASH_DISTANCE = 5
BLUR_SCORE_THRESHOLD = 80.0


def visual_metrics(path):
    """Return (16-digit dHash, Laplacian variance, possible_blur), or Nones.

    A blank/low-contrast image has no useful perceptual hash for matching.
    Work on a grayscale thumbnail to bound memory/CPU after checking pixels.
    """
    try:
        from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError
    except ImportError:
        return None, None, None
    try:
        with Image.open(Path(path)) as source:
            w, h = source.size
            if w <= 0 or h <= 0 or w * h > MAX_PIXELS:
                return None, None, None
            source.seek(0)
            gray = source.convert("L")
            small = gray.resize((9, 8), Image.Resampling.BILINEAR)
            pixels = list(small.getdata())
            dhash = 0
            for y in range(8):
                for x in range(8):
                    dhash = (dhash << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
            # Uniform/grayscale-degenerate images otherwise match unrelated files.
            spread = ImageStat.Stat(small).stddev[0]
            fingerprint = f"{dhash:016x}" if spread >= 12 else None
            thumb = gray.resize((128, 128), Image.Resampling.BILINEAR)
            # A bounded, 8-neighbour Laplacian. Values are centered to avoid
            # negative clipping; score is a heuristic and depends on content.
            response = thumb.filter(ImageFilter.Kernel(
                (3, 3), (-1, -1, -1, -1, 8, -1, -1, -1, -1), scale=1, offset=128
            ))
            score = round(ImageStat.Stat(response).var[0], 2)
            possible_blur = bool(ImageStat.Stat(thumb).stddev[0] >= 15
                                 and score < BLUR_SCORE_THRESHOLD)
            return fingerprint, score, possible_blur
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombError):
        return None, None, None


def near_match(a, b):
    """Bounded dHash Hamming-distance check; exact matches handled separately."""
    if not a or not b or len(a) != 16 or len(b) != 16:
        return False
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count() <= NEAR_HASH_DISTANCE
    except ValueError:
        return False
