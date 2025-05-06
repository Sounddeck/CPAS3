"""
A script to install the recommended langchain-ollama package
"""
import subprocess
import sys

def install_langchain_ollama():
    """Install the langchain-ollama package"""
    print("Installing langchain-ollama package...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-ollama"])
        print("Successfully installed langchain-ollama")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install langchain-ollama")
        return False

if __name__ == "__main__":
    install_langchain_ollama()

