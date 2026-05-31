import unittest

import numpy as np

from image_mode_pic_watermark.raster_cleaner import clean_image, process_page_task


class RasterCleanerTests(unittest.TestCase):
    def test_clean_image_strict_mode_without_corners_returns_image(self):
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        cleaned = clean_image(img, strict_corner_mode=True)
        self.assertEqual(cleaned.shape, img.shape)
        self.assertTrue(np.array_equal(cleaned, img))

    def test_process_page_task_uses_page_parity_for_corner_selection(self):
        img = np.zeros((20, 20, 3), dtype=np.uint8)
        img[0:4, 0:4] = [220, 220, 220]

        _, cleaned_rgb = process_page_task((0, img, False, 0, ["tl"], ["br"], True, (25, 25), True))
        self.assertTrue(np.all(cleaned_rgb[0:4, 0:4] == 255))


if __name__ == "__main__":
    unittest.main()
