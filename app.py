import asyncio

import streamlit as st
from metadata_storage import MetadataStorage
from nips_scraper import NipsScrapper
from progress_tracker import ProgressTracker
from utils import check_network_availability


def init_ui():
    # Streamlit setup
    st.set_page_config(
        page_title="NIPS Scrapper ",
        page_icon="📚",
    )

    st.logo(icon_image="./images/icon-books.png", image="./images/icon-books.png", size="large",
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
    folder_path = st.text_input("Enter Folder Path: ", value=download_directory,
                                                 placeholder="Enter download folder path : ", disabled=True)
    st.toast(f"Folder Selected: {folder_path}")
    return start_year, end_year


async def main():
    log_container = init_ui()
    # Scraper setup
    base_url = "https://papers.nips.cc"  # The correct base URL for your target website
    download_directory = "./downloaded_papers"
    semaphore = asyncio.Semaphore(10)
    progress_tracker = ProgressTracker()
    # Initialize MetadataStorage
    metadata_storage = MetadataStorage()
    nips_scrapper = NipsScrapper(base_url, download_directory, semaphore, progress_tracker, metadata_storage)
    if not check_network_availability():
        if st.button("Reload"):
            st.rerun()
        log_container.error("Please check your internet connection and try again.")
        return
    max_year, min_year = 2024, 1987
    with log_container.container():
        start_year, end_year = get_inputs(max_year, min_year, download_directory)
        if st.button("Start Downloading"):
            if start_year <= min_year and end_year >= max_year:
                log_container.toast(f"Please Enter Year between {min_year} and {max_year}, Please try again")
                st.rerun()
            else:
                log_container.success(
                    f"Downloading : {(end_year - start_year) + 1} years Papers from {start_year} to {end_year}, Please wait...")
                # Start downloading papers
                results = await nips_scrapper.download_papers_from_year_range(start_year, end_year)
                log_container.toast(f" ✅ Download Completed.")


if __name__ == "__main__":
    asyncio.run(main())
