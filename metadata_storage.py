import os
import csv
import pandas as pd
import asyncio
from utils import sanitize_filename

class MetadataStorage:
    def __init__(self, csv_file='./metadata/papers_metadata.csv'):
        self.csv_file = csv_file
        self.loop = asyncio.get_event_loop()  # Get the event loop
        self._initialize_files()

    def _initialize_files(self):
        # Initialize CSV file with headers if it doesn't exist
        if not os.path.exists('./metadata'):
            os.makedirs('./metadata')
        # Initialize the CSV file asynchronously
        if not os.path.exists(self.csv_file):
            self.loop.run_in_executor(None, self._initialize_csv)
    def _initialize_csv(self):
        # Initialize CSV file with headers if it doesn't exist
        with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['paper_name', 'author', 'year', 'pdf_link'])

    async def _append_to_csv(self, paper_name, author, year, pdf_link):
        # Append paper metadata to CSV (using pandas)
        df = pd.DataFrame([[paper_name, author, year, pdf_link]], columns=['paper_name', 'author', 'year', 'pdf_link'])
        await self.loop.run_in_executor(None, self._write_to_csv, df)

    def _write_to_csv(self, df):
        # This function runs in a separate thread for non-blocking behavior
        df.to_csv(self.csv_file, mode='a', header=False, index=False, encoding='utf-8')
    async def save_paper_metadata(self, paper_name, author, year, pdf_link):
        paper_name = sanitize_filename(paper_name)
        await self._append_to_csv(paper_name, author, year, pdf_link)