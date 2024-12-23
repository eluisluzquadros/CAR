# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for SICAR captchas."""

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
                # Install Tesseract on Colab if needed
                subprocess.run(
                    ['apt-get', 'install', '-y', 'tesseract-ocr'],
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                self._logger.error(f"Failed to setup Tesseract: {str(e)}")
                raise

    def _preprocess_captcha(self, image: Image.Image) -> Image.Image:
        """Enhanced preprocessing for SICAR captchas."""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            denoised = cv2.fastNlMeansDenoising(binary)
            
            # Morphological operations to clean up
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to PIL Image
            processed = Image.fromarray(cleaned)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(2.0)
            
            # Resize image to be larger (helps OCR)
            processed = processed.resize((processed.width * 2, processed.height * 2), Image.Resampling.LANCZOS)
            
            return processed
            
        except Exception as e:
            self._logger.error(f"Error in image preprocessing: {str(e)}")
            raise CaptchaProcessingError("Failed to preprocess image") from e

    def _process_text(self, text: str) -> str:
        """Clean up OCR results."""
        # Remove any whitespace
        text = text.strip()
        
        # Remove any non-alphanumeric characters
        text = re.sub(r'[^A-Za-z0-9]+', '', text)
        
        # Convert to uppercase since SICAR captchas are uppercase
        text = text.upper()
        
        return text

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved accuracy."""
        try:
            # Preprocess the image
            processed = self._preprocess_captcha(captcha)
            
            # Save intermediate result for debugging
            processed.save("processed_captcha.png")
            
            # OCR Configuration
            custom_config = (
                '--psm 8 '  # Single word mode
                '--oem 3 '  # LSTM only
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
                'tessedit_minimal_confidence=60'
            )
            
            # Multiple OCR attempts with different preprocessing
            attempts = [
                lambda: processed,
                lambda: processed.filter(ImageFilter.SHARPEN),
                lambda: ImageEnhance.Contrast(processed).enhance(1.5),
                lambda: ImageEnhance.Brightness(processed).enhance(1.2)
            ]
            
            for attempt_func in attempts:
                try:
                    img = attempt_func()
                    text = pytesseract.image_to_string(
                        img,
                        config=custom_config,
                    )
                    cleaned = self._process_text(text)
                    if len(cleaned) >= 4:  # SICAR captchas are usually 5 chars
                        return cleaned
                except Exception as e:
                    self._logger.warning(f"OCR attempt failed: {str(e)}")
                    continue
            
            raise CaptchaProcessingError("No valid text detected in captcha")
            
        except Exception as e:
            self._logger.error(f"Tesseract OCR failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e