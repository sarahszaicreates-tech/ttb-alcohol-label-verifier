import unittest
from io import BytesIO

from PIL import Image

from vesper.ocr import preprocess_image


class OCRPreprocessingTests(unittest.TestCase):
    def test_small_image_is_upscaled_and_grayscaled(self):
        source = Image.new("RGB", (400, 800), "white")
        data = BytesIO()
        source.save(data, format="PNG")
        output = preprocess_image(data.getvalue())
        self.assertEqual(output.mode, "L")
        self.assertEqual(max(output.size), 1600)


if __name__ == "__main__":
    unittest.main()

