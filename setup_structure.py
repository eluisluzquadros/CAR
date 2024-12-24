# /content/CAR/setup_structure.py
import os
import shutil
from pathlib import Path

def setup_project():
    """
    Sets up the project directory structure and moves files to their correct locations.
    """
    # Create base directory structure using pathlib for better path handling
    base_dir = Path("SICAR")
    drivers_dir = base_dir / "drivers"
    
    base_dir.mkdir(exist_ok=True)
    drivers_dir.mkdir(exist_ok=True)
    
    # Create empty __init__.py files for package recognition
    (base_dir / "__init__.py").touch()
    (drivers_dir / "__init__.py").touch()
    
    # File mappings using pathlib.Path
    file_mappings = {
        Path("captcha.py"): drivers_dir / "captcha.py",
        Path("tesseract.py"): drivers_dir / "tesseract.py",
        Path("paddle.py"): drivers_dir / "paddle.py",
        Path("http_client.py"): base_dir / "http_client.py",
        Path("sicar.py"): base_dir / "sicar.py",
        Path("state.py"): base_dir / "state.py",
        Path("polygon.py"): base_dir / "polygon.py",
        Path("url.py"): base_dir / "url.py",
        Path("exceptions.py"): base_dir / "exceptions.py",
    }
    
    for source, dest in file_mappings.items():
        if source.exists():
            shutil.move(str(source), str(dest))  # shutil.move works with Path objects

    print("Project structure set up successfully!")

if __name__ == "__main__":
    setup_project()