# models/metadata_model.py
import asyncio
import csv
import os

import pandas as pd

from utils.file_utils import sanitize_filename


class MetadataModel:
    def __init__(self, csv_file='./metadata', csv_file_name="/papers_metadata.csv"):
        self.csv_file = csv_file
        self.loop = asyncio.get_event_loop()
        self.csv_file_name = csv_file_name
        self._initialize_files()

    def _initialize_files(self):
        if not os.path.exists(path=self.csv_file):
            os.makedirs(self.csv_file)
        if not os.path.exists(self.csv_file):
            self.loop.run_in_executor(None, self._initialize_csv)

    def _initialize_csv(self):
        with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Paper', 'Author', 'Year', 'PdfLink'])

    async def _append_to_csv(self, paper_name, author, year, pdf_link):
        df = pd.DataFrame([[paper_name, author, year, pdf_link]],
                          columns=['Paper', 'Author', 'Year', 'PdfLink'])
        await self.loop.run_in_executor(None, self._write_to_csv, df)

    def _write_to_csv(self, df):
        df.to_csv(self.csv_file + self.csv_file_name, mode='a', header=False,
                  index=False, encoding='utf-8')

    async def save_paper_metadata(self, paper_name, author, year, pdf_link):
        paper_name = sanitize_filename(paper_name)
        await self._append_to_csv(paper_name, author, year, pdf_link)
