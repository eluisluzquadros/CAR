# /content/CAR/SICAR/drivers/paddle.py
"""PaddleOCR Driver with improved error handling and image processing."""

import re
from PIL import Image
import subprocess
import sys
import os
import logging
import numpy as np
import cv2
from paddleocr import PaddleOCR
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Paddle(Captcha):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self.DEBUG_FOLDER = None  # Initialize DEBUG_FOLDER as None
        self._setup_paddle()
        self._initialize_paddle()

    def _setup_paddle(self):
        """Setup PaddleOCR with proper error handling."""
        try:
            import paddle
            import paddleocr
            self._logger.debug("PaddleOCR already installed")

        except ImportError:
            self._logger.info("PaddleOCR not found, attempting installation")
            try:
                # For environments like Google Colab
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install',
                    '--quiet', 'paddlepaddle', 'paddleocr'
                ], check=True, capture_output=True)

            except subprocess.CalledProcessError as e:
                self._logger.error(f"Failed to install PaddleOCR: {str(e)}")
                raise CaptchaProcessingError("Failed to install PaddleOCR") from e

    def _initialize_paddle(self):
        """Initialize PaddleOCR with optimized settings."""
        try:

            # Configure for captcha recognition
            self.ocr = PaddleOCR(
                use_angle_cls=False,  # Faster processing
                lang="en",
                use_space_char=False,
                show_log=False,
                use_gpu='COLAB_GPU' in os.environ or 'CUDA_VISIBLE_DEVICES' in os.environ,  # Use GPU if available
                rec_batch_num=1, # Captcha usually has one word
                
                # Additional advanced configuration (optional)
                det_algorithm='DB', # More robust detector
                det_model_dir=None,
                det_limit_side_len=768,
                det_limit_type='min',
                det_db_thresh=0.3,
                det_db_box_thresh=0.5,
                det_db_unclip_ratio=1.6,
                det_east_score_thresh=0.8,
                det_east_cover_thresh=0.1,
                det_east_nms_thresh=0.2,

                rec_algorithm='CRNN',
                rec_image_shape="3, 32, 100",
                rec_char_type='en',

            )
            self._logger.debug("PaddleOCR initialized successfully")

        except Exception as e:
            self._logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
            raise CaptchaProcessingError("Failed to initialize PaddleOCR") from e

    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """
        Preprocesses the captcha image for better OCR accuracy.
        """
        try:
            if self.DEBUG_FOLDER:  # Check if DEBUG_FOLDER is set
                os.makedirs(self.DEBUG_FOLDER, exist_ok=True)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(self.DEBUG_FOLDER / "1_original.png")

            # Convert PIL Image to NumPy array
            img_array = np.array(image)

            # 1. Convert to grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            # 2. Adaptive Thresholding
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

            # 3. Denoising
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)

            if self.DEBUG_FOLDER:
                # Save intermediate images if DEBUG_FOLDER is set
                cv2.imwrite(str(self.DEBUG_FOLDER / "3_gray.png"), gray)
                cv2.imwrite(str(self.DEBUG_FOLDER / "5_thresh.png"), thresh)
                cv2.imwrite(str(self.DEBUG_FOLDER / "6_denoised.png"), denoised)

            return denoised

        except Exception as e:
            self._logger.error(f"Error in PaddleOCR preprocessing: {str(e)}")
            raise CaptchaProcessingError("Failed to preprocess image for PaddleOCR") from e

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved accuracy."""
        try:
            # Preprocess the image
            processed_image = self._preprocess_image(captcha)

            # Run OCR
            result = self.ocr.ocr(
                processed_image,
                det=False,  # Skip detection for captchas
                cls=False   # Skip classification
            )

            if not result or not result[0]:
                raise CaptchaProcessingError("No text detected in captcha")

            # Extract and clean text
            text = result[0][0][0]
            clean_text = re.sub('[^A-Za-z0-9]+', '', text).upper()

            self._logger.debug(f"PaddleOCR Raw result: '{text}', Cleaned result: '{clean_text}'")

            if not clean_text:
                raise CaptchaProcessingError("No valid characters found in captcha")
            
            if len(clean_text) != 5:
                self._logger.warning(f"PaddleOCR extracted text with incorrect length: {clean_text}")

            return clean_text

        except Exception as e:
            self._logger.error(f"PaddleOCR processing failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with PaddleOCR") from e