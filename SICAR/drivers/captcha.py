# /content/CAR/SICAR/drivers/captcha.py
"""
Captcha Abstract Base Class.

This module defines the abstract base class for Captcha processing drivers.
All specific OCR drivers (Tesseract, PaddleOCR, etc.) should inherit from this class.
"""

from abc import ABC, abstractmethod
from PIL import Image
import numpy as np
import cv2
import logging
from typing import Optional

class CaptchaProcessingError(Exception):
    """Exception raised when captcha processing fails."""
    pass

class Captcha(ABC):
    """Abstract Base Class for Captcha solvers."""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_captcha(self, captcha: Image.Image) -> str:
        """
        Abstract method to get the Captcha value.

        Args:
            captcha: The captcha image as a PIL Image object.

        Returns:
            The extracted text from the captcha.

        Raises:
            CaptchaProcessingError: If the captcha cannot be processed.
        """
        pass

    def _png_to_jpg(self, captcha: Image.Image) -> np.ndarray:
        """
        Convert PNG to JPG format and to a numpy array.
        Convert to BGR if dealing with color image.

        Args:
            captcha: The captcha image as a PIL Image object.

        Returns:
            The image as a numpy array (in BGR format if it was a color image).
        """
        try:
            # Convert to RGB if needed
            if captcha.mode != 'RGB':
                captcha = captcha.convert('RGB')

            # Convert to numpy array
            img_array = np.array(captcha)

            # Convert to BGR for OpenCV if color image
            if len(img_array.shape) == 3:
                return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img_array

        except Exception as e:
            self._logger.error(f"Error converting image: {str(e)}")
            raise CaptchaProcessingError("Failed to convert image format") from e

    def _improve_image(self, image: np.ndarray) -> np.ndarray:
        """
        Improve image quality for OCR using adaptive thresholding and noise removal.

        Args:
            image: The image as a numpy array.

        Returns:
            The improved image as a numpy array.
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) > 2:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                image, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )

            # Remove noise
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

            # Invert back
            binary = cv2.bitwise_not(binary)

            return binary

        except Exception as e:
            self._logger.error(f"Error improving image: {str(e)}")
            raise CaptchaProcessingError("Failed to improve image") from e

    def _process_captcha(self, captcha: Image.Image) -> np.ndarray:
        """
        Process the captcha image (convert format, improve quality).

        Args:
            captcha: The captcha image as a PIL Image object.

        Returns:
            The processed image as a numpy array.
        """
        try:
            # Convert format and to numpy array
            img_array = self._png_to_jpg(captcha)

            # Improve image
            processed = self._improve_image(img_array)

            return processed

        except Exception as e:
            self._logger.error(f"Error processing captcha: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha") from e