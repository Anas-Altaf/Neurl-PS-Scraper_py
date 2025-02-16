# views/progress_view.py

import streamlit as st


class ProgressView:
    def __init__(self):
        self.progress_bar = st.empty()
        self.year_progress_container = st.empty()
        self.total_papers = 0
        self.downloaded_papers = 0
        self.failed_papers = 0
        self.year_stats = {}

    def update_progress(self, year, status):
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

    def display_progress(self):
        overall_progress = (self.downloaded_papers / self.total_papers) * 100 if self.total_papers > 0 else 0
        progress_msg = f"Overall Progress : {overall_progress:.2f}%"
        overall_papers_status = (f"Papers\nTotal: {self.total_papers}  | "
                                 f"Downloaded: {self.downloaded_papers}  | "
                                 f"Failed: {self.failed_papers}")

        self.progress_bar.progress(value=overall_progress / 100, text=progress_msg)

        with self.year_progress_container.container():
            st.warning(overall_papers_status)
            st.write("Year-wise Progress")
            year_progress = "\n".join(
                f"Year {year}: {stats['downloaded']}/{stats['total_papers']}"
                for year, stats in self.year_stats.items()
            )
            st.code(year_progress)
