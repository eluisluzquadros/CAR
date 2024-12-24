# SICAR/drivers/tesseract.py
"""
Tesseract OCR Driver Module.

This module provides an implementation of the Captcha driver using Tesseract OCR,
specifically optimized for SICAR's strikethrough captchas.
"""

import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2

from SICAR.drivers.captcha import Captcha

class Tesseract(Captcha):
    """Implementation of the Captcha driver using Tesseract OCR."""

    # Configuration for Tesseract
    _custom_config = (
        "-l eng "          # Use English language
        "--psm 7 "         # Treat image as single line of text
        "--oem 3 "         # Use LSTM OCR Engine
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # Only allow these characters
    )

    def get_captcha(self, captcha: Image) -> str:
        """
        Extract text from the provided captcha image.

        Args:
            captcha (Image): The captcha image.

        Returns:
            str: The extracted text from the captcha.
        """
        # Convert to numpy array for OpenCV processing
        img_array = np.array(captcha)
        
        # Convert to HSV to handle red strikethrough
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # Define red color ranges in HSV
        lower_red = np.array([0, 120, 70])
        upper_red = np.array([10, 255, 255])
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])
        
        # Create mask for red color
        mask1 = cv2.inRange(hsv, lower_red, upper_red)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        # Combine masks and invert
        red_mask = cv2.bitwise_not(mask1 + mask2)
        
        # Apply mask to remove red strikethrough
        result = cv2.bitwise_and(img_array, img_array, mask=red_mask)
        
        # Convert to grayscale
        gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        
        # Apply threshold to get black text
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL Image
        processed = Image.fromarray(binary)
        
        # Extract text
        text = pytesseract.image_to_string(
            processed,
            config=self._custom_config,
        )
        
        # Clean up the result
        cleaned = re.sub(r'[^A-Z0-9]+', '', text.upper())
        
        return cleaned