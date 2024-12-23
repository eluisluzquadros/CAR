# SICAR/drivers/tesseract.py
"""Tesseract OCR Driver with improved image processing and error handling."""

import re
import pytesseract
from PIL import Image
import os
import subprocess
import sys
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError
import logging

class Tesseract(Captcha):
    def __init__(self):
        super().__init__()
        self._setup_tesseract()
        
    def _setup_tesseract(self):
        """Setup Tesseract with better error handling."""
        try:
            # Check if tesseract is already installed
            pytesseract.get_tesseract_version()
            self._logger.debug("Tesseract already installed")
            
        except Exception as e:
            self._logger.warning(f"Tesseract not found: {str(e)}")
            try:
                # For Google Colab environment
                if 'COLAB_GPU' in os.environ:
                    self._logger.info("Installing Tesseract in Colab environment")
                    subprocess.run(
                        ['apt-get', 'install', '-y', 'tesseract-ocr'],
                        check=True,
                        capture_output=True
                    )
                else:
                    self._logger.error("Tesseract not installed and not in Colab environment")
                    raise CaptchaProcessingError("Tesseract OCR not installed")
                    
            except subprocess.CalledProcessError as e:
                self._logger.error(f"Failed to install Tesseract: {str(e)}")
                raise CaptchaProcessingError("Failed to install Tesseract OCR") from e

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with robust error handling."""
        try:
            # Process the image
            processed_image = self._process_captcha(captcha)
            
            # Configure Tesseract for better captcha recognition
            custom_config = (
                '-l eng '  # English language
                '--psm 7 '  # Assume single line of text
                '--oem 1 '  # LSTM OCR Engine
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            )
            
            # Extract text
            text = pytesseract.image_to_string(
                processed_image,
                config=custom_config,
            ).strip()
            
            # Clean and validate result
            result = re.sub('[^A-Za-z0-9]+', '', text)
            
            self._logger.debug(f"Raw OCR result: '{text}', Cleaned result: '{result}'")
            
            if not result:
                raise CaptchaProcessingError("No text detected in captcha")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Tesseract OCR failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e