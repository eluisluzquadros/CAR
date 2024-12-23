from setuptools import setup, find_packages

setup(
    name="SICAR",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'aiohttp_socks',
        'beautifulsoup4',
        'pillow',
        'tqdm'
    
