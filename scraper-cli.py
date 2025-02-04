import csv
import json
import os
import aiohttp
import aiofiles
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
import re
import sys
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
import os
import csv
import json
import pandas as pd
from utils import sanitize_filename

class MetadataStorage:
    def __init__(self, csv_file='./metadata/papers_metadata.csv', json_file='./metadata/papers_metadata.json'):
        self.csv_file = csv_file
        self.json_file = json_file
        self._initialize_files()

    def _initialize_files(self):
        # Initialize CSV file with headers if it doesn't exist
        if not os.path.exists('./metadata'):
            os.makedirs('./metadata')
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['paper_name', 'author', 'year', 'pdf_link'])

        # Initialize JSON file with an empty list if it doesn't exist
        if not os.path.exists(self.json_file):
            with open(self.json_file, mode='w', encoding='utf-8') as file:
                json.dump([], file, ensure_ascii=False, indent=4)

    def _append_to_csv(self, paper_name, author, year, pdf_link):
        # Append paper metadata to CSV (using pandas)
        df = pd.DataFrame([[paper_name, author, year, pdf_link]], columns=['paper_name', 'author', 'year', 'pdf_link'])
        df.to_csv(self.csv_file, mode='a', header=False, index=False, encoding='utf-8')

    def _append_to_json(self, paper_name, author, year, pdf_link):
        # Append paper metadata to JSON as a list
        with open(self.json_file, mode='r+', encoding='utf-8') as file:
            data = json.load(file)
            data.append({
                'paper_name': paper_name,
                'author': author,
                'year': year,
                'pdf_link': pdf_link
            })
            file.seek(0)
            json.dump(data, file, ensure_ascii=False, indent=4)

    def save_paper_metadata(self, paper_name, author, year, pdf_link):
        # Sanitize paper name and append data to CSV and JSON
        paper_name = sanitize_filename(paper_name)
        self._append_to_csv(paper_name, author, year, pdf_link)
        self._append_to_json(paper_name, author, year, pdf_link)
class ProgressTracker:
    def __init__(self):
        self.total_papers = 0
        self.downloaded_papers = 0
        self.failed_papers = 0
        self.year_stats = {}
    def update(self, year, status):
        if status == "success":
            self.downloaded_papers += 1
            if year not in self.year_stats:
                self.year_stats[year] = {"downloaded": 0, "failed": 0}
            self.year_stats[year]["downloaded"] += 1
        else:
            self.failed_papers += 1
            if year not in self.year_stats:
                self.year_stats[year] = {"downloaded": 0, "failed": 0}
            self.year_stats[year]["failed"] += 1
        self.display_progress()
    def get_overall_progress(self):
        return (self.downloaded_papers / self.total_papers) * 100 if self.total_papers > 0 else 0
    def get_year_progress(self, year):
        year_data = self.year_stats.get(year, {"downloaded": 0, "total_papers": 0})
        year_progress = (year_data["downloaded"] / year_data["total_papers"]) * 100 if year_data["total_papers"] > 0 else 0
        return year_progress
    def display_progress(self):
        sys.stdout.write(f"\rTotal Papers: {self.total_papers} | Downloaded: {self.downloaded_papers} | Failed: {self.failed_papers} | Overall Progress: {self.get_overall_progress():.2f}% |")
        for year, stats in self.year_stats.items():
            year_progress = self.get_year_progress(year)
            sys.stdout.write(f"Year {year}: {stats['downloaded']}/{stats['total_papers']} ({year_progress:.2f}%) |")
        sys.stdout.flush()
