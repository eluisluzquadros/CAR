# /content/CAR/setup.py
from setuptools import setup, find_packages

setup(
    name="SICAR",
    version="0.0.2", # updated version
    packages=find_packages(),
    python_requires=">=3.7", # updated to 3.7 since f-strings were introduced.
    install_requires=[
        'requests',
        'beautifulsoup4',
        'pillow>=9.0.0', # Specify version for security or compatibility
        'pytesseract',
        'numpy',
        'opencv-python-headless', # Use headless version to avoid GUI dependencies
        'paddlepaddle>=2.6.0',
        'paddleocr>=2.7.0.3',
    ],
    package_data={'': ['*']},
    zip_safe=False
)