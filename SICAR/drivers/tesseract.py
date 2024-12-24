# /content/CAR/SICAR/drivers/tesseract.py
"""Tesseract OCR Driver optimized for SICAR text captchas."""

import re
import pytesseract
from PIL import Image, ImageEnhance
import numpy as np
import cv2
import os
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError

class Tesseract(Captcha):
    """Implementation of the Captcha driver using Tesseract OCR."""

    _custom_config = (
        "-l eng "  # English language
        "--psm 7 "  # Treat the image as a single text line
        "--oem 3 "  # Use LSTM-based OCR engine
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" # Whitelist uppercase letters and digits
    )

    def _remove_red_experimental(self, image: Image.Image) -> Image.Image:
        """
        Experimentally removes red components from the image using HSV color space.
        This is specifically tuned for the characteristics of SICAR captchas.

        Args:
            image: The input image (PIL Image).

        Returns:
            The image with red components removed (PIL Image).
        """
        try:
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background

            if image.mode != 'RGB':
                image = image.convert('RGB')

            img_array = np.array(image)
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)

            # Define lower and upper bounds for red color in HSV
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([15, 255, 255])
            lower_red2 = np.array([165, 50, 50])
            upper_red2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)

            # Visualize the mask (Optional - for debugging)
            # os.makedirs('debug', exist_ok=True)
            # cv2.imwrite('debug/mask.png', mask)

            result = img_array.copy()
            result[mask > 0] = [255, 255, 255]

            return Image.fromarray(result)

        except Exception as e:
            self._logger.error(f"Error in experimental red removal: {str(e)}")
            return image

    def get_captcha(self, captcha: Image) -> str:
        """
        Extract text from the captcha image using Tesseract OCR.

        Args:
            captcha: The captcha image (PIL Image).

        Returns:
            The extracted text from the captcha (string).
        """
        try:
            # Save original (Optional - for debugging)
            # os.makedirs('debug', exist_ok=True)
            # captcha.save('debug/1_original.png')

            # Remove red components (experimentally)
            no_red = self._remove_red_experimental(captcha)
            # no_red.save('debug/2_no_red.png') # (Optional - for debugging)

            # Convert to grayscale
            gray = no_red.convert('L')
            # gray.save('debug/3_gray.png') # (Optional - for debugging)

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)
            # enhanced.save('debug/4_enhanced.png') # (Optional - for debugging)
            
            # Adaptive Thresholding
            thresh = cv2.adaptiveThreshold(np.array(enhanced), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            # Image.fromarray(thresh).save('debug/5_thresh.png')

            # Denoising
            denoised = cv2.fastNlMeansDenoising(thresh, None, h=10, searchWindowSize=21, templateWindowSize=7)
            # Image.fromarray(denoised).save('debug/6_denoised.png')

            # Additional pre-processing attempts (if needed)
            attempts = [
                Image.fromarray(denoised),  # Denoised image
                Image.fromarray(thresh),     # Thresholded image
                enhanced,                   # Enhanced grayscale
                gray,                       # Original grayscale
                no_red                      # Color without red
            ]

            for i, img in enumerate(attempts):
                try:
                    text = pytesseract.image_to_string(
                        img,
                        config=self._custom_config
                    )
                    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                    
                    if cleaned and len(cleaned) == 5:
                        self._logger.debug(f"Tesseract extracted: {cleaned} (Attempt {i+1})")
                        return cleaned
                    else:
                        self._logger.debug(f"Tesseract attempt {i+1} did not yield a valid result: {cleaned}")
                except Exception as e:
                    self._logger.warning(f"Tesseract attempt {i+1} failed: {str(e)}")

            # If none of the attempts were successful
            raise CaptchaProcessingError("Tesseract OCR failed to extract a valid captcha after multiple attempts.")

        except Exception as e:
            self._logger.error(f"Error in Tesseract get_captcha: {str(e)}")
            raise CaptchaProcessingError("Failed to process captcha with Tesseract") from e