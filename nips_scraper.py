import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from utils import sanitize_filename, create_directory
from progress_tracker import ProgressTracker
import asyncio
import os
class NipsScrapper:
    def __init__(self, base_url, download_directory, semaphore, progress_tracker: ProgressTracker, metadata_storage):
        self.base_url = base_url
        self.download_directory = download_directory
        self.semaphore = semaphore
        self.progress_tracker = progress_tracker
        self.metadata_storage = metadata_storage
    async def download_paper(self, session, pdf_url: str, save_directory: str, paper_name: str, year: str, author):
        try:
            paper_name = sanitize_filename(paper_name)
            async with session.get(pdf_url) as response:
                response.raise_for_status()
                # Create the full path to save the PDF
                file_path = os.path.join(save_directory, fr"{paper_name}.pdf")
                # Write the PDF to the file asynchronously
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

                # Find all links for papers (filter by 'Paper' text)
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
        # Extract all year-wise sub-links
        async with aiohttp.ClientSession() as session:
            year_links = await self.extract_year_links(session, self.base_url)
            return int(year_links[0].split('/')[-1]), int(year_links[-1].split('/')[-1])
    def convert_to_pdf_url(self, abstract_url: str) -> str:
        return abstract_url.replace('hash/', 'file/').replace("Abstract", "Paper").replace('.html', '.pdf')

    async def download_papers_from_year_range(self, start_year, end_year):
        create_directory(self.download_directory)
        async with aiohttp.ClientSession() as session:
            year_links = await self.extract_year_links(session, self.base_url)
            tasks = []  # List to store all download tasks
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
                        pdf_link = self.convert_to_pdf_url(paper_link["link"])
                        paper_name = paper_link["title"]
                        author = paper_link["author"]
                        tasks.append(self.download_paper_with_semaphore(session, self.base_url + pdf_link, paper_name, year, author))

            for _ in await asyncio.gather(*tasks):
                pass
    async def download_paper_with_semaphore(self, session, pdf_url: str, paper_name: str, year: str, author):
        async with self.semaphore:
            await self.metadata_storage.save_paper_metadata(paper_name=paper_name, author=author, year=year, pdf_link=pdf_url)
            return await self.download_paper(session, pdf_url, self.download_directory, paper_name, year, author)
