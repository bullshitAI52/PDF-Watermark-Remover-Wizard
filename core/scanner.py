# -*- coding: utf-8 -*-
import unicodedata


def normalize_text(value):
    """Normalize text so matching survives spacing and punctuation differences."""
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    chars = []
    for ch in normalized:
        category = unicodedata.category(ch)
        if category.startswith(("P", "Z", "C")):
            continue
        chars.append(ch)
    return "".join(chars)


def estimate_rotation(*_args, **_kwargs):
    """Compatibility shim for older engine experiments."""
    return 0.0


def apply_matrix(point, matrix=None):
    """Apply a 2D affine matrix (a, b, c, d, e, f) to a point."""
    if matrix is None:
        return point

    x, y = point
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)
