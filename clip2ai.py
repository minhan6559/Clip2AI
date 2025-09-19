"""
clip2google.py

Press Ctrl+Shift+N+A+T to send the current clipboard text to Google Gemini,
then replace the clipboard with the model response.
"""

import os
import threading
import time
import logging
import sys
import subprocess
import importlib

# Required packages with their import names and pip names
REQUIRED_PACKAGES = {
    "pyperclip": "pyperclip",
    "keyboard": "keyboard",
    "google.generativeai": "google-generativeai",
}


def install_package(package_name):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False


def check_and_install_packages():
    """Check if required packages are installed and install them if missing"""
    missing_packages = []

    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing_packages.append(pip_name)

    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            print(f"Installing {package}...")
            if install_package(package):
                print(f"Successfully installed {package}")
            else:
                print(f"Failed to install {package}")
                sys.exit(1)
        print("All packages installed successfully. Restarting...")
        # Restart the script to import the newly installed packages
        os.execv(sys.executable, [sys.executable] + sys.argv)


# Check and install packages before importing them
check_and_install_packages()

# Now import the packages
import pyperclip
import keyboard
import google.generativeai as genai

# Configure logging to write to a file instead of console
log_file = os.path.join(os.path.dirname(__file__), "clipboard_ai.log")
logging.basicConfig(
    filename=log_file,
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)

# API_KEY = os.getenv("GOOGLE_API_KEY")
# if not API_KEY:
#     logging.error("GOOGLE_API_KEY not set. Set the environment variable and retry.")
#     raise SystemExit("GOOGLE_API_KEY missing")

API_KEY = "AIzaSyD5PgEL3U69usl5Oo777-Mal1zmKmW2Ms8"

# Initialize Google Generative AI client
genai.configure(api_key=API_KEY)

# Keep track of the last processed clipboard to avoid re-processing identical text
_last_processed = None
_lock = threading.Lock()


def extract_text_from_response(resp):
    """
    Try several ways to extract the assistant text from different Google Gemini response shapes.
    Adjust this code if the Google Generative AI client returns a different structure.
    """
    try:
        # Typical structure for Gemini responses: resp.text
        return resp.text
    except Exception:
        try:
            # Fallback: check for candidates structure
            return resp.candidates[0].content.parts[0].text
        except Exception:
            try:
                # Alternative structure
                return resp.parts[0].text
            except Exception:
                return None


def send_prompt_to_gemini(
    prompt_text, model="gemini-2.0-flash-lite", max_tokens=800, temperature=0.2
):
    """
    Send prompt_text to Google Gemini and return the assistant text or None on error.
    Using Gemini Flash 2.5 model for fast responses.
    """
    try:
        logging.info("Calling Google Gemini API...")
        # Create model instance
        model_instance = genai.GenerativeModel(model)

        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # Generate response
        response = model_instance.generate_content(
            prompt_text, generation_config=generation_config
        )

        out = extract_text_from_response(response)
        return out
    except Exception as e:
        logging.exception("Google Gemini request failed")
        return None


def process_clipboard():
    global _last_processed
    with _lock:
        text = pyperclip.paste()
        if not isinstance(text, str) or text.strip() == "":
            logging.info("Clipboard is empty or not text. Nothing to do.")
            return

        # Avoid reprocessing identical text
        if text == _last_processed:
            logging.info("Clipboard text equals last processed text. Skipping.")
            return

        logging.info("Sending clipboard to Google Gemini. Length: %d chars", len(text))
        # You can customise prompt behavior here, for example add system instruction wrapper
        model_response = send_prompt_to_gemini(text)
        if model_response:
            pyperclip.copy(model_response)
            _last_processed = model_response
            logging.info(
                "Clipboard updated with Gemini response. Length: %d chars",
                len(model_response),
            )
        else:
            logging.error("No response from Google Gemini. Clipboard not changed.")


def hotkey_callback():
    # Run the potentially blocking API call in a background thread
    threading.Thread(target=process_clipboard, daemon=True).start()


def main():
    # Register hotkey. This string means press and hold Alt+G together.
    hotkey = "alt+g"
    logging.info("Clipboard AI service started. Hotkey: %s", hotkey)
    keyboard.add_hotkey(hotkey, hotkey_callback)

    logging.info("Service running in background. Press Alt+ESC to exit.")
    # Keep running until user presses Alt+ESC
    try:
        keyboard.wait("alt+x")
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Clipboard AI service stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
