def is_valid_bounding_box(bb, min_size=50):
    _, _, w, h = bb  # Tách các giá trị x, y, w, h
    return w >= min_size and h >= min_size
