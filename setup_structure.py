# setup_structure.py
import os
import shutil

def setup_project():
    # Create base directory structure
    os.makedirs("SICAR/drivers", exist_ok=True)
    
    # Create empty __init__.py files
    open("SICAR/__init__.py", "a").close()
    open("SICAR/drivers/__init__.py", "a").close()
    
    # Move files to correct locations if they exist
    file_mappings = {
        "captcha.py": "SICAR/drivers/captcha.py",
        "tesseract.py": "SICAR/drivers/tesseract.py",
        "http_client.py": "SICAR/http_client.py",
        "sicar.py": "SICAR/sicar.py",
        "state.py": "SICAR/state.py",
        "polygon.py": "SICAR/polygon.py",
        "url.py": "SICAR/url.py",
        "exceptions.py": "SICAR/exceptions.py",
    }
    
    for source, dest in file_mappings.items():
        if os.path.exists(source):
            shutil.move(source, dest)

    print("Project structure set up successfully!")

if __name__ == "__main__":
    setup_project()