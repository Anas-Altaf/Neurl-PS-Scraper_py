# views/ui_view.py

import streamlit as st


class UIView:
    @staticmethod
    def init_ui():
        st.set_page_config(page_title="NIPS Scrapper", page_icon="📚")
        st.title("Neural-PS Scraper")
        st.write("This app downloads all NIPS conference papers within a specified year range.")
        st.toast("Welcome to the Neural-PS Scraper")
        st.toast("This App is created by [Anas Altaf](https://github.com/Anas-Altaf)")
        return st.empty()

    @staticmethod
    def get_year_inputs(max_year=2024, min_year=1987):
        start_year = int(st.number_input("Enter Min Year: ",
                                         min_value=min_year,
                                         max_value=max_year,
                                         value=min_year))
        end_year = int(st.number_input("Enter Max Year: ",
                                       min_value=min_year,
                                       max_value=max_year,
                                       value=max_year))
        return start_year, end_year

    @staticmethod
    def get_path_inputs(csv_path, download_directory):
        csv_path = st.text_input("Enter Metadata Path: ",
                                 value=csv_path,
                                 placeholder="Enter metadata path : ")
        st.toast(f"CSV Path Selected: {csv_path}")
        folder_path = st.text_input("Enter Folder Path: ",
                                    value=download_directory,
                                    placeholder="Enter download folder path : ")
        return folder_path, csv_path
