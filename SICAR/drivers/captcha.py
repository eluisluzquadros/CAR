# SICAR/drivers/captcha.py
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
        """Convert image to JPG format with improved error handling."""
        try:
            # Make sure we have an RGB image
            if captcha.mode != 'RGB':
                captcha = captcha.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(captcha)
            
            # Convert to BGR for OpenCV
            if len(img_array.shape) == 3:  # Color image
                return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img_array  # Already grayscale
            
        except Exception as e:
            self._logger.error(f"Error converting image format: {str(e)}")
            raise CaptchaProcessingError("Failed to convert image format") from e

    def _improve_image(self, image: np.ndarray) -> np.ndarray:
        """Improve image quality for better OCR results."""
        try:
            # Convert to grayscale if needed
            if len(image.shape) > 2:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            image = cv2.GaussianBlur(image, (3, 3), 0)
            
            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                image, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Remove small noise
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # Invert back
            binary = cv2.bitwise_not(binary)
            
            return binary
            
        except Exception as e:
            self._logger.error(f"Error improving image: {str(e)}")
            raise CaptchaProcessingError("Failed to improve image") from e

    def _process_captcha(self, captcha: Image) -> np.ndarray:
        """Process captcha image with full error handling and logging."""
        try:
            # Log image details for debugging
            self._logger.debug(f"Processing captcha image: mode={captcha.mode}, size={captcha.size}")
            
            # Convert format
            img_array = self._png_to_jpg(captcha)
            self._logger.debug(f"Converted image shape: {img_array.shape}")
            
            # Improve image
            processed = self._improve_image(img_array)
            self._logger.debug(f"Processed image shape: {processed.shape}")
            
            return processed
            
        except Exception as e:
            self._logger.error(f"Error processing captcha: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha") from e