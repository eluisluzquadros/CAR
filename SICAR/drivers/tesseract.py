# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for strikethrough captchas."""

import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import os
import subprocess
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Tesseract(Captcha):
    def __init__(self):
        super().__init__()
        self._setup_tesseract()
        
    def _setup_tesseract(self):
        """Setup Tesseract if needed."""
        try:
            pytesseract.get_tesseract_version()
        except:
            try:
                subprocess.run(
                    ['apt-get', 'install', '-y', 'tesseract-ocr'],
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                self._logger.error(f"Failed to setup Tesseract: {str(e)}")
                raise

    def _remove_strikethrough(self, image_array: np.ndarray) -> np.ndarray:
        """Remove red strikethrough line."""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(image_array, cv2.COLOR_RGB2HSV)
        
        # Define red color range (both upper and lower ranges for red in HSV)
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        # Create masks for red color
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        # Invert mask to get everything but red
        mask = cv2.bitwise_not(red_mask)
        
        # Apply mask to original image
        result = cv2.bitwise_and(image_array, image_array, mask=mask)
        
        return result

    def _preprocess_captcha(self, image: Image.Image) -> Image.Image:
        """Preprocess captcha image to remove strikethrough and enhance text."""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Remove red strikethrough
            cleaned = self._remove_strikethrough(img_array)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cleaned, cv2.COLOR_RGB2GRAY)
            
            # Apply thresholding to get black text
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            processed = Image.fromarray(binary)
            
            # Resize to make text clearer
            processed = processed.resize(
                (processed.width * 2, processed.height * 2),
                Image.Resampling.LANCZOS
            )
            
            # Save debug image
            processed.save('debug_processed.png')
            
            return processed
            
        except Exception as e:
            self._logger.error(f"Error in image preprocessing: {str(e)}")
            raise CaptchaProcessingError("Failed to preprocess image") from e

    def _process_text(self, text: str) -> str:
        """Clean up OCR results."""
        # Remove any non-alphanumeric characters
        text = re.sub(r'[^A-Za-z0-9]+', '', text.strip())
        
        # Convert to uppercase
        text = text.upper()
        
        return text

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from strikethrough captcha."""
        try:
            # Save original for debugging
            captcha.save('debug_original.png')
            
            # Preprocess the image
            processed = self._preprocess_captcha(captcha)
            
            # OCR Configuration
            custom_config = (
                '--psm 7 '  # Treat image as single line of text
                '--oem 3 '  # LSTM OCR Engine
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
                'tessedit_do_invert=0'
            )
            
            # Try multiple preprocessing variations
            attempts = [
                lambda: processed,
                lambda: processed.filter(ImageFilter.SHARPEN),
                lambda: ImageEnhance.Contrast(processed).enhance(2.0),
                lambda: processed.filter(ImageFilter.EDGE_ENHANCE_MORE)
            ]
            
            for i, attempt_func in enumerate(attempts):
                try:
                    img = attempt_func()
                    img.save(f'debug_attempt_{i}.png')
                    
                    text = pytesseract.image_to_string(
                        img,
                        config=custom_config
                    )
                    
                    cleaned = self._process_text(text)
                    self._logger.debug(f"Attempt {i + 1}: Raw='{text}', Cleaned='{cleaned}'")
                    
                    if len(cleaned) >= 4:
                        return cleaned
                        
                except Exception as e:
                    self._logger.warning(f"OCR attempt {i + 1} failed: {str(e)}")
                    continue
            
            raise CaptchaProcessingError("No valid text detected in captcha")
            
        except Exception as e:
            self._logger.error(f"Tesseract OCR failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e