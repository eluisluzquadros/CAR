"""Tesseract OCR Driver with Colab compatibility."""

import re
import pytesseract
from PIL import Image
import os
import subprocess
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Tesseract(Captcha):
    def __init__(self):
        super().__init__()
        self._setup_tesseract()
        
    def _setup_tesseract(self):
        """Setup Tesseract if needed (especially for Colab)."""
        try:
            pytesseract.get_tesseract_version()
        except:
            try:
                # Instalar Tesseract no Colab se necessário
                subprocess.run(
                    ['apt-get', 'install', '-y', 'tesseract-ocr'],
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                self._logger.error(f"Failed to setup Tesseract: {str(e)}")
                raise

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved error handling."""
        try:
            processed_image = self._process_captcha(captcha)
            
            # Configuração mais robusta do Tesseract
            config = r'-l eng --psm 7 --oem 1 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            
            text = pytesseract.image_to_string(
                processed_image,
                config=config,
            )
            
            # Limpar e validar resultado
            result = re.sub('[^A-Za-z0-9]+', '', text)
            
            if not result:
                raise CaptchaProcessingError("No text detected in captcha")
                
            return result
            
        except Exception as e:
            self._logger.error(f"Error in Tesseract OCR: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e