import os
import re

import tkinter as tk
from tkinter import filedialog

import requests


def create_directory(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

def sanitize_filename(filename: str) -> str:
    # Replace invalid characters with an underscore
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = re.sub(r"\\ ",repl='_',string=filename)
    filename = re.sub(r'\t', '_', filename)           # Replace tab character with underscore
    filename = re.sub(r'\n', '_', filename)
    return filename
def check_network_availability():
    try:
        response = requests.get("https://www.google.com")
        return True
    except requests.ConnectionError:
        return False
