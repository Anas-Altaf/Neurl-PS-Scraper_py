# controllers/scraper_controller.py
import asyncio

import aiohttp

from utils.file_utils import create_directory


class ScraperController:
    def __init__(self, scraper_model, metadata_model, progress_view, semaphore):
        self.scraper_model = scraper_model
        self.metadata_model = metadata_model
        self.progress_view = progress_view
        self.semaphore = semaphore

    async def get_year_range(self):
        async with aiohttp.ClientSession() as session:
            year_links = await self.scraper_model.extract_year_links(
                session, self.scraper_model.base_url)
            max_year = int(year_links[0].split('/')[-1])
            min_year = int(year_links[-1].split('/')[-1])
            return min_year, max_year

    async def download_papers(self, start_year, end_year, download_directory):
        create_directory(download_directory)
        async with aiohttp.ClientSession() as session:
            year_links = await self.scraper_model.extract_year_links(
                session, self.scraper_model.base_url)

            tasks = []
            for year_link in year_links:
                year = year_link.split('/')[-1]
                if start_year <= int(year) <= end_year:
                    tasks.extend(await self._process_year(
                        session, year_link, year, download_directory))

            await asyncio.gather(*tasks)

    async def _process_year(self, session, year_link, year, download_directory):
        full_year_url = self.scraper_model.base_url + year_link
        paper_links = await self.scraper_model.extract_paper_links(session, full_year_url)

        self.progress_view.total_papers += len(paper_links)
        self.progress_view.year_stats[year] = {
            "total_papers": len(paper_links),
            "downloaded": 0,
            "failed": 0,
        }

        tasks = []
        for paper in paper_links:
            pdf_link = self.scraper_model.convert_to_pdf_url(paper["link"])
            tasks.append(self._download_paper_with_semaphore(
                session, pdf_link, paper["title"], year, paper["author"],
                download_directory))
        return tasks

    async def _download_paper_with_semaphore(self, session, pdf_url, paper_name,
                                             year, author, download_directory):
        async with self.semaphore:
            full_pdf_url = self.scraper_model.base_url + pdf_url
            success = await self.scraper_model.download_paper(
                session, full_pdf_url, download_directory, paper_name)

            await self.metadata_model.save_paper_metadata(
                paper_name, author, year, pdf_url)

            self.progress_view.update_progress(year, "success" if success else "failed")
