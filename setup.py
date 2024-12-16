from setuptools import setup, find_packages

setup(
    name="SICAR",
    packages=find_packages(),
    install_requires=[
        'httpx',
        'Pillow',
        'numpy',
        'opencv-python',
        'beautifulsoup4',
        'tqdm',
        'pytesseract'
    ],
)