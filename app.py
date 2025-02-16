# main.py
import asyncio

import requests
import streamlit as st

from controllers.scraper_controller import ScraperController
from models.metadata_model import MetadataModel
from models.scraper_model import ScraperModel
from views.progress_view import ProgressView
from views.ui_view import UIView

# Constants and configurations
BASE_URL = "https://papers.nips.cc"
DOWNLOAD_DIR = "./downloaded_papers"
CSV_PATH = "./metadata"
CSV_FILE_NAME = "/papers_metadata.csv"


def check_network_availability(url):
    try:
        requests.get(url)
        return True
    except requests.ConnectionError:
        return False


async def main():
    # Initialize views
    ui_view = UIView()
    log_container = ui_view.init_ui()
    progress_view = ProgressView()

    # Network check
    if not check_network_availability(BASE_URL):
        if st.button("Reload"):
            st.rerun()
        log_container.error("Unable to access Site, Please check your internet connection.")
        return

    # Initialize models and controller
    scraper_model = ScraperModel(BASE_URL)
    metadata_model = MetadataModel(CSV_PATH, CSV_FILE_NAME)
    semaphore = asyncio.Semaphore(10)
    controller = ScraperController(scraper_model, metadata_model, progress_view, semaphore)

    with log_container.container():
        # Get user inputs
        download_dir, csv_path = ui_view.get_path_inputs(CSV_PATH, DOWNLOAD_DIR)
        min_year, max_year = await controller.get_year_range()
        start_year, end_year = ui_view.get_year_inputs(max_year, min_year)

        if st.button("Start Downloading"):
            if start_year < min_year or end_year > max_year:
                st.toast(f"Please Enter Year between {min_year} and {max_year}")
                st.rerun()
            else:
                log_container.success(
                    f"Downloading: {(end_year - start_year) + 1} years of papers "
                    f"from {start_year} to {end_year}, Please wait...")
                await controller.download_papers(start_year, end_year, download_dir)
                log_container.toast("✅ Download Completed.")


if __name__ == "__main__":
    asyncio.run(main())