class NipsScrapper:
    def __init__(self, base_url, download_directory, semaphore, progress_tracker):
        self.base_url = base_url
        self.download_directory = download_directory
        self.semaphore = semaphore
        self.progress_tracker = progress_tracker
        self.metadata_storage = MetadataStorage()
    async def download_paper(self, session, pdf_url: str, save_directory: str, paper_name: str, year: str):
        try:
            paper_name = sanitize_filename(paper_name)
            async with session.get(pdf_url) as response:
                response.raise_for_status()
                file_path = os.path.join(save_directory, f"{paper_name}.pdf")
                async with aiofiles.open(file_path, 'wb') as file:
                    await file.write(await response.read())
                self.progress_tracker.update(year, "success")
                return {"status": "success", "file_name": f"{paper_name}.pdf", "url": pdf_url, "year": year}
        except aiohttp.ClientError as e:
            print(f"Failed to download {paper_name}: {e}")
            self.progress_tracker.update(year, "failed")
            return {"status": "failed", "file_name": "", "url": pdf_url, "year": year}
    async def extract_paper_links(self, session, page_url: str):
        try:
            paper_links = []
            async with session.get(page_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                selected_a_tags = soup.select("body > div.container-fluid > div > ul > li a")
                for a in selected_a_tags:
                    link = a.get('href')
                    title = a.get_text()
                    author = a.find_next_sibling('i').get_text()
                    paper_links.append({
                        "title": title,
                        "link": link,
                        "author": author
                    })
            return paper_links
        except aiohttp.ClientError as e:
            print(f"Failed to extract paper links from {page_url}: {e}")
            return {}
    async def extract_year_links(self, session, sub_link_url: str) -> list[str]:
        try:
            async with session.get(sub_link_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                year_links = [
                    a.get('href') for a in soup.find_all('a') if 'paper_files/paper/' in a.get('href')
                ]
                return year_links
        except aiohttp.ClientError as e:
            print(f"Failed to extract year links from {sub_link_url}: {e}")
            return []
    async def get_max_min_year(self) -> (int,int):
        async with aiohttp.ClientSession() as session:
            year_links = await self.extract_year_links(session, self.base_url)
            return int(year_links[0].split('/')[-1]), int(year_links[-1].split('/')[-1])
    def convert_to_pdf_url(self, abstract_url: str) -> str:
        return abstract_url.replace('hash/', 'file/').replace('Abstract.html', 'Paper.pdf')
    async def download_papers_from_year_range(self, start_year, end_year):
        create_directory(self.download_directory)
        async with aiohttp.ClientSession() as session:
            year_links = await self.extract_year_links(session, self.base_url)
            tasks = []
            for year_link in year_links:
                year = year_link.split('/')[-1]
                if start_year <= int(year) <= end_year:
                    full_year_url = self.base_url + year_link
                    paper_links_extracted = await self.extract_paper_links(session, full_year_url)
                    total_papers_in_year = len(paper_links_extracted)
                    self.progress_tracker.total_papers += total_papers_in_year
                    self.progress_tracker.year_stats[year] = {
                        "total_papers": total_papers_in_year,
                        "downloaded": 0,
                        "failed": 0,
                    }
                    for paper_link in paper_links_extracted:
                        author = paper_link["author"]
                        pdf_link = self.convert_to_pdf_url(paper_link["link"])
                        paper_name = paper_link["title"]
                        self.metadata_storage.save_paper_metadata(paper_name=paper_name, author=author, year=year, pdf_link=self.base_url + pdf_link,)
                        tasks.append(self.download_paper_with_semaphore(session, self.base_url + pdf_link, paper_name, year))
            for _ in await asyncio.gather(*tasks):
                self.progress_tracker.display_progress()
    async def download_paper_with_semaphore(self, session, pdf_url: str, paper_name: str, year: str):
        async with self.semaphore:
            return await self.download_paper(session, pdf_url, self.download_directory, paper_name, year)
async def main():
    base_url = "https://papers.nips.cc"
    download_directory = "./downloaded_papers"
    concurrents = asyncio.Semaphore(10)
    progress_tracker = ProgressTracker()
    nips_scrapper = NipsScrapper(base_url, download_directory, concurrents, progress_tracker)
    start_year = int(input("Enter Min Year: ").strip())
    end_year = int(input("Enter Max Year: ").strip())
    max_year, min_year = await nips_scrapper.get_max_min_year()
    if start_year < min_year and end_year > max_year:
        print(f"Please Enter Year between {min_year} and {max_year}")
        return
    await nips_scrapper.download_papers_from_year_range(start_year, end_year)
if __name__ == "__main__":
    asyncio.run(main())
