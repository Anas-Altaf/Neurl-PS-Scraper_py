import asyncio
import os
import re

import aiofiles
import aiohttp
from bs4 import BeautifulSoup


class NeurIPSAsyncScraper:
    BASE_URL = "https://papers.nips.cc"
    MAX_RETRIES = 5  # Increased retries
    TIMEOUT = 180  # Increased timeout
    CONCURRENT_LIMIT = 2  # Reduced concurrency
    RETRY_BACKOFF = [2, 4, 8, 16, 32]  # Longer backoff times

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.pdfs_dir = "pdfs"
        os.makedirs(self.pdfs_dir, exist_ok=True)
        self.connector = aiohttp.TCPConnector(limit=self.CONCURRENT_LIMIT)

    async def scrape_neurips_papers(self):
        current_year = 2024
        start_year = current_year - 5

        timeout = aiohttp.ClientTimeout(total=self.TIMEOUT, connect=40, sock_read=180, sock_connect=40)
        async with aiohttp.ClientSession(timeout=timeout, connector=self.connector, headers=self.HEADERS) as session:
            tasks = [self.process_year(session, year) for year in range(start_year, current_year + 1)]
            await asyncio.gather(*tasks)

    async def process_year(self, session, year):
        url = f"{self.BASE_URL}/paper_files/paper/{year}"
        print(f"Fetching papers from: {url}")

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Failed to fetch {url}, Status: {response.status}")
                    return
                else:
                    print(f"Processing papers for {year}")
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                print(f"Soup result is  : {soup.prettify()}")
                papers = soup.select('body > div.container-fluid > div > ul  li a[href]')
                if not papers:
                    print(f"No papers found for {year}, URL might be incorrect.")
                    return
                print(f"Found {len(papers)} papers for {year}")
                print(f"🎨data is {papers}")
                paper_tasks = [self.process_paper(session, year, paper) for paper in papers]
                await asyncio.gather(*paper_tasks)
        except aiohttp.ClientError as e:
            print(f"Request failed for {url}: {e}")
        except asyncio.TimeoutError:
            print(f"Timeout while requesting {url}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def process_paper(self, session, year, paper):
        title = paper.text.strip()
        paper_url = f"{self.BASE_URL}{paper['href']}"
        print(f"Paper Url is {paper_url}")
        pdf_url = paper_url.replace('hash/', 'file/').replace("Abstract", "Paper").replace('.html', '.pdf')
        print(f"PDF Url is {pdf_url}")
        authors = await self.extract_authors(session, paper_url)

        # Ensure filename is valid
        filename = re.sub(r'[<>:"/\\|?*]', '_', title) + ".pdf"

        # Attempt to download PDF
        await self.download_pdf(session, pdf_url, filename)

    async def extract_authors(self, session, paper_url):
        return await self.retry_request(session, paper_url, self._extract_authors)

    async def _extract_authors(self, session, paper_url):
        async with session.get(paper_url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            authors_elem = soup.select_one('.container .authors')
            return authors_elem.text.strip() if authors_elem else "Unknown"

    async def download_pdf(self, session, pdf_url, filename):
        return await self.retry_request(session, pdf_url, self._download_pdf, filename)

    async def _download_pdf(self, session, pdf_url, filename):
        try:
            async with session.get(pdf_url) as response:
                if response.status == 200:
                    filepath = os.path.join(self.pdfs_dir, filename)
                    os.makedirs(self.pdfs_dir, exist_ok=True)

                    async with aiofiles.open(filepath, mode='wb') as f:
                        await f.write(await response.read())

                    print(f"Downloaded: {filename}")
                    return True
                else:
                    print(f"Failed to download {filename}. Status code: {response.status}")
                    return False
        except Exception as e:
            print(f"PDF download failed: {pdf_url} - {e}")
            return False

    async def retry_request(self, session, url, func, *args, retries=MAX_RETRIES):
        for attempt, backoff in zip(range(retries), self.RETRY_BACKOFF):
            try:
                return await func(session, url, *args)
            except (aiohttp.ClientError, ConnectionResetError, asyncio.TimeoutError) as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                break
            print(f"Retrying {url} in {backoff} seconds...")
            await asyncio.sleep(backoff)
        print(f"All attempts failed for {url}")
        return None


async def main():
    scraper = NeurIPSAsyncScraper()
    await scraper.scrape_neurips_papers()


if __name__ == "__main__":
    asyncio.run(main())
