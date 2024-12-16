"""PaddleOCR Driver with Colab compatibility."""

import re
from PIL import Image
import subprocess
import sys
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Paddle(Captcha):
    def __init__(self):
        super().__init__()
        self._setup_paddle()
        self._initialize_paddle()
    
    def _setup_paddle(self):
        """Setup PaddleOCR if needed (especially for Colab)."""
        try:
            import paddleocr
        except ImportError:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install',
                    'paddlepaddle', 'paddleocr'
                ], check=True, capture_output=True)
            except Exception as e:
                self._logger.error(f"Failed to setup PaddleOCR: {str(e)}")
                raise

    def _initialize_paddle(self):
        """Initialize PaddleOCR with proper settings."""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                lang="en",
                use_space_char=False,
                show_log=False,
                use_gpu=False  # Safer default for Colab
            )
        except Exception as e:
            self._logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
            raise

    def get_captcha(self, captcha: Image) -> str:
        """Extract text from captcha with improved error handling."""
        try:
            processed_image = self._process_captcha(captcha)
            result = self.ocr.ocr(processed_image, det=False, cls=False)
            
            if not result or not result[0]:
                raise CaptchaProcessingError("No text detected in captcha")
            
            text = result[0][0][0]
            clean_text = re.sub('[^A-Za-z0-9]+', '', text)
            
            return clean_text
            
        except Exception as e:
            self._logger.error(f"Error in PaddleOCR: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with PaddleOCR") from e