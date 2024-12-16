"""Captcha Abstract Base Class with improved error handling."""

from abc import ABC, abstractmethod
import tempfile
from PIL import Image
import numpy as np
import cv2
import logging
from typing import Optional

class CaptchaProcessingError(Exception):
    """Exception raised when captcha processing fails."""
    pass

class Captcha(ABC):
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_captcha(self, captcha: Image) -> str:
        """Abstract method to get the Captcha value."""
        pass

    def _png_to_jpg(self, captcha: Image) -> np.ndarray:
        """Convert PNG to JPG with improved error handling."""
        try:
            # Converter diretamente para array numpy
            img_array = np.array(captcha.convert('RGB'))
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        except Exception as e:
            self._logger.error(f"Error converting image: {str(e)}")
            raise CaptchaProcessingError("Failed to convert image format") from e

    def _improve_image(self, image: np.ndarray) -> np.ndarray:
        """Improve image quality with better error handling."""
        try:
            # Garantir que a imagem está em grayscale
            if len(image.shape) > 2:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Aplicar threshold adaptativo
            binary = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )

            # Remover ruído
            kernel = np.ones((2,2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            return binary
        except Exception as e:
            self._logger.error(f"Error improving image: {str(e)}")
            raise CaptchaProcessingError("Failed to improve image") from e

    def _process_captcha(self, captcha: Image) -> np.ndarray:
        """Process captcha with comprehensive error handling."""
        try:
            # Converter para array numpy
            img_array = self._png_to_jpg(captcha)
            
            # Processar imagem
            processed = self._improve_image(img_array)
            
            return processed
        except Exception as e:
            self._logger.error(f"Error processing captcha: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha") from e