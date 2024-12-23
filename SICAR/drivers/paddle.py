# SICAR/drivers/paddle.py
"""PaddleOCR Driver with improved error handling and image processing."""

import re
from PIL import Image
import subprocess
import sys
import os
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Paddle(Captcha):
    def __init__(self):
        super().__init__()
        self._setup_paddle()
        self._initialize_paddle()
    
    def _setup_paddle(self):
        """Setup PaddleOCR with proper error handling."""
        try:
            import paddleocr
            self._logger.debug("PaddleOCR already installed")
            
        except ImportError:
            self._logger.info("PaddleOCR not found, attempting installation")
            try:
                # For Google Colab environment
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
            from paddleocr import PaddleOCR
            
            # Configure for captcha recognition
            self.ocr = PaddleOCR(
                use_angle_cls=False,  # Faster processing
                lang="en",
                use_space_char=False,
                show_log=False,
                use_gpu='COLAB_GPU' in os.environ,  # Use GPU if available in Colab
                enable_mkldnn=True,  # Enable Intel MKL-DNN acceleration
                det_db_thresh=0.3,  # Lower threshold for text detection
                det_db_box_thresh=0.3,
                det_limit_side_len=960,
                rec_batch_num=1
            )
            self._logger.debug("PaddleOCR initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
            raise CaptchaProcessingError("Failed to initialize PaddleOCR") from e

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved accuracy."""
        try:
            # Process the image
            processed_image = self._process_captcha(captcha)
            
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
            clean_text = re.sub('[^A-Za-z0-9]+', '', text)
            
            self._logger.debug(f"Raw OCR result: '{text}', Cleaned result: '{clean_text}'")
            
            if not clean_text:
                raise CaptchaProcessingError("No valid characters found in captcha")
            
            return clean_text
            
        except Exception as e:
            self._logger.error(f"PaddleOCR processing failed: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with PaddleOCR") from e