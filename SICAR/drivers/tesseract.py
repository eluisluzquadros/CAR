# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for SICAR captchas."""

import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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

    def _remove_noise(self, image):
        """Remove noise using morphological operations."""
        kernel = np.ones((2,2), np.uint8)
        opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        return closing

    def _preprocess_captcha(self, image: Image.Image) -> Image.Image:
        """Enhanced preprocessing specifically for SICAR captchas."""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Invert image (since SICAR captchas are white on black)
            inverted = cv2.bitwise_not(gray)
            
            # Apply thresholding
            _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            denoised = self._remove_noise(binary)
            
            # Convert back to PIL Image
            processed = Image.fromarray(denoised)
            
            # Resize image (2x) to help OCR
            width, height = processed.size
            processed = processed.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
            
            # Add padding
            border = 20
            processed = ImageOps.expand(processed, border=border, fill='white')
            
            # Save debug image
            processed.save('debug_processed.png')
            
            return processed
            
        except Exception as e:
            self._logger.error(f"Error in image preprocessing: {str(e)}")
            raise CaptchaProcessingError("Failed to preprocess image") from e

    def _process_text(self, text: str) -> str:
        """Clean up OCR results."""
        # Remove any whitespace and non-alphanumeric characters
        text = re.sub(r'[^A-Za-z0-9]+', '', text.strip())
        
        # Convert to uppercase (SICAR captchas are uppercase)
        text = text.upper()
        
        return text

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved accuracy."""
        try:
            # Save original for debugging
            captcha.save('debug_original.png')
            
            # Preprocess the image
            processed = self._preprocess_captcha(captcha)
            
            # OCR Configuration tuned for SICAR captchas
            custom_config = (
                '--psm 7 '  # Treat image as single line of text
                '--oem 3 '  # Use LSTM OCR Engine
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
                'tessedit_do_invert=0 '
                'tessedit_min_confidence=60'
            )
            
            # Try multiple preprocessing variations
            attempts = [
                lambda: processed,
                lambda: processed.filter(ImageFilter.SHARPEN),
                lambda: ImageEnhance.Contrast(processed).enhance(2.0),
                lambda: processed.filter(ImageFilter.EDGE_ENHANCE_MORE),
            ]
            
            for i, attempt_func in enumerate(attempts):
                try:
                    img = attempt_func()
                    img.save(f'debug_attempt_{i}.png')  # Save each attempt for debugging
                    
                    text = pytesseract.image_to_string(
                        img,
                        config=custom_config,
                    )
                    
                    cleaned = self._process_text(text)
                    self._logger.debug(f"Attempt {i + 1}: Raw='{text}', Cleaned='{cleaned}'")
                    
                    if len(cleaned) >= 4:  # SICAR captchas are usually 5 chars
                        return cleaned
                        
                except Exception as e:
                    self._logger.warning(f"OCR attempt {i + 1} failed: {str(e)}")
                    continue
            
            raise CaptchaProcessingError("No valid text detected in captcha")
            
        except Exception as e:
            self._logger.error(f"Tesseract OCR failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e