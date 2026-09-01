import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

#MAX_LOG_LINES = 100

class LogsTab(ttk.Frame):
	MAX_LOG_LINES = 500
	def __init__(self, parent):
		super().__init__(parent)

		self.text = ScrolledText(self, state="disabled", height=10)
		self.text.pack(fill="both", expand=True)

	def log(self, message):
		text = self.text
		text.config(state="normal")

		# Append new line
		text.insert("end", message + "\n")

		# ---- LINE LIMIT ENFORCEMENT ----
		# Get current line count
		line_count = int(text.index("end-1c").split(".")[0])

		if line_count > self.MAX_LOG_LINES:
			# Delete oldest lines
			excess = line_count - self.MAX_LOG_LINES
			text.delete("1.0", f"{excess + 1}.0")

		# Keep view pinned to bottom
		text.see("end")
		text.config(state="disabled")


	# def log(self, message):
	# 	self.text.config(state="normal")
	# 	self.text.insert("end", message + "\n")
	# 	self.text.see("end")
	# 	self.text.config(state="disabled")

	def handle_event(self, event):
		self.log(f"[{event.event_type}] {event.payload}")
