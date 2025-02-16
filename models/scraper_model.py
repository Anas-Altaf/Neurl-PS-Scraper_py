# models/scraper_model.py
import os

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from utils.file_utils import sanitize_filename


class ScraperModel:
    def __init__(self, base_url):
        self.base_url = base_url

    async def extract_year_links(self, session, sub_link_url):
        try:
            async with session.get(sub_link_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                return [a.get('href') for a in soup.find_all('a')
                        if 'paper_files/paper/' in a.get('href')]
        except aiohttp.ClientError as e:
            print(f"Failed to extract year links from {sub_link_url}: {e}")
            return []

    async def extract_paper_links(self, session, page_url):
        try:
            async with session.get(page_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                selected_a_tags = soup.select("body > div.container-fluid > div > ul > li a")
                return [{
                    "title": a.get_text(),
                    "link": a.get('href'),
                    "author": a.find_next_sibling('i').get_text()
                } for a in selected_a_tags]
        except aiohttp.ClientError as e:
            print(f"Failed to extract paper links from {page_url}: {e}")
            return {}

    def convert_to_pdf_url(self, abstract_url):
        return abstract_url.replace('hash/', 'file/').replace("Abstract", "Paper").replace('.html', '.pdf')

    async def download_paper(self, session, pdf_url, save_directory, paper_name):
        try:
            paper_name = sanitize_filename(paper_name)
            async with session.get(pdf_url) as response:
                response.raise_for_status()
                file_path = os.path.join(save_directory, f"{paper_name}.pdf")
                async with aiofiles.open(file_path, 'wb') as file:
                    await file.write(await response.read())
                return True
        except aiohttp.ClientError as e:
            print(f"Failed to download {paper_name}: {e}")
            return False
