from setuptools import setup, find_packages

setup(
    name="SICAR",
    version="0.0.1",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        'aiohttp',
        'aiohttp_socks',
        'beautifulsoup4',
        'pillow',
        'tqdm'
    ],
    package_data={'': ['*']},
    zip_safe=False
)
