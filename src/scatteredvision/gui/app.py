import tkinter as tk
from tkinter import ttk
from queue import Queue, Empty
from threading import Thread
import uuid

from scatteredvision.gui.intake_tab import IntakeTab
from scatteredvision.gui.search_tab import SearchTab
from scatteredvision.gui.clusterreview_tab import ClusterReviewTab
from scatteredvision.gui.analysis_tab import AnalysisTab
from scatteredvision.gui.logs_tab import LogsTab
from scatteredvision.gui.about_tab import AboutTab
from scatteredvision.jobs.intake import IntakeJob
from scatteredvision.jobs.config import IntakeConfig

class ScatteredVisionApp(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Scattered Vision")
		self.geometry("1100x900")

		self.event_queue = Queue()

		self.notebook = ttk.Notebook(self)
		self.notebook.pack(fill="both", expand=True)

		self.intake_tab = IntakeTab(self.notebook, self.event_queue)
		self.search_tab = SearchTab(self.notebook, self.event_queue)
		self.clusterreview_tab = ClusterReviewTab(self.notebook, self.event_queue)		
		self.analysis_tab = AnalysisTab(self.notebook, self.event_queue)
		self.logs_tab = LogsTab(self.notebook)
		self.about_tab = AboutTab(self.notebook)

		self.notebook.add(self.intake_tab, text="Intake")
		self.notebook.add(self.search_tab, text="Search")
		self.notebook.add(self.clusterreview_tab, text="Cluster Review")
		self.notebook.add(self.analysis_tab, text="Analysis")
		self.notebook.add(self.logs_tab, text="Logs")
		self.notebook.add(self.about_tab, text="About")

		control_frame = ttk.Frame(self)
		control_frame.pack(fill="x")


		self.after(50, self.poll_events)

	def poll_events(self):
		try:
			while True:
				event = self.event_queue.get_nowait()

				self.intake_tab.handle_event(event)
				self.search_tab.handle_event(event)
				self.clusterreview_tab.handle_event(event)
				self.analysis_tab.handle_event(event)
				self.logs_tab.handle_event(event)

		except Empty:
			pass

		self.after(50, self.poll_events)
