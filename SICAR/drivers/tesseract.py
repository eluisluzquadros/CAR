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

    def _remove_red(self, image: np.ndarray) -> np.ndarray:
        """Remove red components from image."""
        # Ensure image is in correct format
        if len(image.shape) != 3:
            return image
            
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Define red color ranges
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        # Create mask for red pixels
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Create output image
        result = image.copy()
        result[mask > 0] = [255, 255, 255]
        
        return result

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from the captcha image."""
        try:
            # Convert to numpy array
            img_array = np.array(captcha)
            
            # Create debug directory
            os.makedirs('debug', exist_ok=True)
            
            # Save original numpy array
            cv2.imwrite('debug/1_original.png', cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
            
            # Remove red
            no_red = self._remove_red(img_array)
            cv2.imwrite('debug/2_no_red.png', cv2.cvtColor(no_red, cv2.COLOR_RGB2BGR))
            
            # Convert to grayscale
            gray = cv2.cvtColor(no_red, cv2.COLOR_RGB2GRAY)
            cv2.imwrite('debug/3_gray.png', gray)
            
            # Apply threshold
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            cv2.imwrite('debug/4_binary.png', binary)
            
            # Convert back to PIL Image
            final = Image.fromarray(binary)
            
            # Try OCR
            text = pytesseract.image_to_string(
                final,
                config=self._custom_config
            )
            
            # Clean up the text
            result = re.sub(r'[^A-Z0-9]', '', text.upper())
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error in OCR: {str(e)}")
            import traceback
            self._logger.error(traceback.format_exc())
            return ""