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

    def _remove_red(self, image: Image.Image) -> Image.Image:
        """Remove red components from image."""
        try:
            # Convert RGBA to RGB if needed
            if image.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                # Paste using alpha channel as mask
                background.paste(image, mask=image.split()[3])
                image = background
            
            # Convert to RGB if not already
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to HSV
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # Define red ranges
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            
            # Create mask for red pixels
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
            
            # Save debug images
            os.makedirs('debug', exist_ok=True)
            cv2.imwrite('debug/mask.png', mask)
            
            # Create output image
            result = img_array.copy()
            result[mask > 0] = [255, 255, 255]
            
            # Convert back to PIL
            return Image.fromarray(result)
            
        except Exception as e:
            self._logger.error(f"Error removing red: {str(e)}")
            import traceback
            self._logger.error(traceback.format_exc())
            return image

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from the captcha image."""
        try:
            # Save original
            os.makedirs('debug', exist_ok=True)
            captcha.save('debug/1_original.png')
            
            # Remove red
            no_red = self._remove_red(captcha)
            no_red.save('debug/2_no_red.png')
            
            # Convert to grayscale
            gray = no_red.convert('L')
            gray.save('debug/3_gray.png')
            
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)
            enhanced.save('debug/4_enhanced.png')
            
            # Try OCR with different preprocessing
            attempts = [
                enhanced,  # Enhanced grayscale
                gray,     # Original grayscale
                no_red    # Color without red
            ]
            
            for i, img in enumerate(attempts):
                try:
                    text = pytesseract.image_to_string(
                        img,
                        config=self._custom_config
                    )
                    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                    if cleaned:
                        return cleaned
                except Exception as e:
                    self._logger.warning(f"OCR attempt {i+1} failed: {str(e)}")
                    continue
            
            return ""
            
        except Exception as e:
            self._logger.error(f"Error in OCR: {str(e)}")
            import traceback
            self._logger.error(traceback.format_exc())
            return ""