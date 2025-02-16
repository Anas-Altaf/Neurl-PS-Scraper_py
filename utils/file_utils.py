# utils/file_utils.py
import os
import re


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def sanitize_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = re.sub(r"\\ ", repl='_', string=filename)
    filename = re.sub(r'\t', '_', filename)
    filename = re.sub(r'\n', '_', filename)
    return filename
