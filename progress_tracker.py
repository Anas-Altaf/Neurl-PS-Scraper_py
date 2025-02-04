import streamlit as st

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
        year_progress = (year_data["downloaded"] / year_data["total_papers"]) * 100 if year_data["total_papers"] > 0 else 0
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
