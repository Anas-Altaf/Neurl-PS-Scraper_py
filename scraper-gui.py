import asyncio
import csv
import os
import re

import aiofiles
import aiohttp
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


def create_directory(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


def sanitize_filename(filename: str) -> str:
    # Replace invalid characters with an underscore
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = re.sub(r"\\ ", repl='_', string=filename)
    filename = re.sub(r'\t', '_', filename)  # Replace tab character with underscore
    filename = re.sub(r'\n', '_', filename)
    return filename


def check_network_availability(url):
    try:
        requests.get(url)
        return True
    except requests.ConnectionError:
        return False


class MetadataStorage:
    def __init__(self, csv_file='./metadata', csv_file_name="/papers_metadata.csv"):
        self.csv_file = csv_file
        self.loop = asyncio.get_event_loop()  # Get the event loop
        self._initialize_files()
        self.csv_file_name = csv_file_name

    def _initialize_files(self):
        # Initialize CSV file with headers if it doesn't exist
        if not os.path.exists(path=self.csv_file):
            os.makedirs(self.csv_file)
        # Initialize the CSV file asynchronously
        if not os.path.exists(self.csv_file):
            self.loop.run_in_executor(None, self._initialize_csv)

    def _initialize_csv(self):
        # Initialize CSV file with headers if it doesn't exist
        with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Paper', 'Author', 'Year', 'PdfLink', 'Abstract'])

    async def _append_to_csv(self, paper_name, author, year, pdf_link, abstract):
        # Append paper metadata to CSV (using pandas)
        df = pd.DataFrame([[paper_name, author, year, pdf_link, abstract]],
                          columns=['Paper', 'Author', 'Year', 'PdfLink', 'Abstract'])
        await self.loop.run_in_executor(None, self._write_to_csv, df)

    def _write_to_csv(self, df):
        # This function runs in a separate thread for non-blocking behavior
        df.to_csv(self.csv_file + self.csv_file_name, mode='a', header=False, index=False, encoding='utf-8')

    async def save_paper_metadata(self, paper_name, author, year, pdf_link, abstract):
        paper_name = sanitize_filename(paper_name)
        await self._append_to_csv(paper_name, author, year, pdf_link, abstract)


class ProgressTracker:
    def __init__(self):
        # UI Elements
        self.progress_bar = st.empty()
        self.year_progress_container = st.empty()

        # Initialize progress tracking variables
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
        self.display_ui_progress()

    def get_overall_progress(self):
        return (self.downloaded_papers / self.total_papers) * 100 if self.total_papers > 0 else 0

    def get_year_progress(self, year):
        year_data = self.year_stats.get(year, {"downloaded": 0, "total_papers": 0})
        year_progress = (year_data["downloaded"] / year_data["total_papers"]) * 100 if year_data[
                                                                                           "total_papers"] > 0 else 0
        return year_progress

    def display_ui_progress(self):
        overall_progress = self.get_overall_progress() / 100
        progress_msg = f"Overall Progress : {self.get_overall_progress():.2f}%"
        overall_papers_status = f"Papers\nTotal: {self.total_papers}  | Downloaded: {self.downloaded_papers}  | Failed: {self.failed_papers}"

        self.progress_bar.progress(value=overall_progress, text=progress_msg)

        with self.year_progress_container.container():
            st.warning(overall_papers_status)
            st.write("Year-wise Progress")
            year_progress = ""
            for year, stats in self.year_stats.items():
                year_progress += f"Year {year}: {stats['downloaded']}/{stats['total_papers']} \n"
            st.code(year_progress)


class NipsScrapper:
    def __init__(self, base_url, download_directory, semaphore, progress_tracker: ProgressTracker,
                 metadata_storage: MetadataStorage):
        self.base_url = base_url
        self.download_directory = download_directory
        self.semaphore = semaphore
        self.progress_tracker = progress_tracker
        self.metadata_storage = metadata_storage

    async def download_paper(self, session, pdf_url: str, save_directory: str, paper_name: str, year: str):
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

    async def get_paper_abstract(self, paper_web_link, session) -> str:
        try:
            async with session.get(paper_web_link) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                abstract = soup.select_one('body > div.container-fluid > div > p:nth-child(9)').get_text()
                st.write(f'Abstract for {paper_web_link} : \n')
                st.code(abstract)
                return abstract
        except aiohttp.ClientError as e:
            print(f"Failed to extract Abstract  from {paper_web_link}: {e}")
        return ''

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

    async def get_max_min_year(self) -> (int, int):
        # Extract all year-wise sub-links
        async with aiohttp.ClientSession() as session:
            year_links = await self.extract_year_links(session, self.base_url)
            # st.code(f"Years : {year_links}")
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
                        paper_abstract = await self.get_paper_abstract(self.base_url + paper_link["link"], session)
                        tasks.append(
                            self.download_paper_with_semaphore(session, self.base_url + pdf_link, paper_name, year,
                                                               author, paper_abstract))

            for _ in await asyncio.gather(*tasks):
                pass

    async def download_paper_with_semaphore(self, session, pdf_url: str, paper_name: str, year: str, author, abstract):
        async with self.semaphore:
            await self.metadata_storage.save_paper_metadata(paper_name=paper_name, author=author, year=year,
                                                            pdf_link=pdf_url, abstract=abstract)
            return await self.download_paper(session, pdf_url, self.download_directory, paper_name, year)


def init_ui():
    # Streamlit setup
    st.set_page_config(
        page_title="NIPS Scrapper ",
        page_icon="📚",
    )
    if 'session' not in st.session_state:
        st.session_state.s = 'session'
    st.logo(icon_image="images/icon-books.png", image="./images/icon-books.png", size="large",
            link="https://github.com/Anas-Altaf")
    st.title("Neural-PS Scraper")
    st.write("This app downloads all NIPS conference papers within a specified year range.")
    st.toast("Welcome to the Neural-PS Scraper")
    st.toast("This App is created by [Anas Altaf](https://github.com/Anas-Altaf)")
    return st.empty()


def get_inputs(max_year=2024, min_year=1987, download_directory="./downloads"):
    start_year = int(
        st.number_input("Enter Min Year: ", min_value=min_year, max_value=max_year, value=min_year))
    end_year = int(
        st.number_input("Enter Max Year: ", min_value=min_year, max_value=max_year, value=max_year))

    return start_year, end_year


def get_paths(csv_path, download_directory):
    csv_path = st.text_input("Enter Metadata Path: ", value=csv_path,
                             placeholder="Enter metadata path : ", disabled=False)
    st.toast(f"CSV Path Selected: {csv_path}")
    folder_path = st.text_input("Enter Folder Path: ", value=download_directory,
                                placeholder="Enter download folder path : ", disabled=False)
    return folder_path, csv_path


async def main():
    try:

        log_container = init_ui()
        # Scraper setup
        base_url = "https://papers.nips.cc"  # The correct base URL for your target website
        download_directory = r".\downloaded_papers"
        csv_path = "./metadata"
        csv_file_name = "/papers_metadata.csv"
        if not check_network_availability(base_url):
            if st.button("Reload"):
                st.rerun()
            log_container.error("Unable to access Site, Please check your internet connection and try again.")
            return
        semaphore = asyncio.Semaphore(10)
        progress_tracker = ProgressTracker()
        # Initialize MetadataStorage
        with log_container.container():
            download_directory, csv_path = get_paths(csv_path, download_directory)
            # st.write(f"Path is {download_directory}")
            metadata_storage = MetadataStorage(csv_file=csv_path, csv_file_name=csv_file_name)
            nips_scrapper = NipsScrapper(base_url, os.path.join(download_directory, 'docs'), semaphore,
                                         progress_tracker, metadata_storage)
            max_year, min_year = await nips_scrapper.get_max_min_year()
            start_year, end_year = get_inputs(max_year, min_year, download_directory)
            if st.button("Start Downloading"):
                if start_year < min_year or end_year > max_year:
                    st.toast(f"Please Enter Year between {min_year} and {max_year}, Please try again")
                    st.rerun()
                else:
                    log_container.success(
                        f"Downloading : {(end_year - start_year) + 1} years Papers from {start_year} to {end_year}, Please wait...")
                    # Start downloading papers
                    await nips_scrapper.download_papers_from_year_range(start_year, end_year)
                    log_container.toast(f" ✅ Download Completed.")
    except Exception as e:
        st.error(f"Error : {e}")


if __name__ == "__main__":
    asyncio.run(main())
