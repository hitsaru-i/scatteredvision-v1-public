import tkinter as tk
import tkinter.scrolledtext as scrolled
from tkinter import ttk, filedialog
from threading import Thread, Event
import uuid
from scatteredvision.jobs.intake import IntakeJob
from scatteredvision.jobs.config import IntakeConfig
from scatteredvision.core import config as cfg
from scatteredvision.core.events import JobEvent



class IntakeTab(ttk.Frame):
	def __init__(self, parent, event_queue):
		super().__init__(parent)
		self.job= None

		self.event_queue = event_queue

		defaults = cfg.load_config()

		self.root_dir_var = tk.StringVar(value=defaults.get("default_root_dir", ""))
		self.db_path_var = tk.StringVar(value=defaults.get("default_db_file", ""))
		self.tolerance_var = tk.DoubleVar(value=defaults.get("default_tolerance", 0.5))

		self._build_ui()

	def _build_ui(self):
		progress_percentage = 0
		row = 0
		# Root directory

		ttk.Label(self, text="Root Directory:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		ttk.Entry(self, textvariable=self.root_dir_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
		ttk.Button(self, text="Browse", command=self._browse_root).grid(row=row, column=2, padx=5)
		row += 1

		# Database file
		ttk.Label(self, text="Database File:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		ttk.Entry(self, textvariable=self.db_path_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
		ttk.Button(self, text="Browse", command=self._browse_db).grid(row=row, column=2, padx=5)
		row += 1

		# Tolerance slider
		ttk.Label(self, text="Tolerance:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		tol_frame = ttk.Frame(self)
		tol_frame.grid(row=row, column=1, sticky="w")
		ttk.Scale(tol_frame, from_=0.3, to=0.8, variable=self.tolerance_var, orient="horizontal", length=200).pack(side="left")
		self.tolerance_label = ttk.Label(tol_frame, textvariable=self.tolerance_var)
		self.tolerance_label.pack(side="left", padx=10)
		row += 1


		status_frame = ttk.Frame(self)
		status_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5,pady=5)
		# status line

		self.status_var = tk.StringVar(value="Status: Idle")
		ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w", padx=5)
		row+=1
		# File line
		self.current_file_var = tk.StringVar(value="File: —")
		ttk.Label(status_frame, textvariable=self.current_file_var).grid(row=1, column=0, sticky="w", padx=5)
#		ttk.Label(self, text="File: ").grid(row=row, column=0, sticky="w", padx=5, pady=5)
#		ttk.Label(self, text=self.db_path_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)

		# Percentage line
		self.progress_percent_var = tk.StringVar(value="Progress: 0%")
		ttk.Label(status_frame, textvariable=self.progress_percent_var).grid(row=2, column=0, sticky="w", padx=5)			
##		ttk.Label(self, text="Percent:  ").grid(row=row, column=0, sticky="w", padx=5, pady=5)
##		ttk.Label(self, text=progress_percentage, width=50).grid(row=row, column=1, sticky="ew", padx=5)
		

		row += 1

#		Progress bar
		self.progress_var = tk.DoubleVar(value=0)
		self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
		self.progress_bar.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
		row += 1

		# # Logging box
		# self.log_box = scrolled.ScrolledText(self, height=10)
		# self.log_box.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
		# row += 1

		# def log_event(self, message):
		#     self.log_box.insert("end", message + "\n")
		#     self.log_box.see("end")


		# --- Start Button (NOW A TAB MEMBER) ---
		self.start_button = ttk.Button(self, text="Start Intake", command=self.start_intake_job)
		self.start_button.grid(row=row, column=0, columnspan=3, pady=10)
		row+=1
		self.cancel_button = ttk.Button(self,text="Cancel Intake",command=self.cancel_intake,state="disabled")
		self.cancel_button.grid(row=row, column=0, columnspan=3, pady=10)
		self.cancel_button.config(state="disabled")



		self.columnconfigure(1, weight=1)

	# File dialogs
	def _browse_root(self):
		path = filedialog.askdirectory(title="Select root directory")
		if path:
			self.root_dir_var.set(path)

	def _browse_db(self):
		path = filedialog.asksaveasfilename(
			title="Select database file",
			defaultextension=".db",
			filetypes=[("SQLite DB", "*.db *.sqlite")]
		)
		if path:
			self.db_path_var.set(path)

	# --- Public API ---
	def get_config(self):
		return {
			"root_dir": self.root_dir_var.get(),
			"db_path": self.db_path_var.get(),
			"tolerance": float(self.tolerance_var.get())
		}

	def is_valid(self):
		return bool(self.root_dir_var.get() and self.db_path_var.get())

	# --- Job Launcher ---
	def start_intake_job(self):
		if not self.is_valid():
			# Replace with GUI logging mechanism
			print("Please select root directory and database file.")
			return

		cfg = self.get_config()

		if self.event_queue is None:
			print("No event queue configured. Job cannot run.")
			return

		config = IntakeConfig(
			root_dir=cfg["root_dir"],
			db_path=cfg["db_path"],
			tolerance=cfg["tolerance"]
		)

		self.job = IntakeJob(
			job_id=str(uuid.uuid4()),
			config=config,
			event_queue=self.event_queue
		)

		# Disable button immediately
		self.start_button.config(state="disabled")
		self.cancel_button.config(state="normal")
		Thread(target=self.job.run, daemon=True).start()

	def handle_event(self, event: JobEvent):
		event_type = event.event_type
		payload = event.payload or {}

		if event_type == "INTAKE_LOG":
			self.log_event(event.get("message", ""))
		elif event_type == "PROGRESS":
#			self.progress_var.set(event.get("current", 0))
			current = payload.get("current", 0)
			total = payload.get("total", 1)  # avoid div by zero			
#			percent = payload.get("current",0)
			current_file = payload.get("image_path",0)
			if total > 0:
				percent = (current/total) * 100
			else:
				percent = 0.0
			if percent is not None:
				self.progress_var.set(percent)
				self.progress_percent_var.set(f"Progress: {percent:.1f}%")
				self.progress_bar.update_idletasks()

		elif event_type == "PREVIEW_DATA":
			current_file = payload.get("image_path",0)
			if current_file:
				self.current_file_var.set(f"File: {current_file}")			

		elif event_type == "STATUS":
			status = payload.get("message", 0)
			if status:
				self.status_var.set(f"Status: {status}")

##		elif event_type == "INTAKE_PROGRESS":
##			self.progress_var.set(event.get("progress", 0))
##		elif event_type == "INTAKE_FINISHED":
##			self.start_button.config(state="normal")
		elif event_type == "JOB_COMPLETED":
			self.status_var.set("Status: Complete")
			self.start_button.config(state="normal")		

#		Thread(target=job.run, daemon=True).start()

	def cancel_intake(self):
		if self.job:
			self.job.request_cancel()
			self.status_var.set("Cancellation requested...")
#			self.emit()

