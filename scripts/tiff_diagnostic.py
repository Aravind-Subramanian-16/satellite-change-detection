from PIL import Image
import numpy as np
import io

# Let's see if PIL can read a multi-page TIFF or multi-band TIFF
# Actually, an easier Sentinel Hub format for multiple bands without TIFF is `image/png` returning two different images in `application/tar`.
# But wait, Sentinel Hub allows "image/tiff".
