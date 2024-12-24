# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for SICAR text captchas."""

import re
import pytesseract
from PIL import Image
import numpy as np
import cv2

from SICAR.drivers.captcha import Captcha

class Tesseract(Captcha):
    """Implementation of the Captcha driver using Tesseract OCR."""

    # Tesseract configuration for better text recognition
    _custom_config = (
        "-l eng "  # Use English language
        "--psm 7 "  # Treat as single line
        "--oem 3 "  # LSTM OCR Engine
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "  # Allowed chars
    )

    def _remove_red_line(self, img_array: np.ndarray) -> np.ndarray:
        """Remove the red strikethrough line."""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)

        # Define red color range in HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        # Create masks for red color
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2

        # Remove red line
        img_array[mask > 0] = [255, 255, 255]  # Set red pixels to white
        
        return img_array

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from the captcha image."""
        # Convert to numpy array
        img_array = np.array(captcha)

        # Remove red strikethrough line
        cleaned = self._remove_red_line(img_array)

        # Convert to grayscale
        gray = cv2.cvtColor(cleaned, cv2.COLOR_RGB2GRAY)

        # Apply threshold to get black text
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Convert back to PIL Image
        processed = Image.fromarray(binary)

        # OCR
        text = pytesseract.image_to_string(
            processed,
            config=self._custom_config
        )

        # Clean up the result
        cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())

        return cleaned_text