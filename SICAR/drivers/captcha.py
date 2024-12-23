# test_captcha.py
from SICAR.sicar import Sicar
from PIL import Image
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_captcha():
    car = None
    try:
        print("\nInitializing SICAR client...")
        car = Sicar()
        
        print("\nDownloading captcha...")
        captcha_image = car._download_captcha()
        
        # Save original captcha
        print("Saving original captcha...")
        captcha_image.save("original_captcha.png")
        
        print("\nAttempting to solve captcha...")
        captcha_text = car._driver.get_captcha(captcha_image)
        
        print(f"\nCaptcha solution: {captcha_text}")
        print(f"Solution length: {len(captcha_text)}")
        
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__} - {str(e)}")
    finally:
        if car:
            car.close()

print("Starting captcha test...")
test_captcha()