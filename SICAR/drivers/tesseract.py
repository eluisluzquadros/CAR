# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for SICAR text captchas."""

import re
import pytesseract
from PIL import Image
import numpy as np
import cv2
import os
from SICAR.drivers.captcha import Captcha

class Tesseract(Captcha):
    """Implementation of the Captcha driver using Tesseract OCR."""

    _custom_config = (
        "-l eng "
        "--psm 7 "
        "--oem 3 "
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )

    def _process_image(self, img_array: np.ndarray, debug: bool = True) -> np.ndarray:
        """Process image with debug output."""
        # Create debug directory
        if debug:
            os.makedirs('debug', exist_ok=True)

        # Convert to HSV
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        if debug:
            cv2.imwrite('debug/1_hsv.png', cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR))

        # Remove red line
        # Define broader red ranges
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([180, 255, 255])

        # Create masks
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        if debug:
            cv2.imwrite('debug/2_red_mask.png', red_mask)

        # Remove red components
        result = img_array.copy()
        result[red_mask > 0] = [255, 255, 255]
        if debug:
            cv2.imwrite('debug/3_no_red.png', cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        # Convert to grayscale
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        if debug:
            cv2.imwrite('debug/4_gray.png', gray)

        # Apply adaptive thresholding
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        if debug:
            cv2.imwrite('debug/5_adaptive.png', adaptive)

        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, kernel)
        if debug:
            cv2.imwrite('debug/6_cleaned.png', cleaned)

        # Invert if needed (text should be black on white)
        if np.mean(cleaned) > 127:
            cleaned = cv2.bitwise_not(cleaned)
        if debug:
            cv2.imwrite('debug/7_final.png', cleaned)

        return cleaned

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from the captcha image."""
        try:
            # Convert PIL to numpy array
            img_array = np.array(captcha)

            # Process image
            processed = self._process_image(img_array)

            # Convert back to PIL
            pil_processed = Image.fromarray(processed)

            # Try multiple PSM modes
            configs = [
                '--psm 7',  # Treat as single line of text
                '--psm 8',  # Treat as single word
                '--psm 13'  # Raw line with default OCR
            ]

            results = []
            for config in configs:
                full_config = f"{config} -l eng --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                text = pytesseract.image_to_string(pil_processed, config=full_config)
                cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                if cleaned:
                    results.append(cleaned)

            # Get the most common result or the first non-empty one
            if results:
                from collections import Counter
                counter = Counter(results)
                result = counter.most_common(1)[0][0]
                return result

            return ""

        except Exception as e:
            self._logger.error(f"Error in OCR: {str(e)}")
            return ""