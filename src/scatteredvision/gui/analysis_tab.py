import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import threading
import sqlite3
import os
from scatteredvision.core.db_faces import (
	load_analysis_overview,
	load_cluster_stats,
	load_cluster_distribution,
	create_face_cluster,
	insert_face,
	encode_face_vector,
	decode_face_vector,
	recalibrate_clusters
)
from scatteredvision.core import config as cfg
from scatteredvision.jobs.analysis import ReadMetricsJob, RecalibrateClustersJob



class AnalysisTab(ttk.Frame):
	def __init__(self, parent, event_queue):
		super().__init__(parent)

		defaults = cfg.load_config()
		self.event_queue = event_queue
		self.job= None
		row = 0
		self.tolerance_var = tk.DoubleVar(value=defaults.get("default_tolerance", 0.5))		

		# ==============================
		# Database Selection Row
		# ==============================
		ttk.Label(self, text="Database:").grid(
			row=row, column=0, sticky="w", padx=5, pady=5
		)

		self.db_path_var = tk.StringVar(
			value=defaults.get("default_db_file", "")
		)

		self.db_entry = ttk.Entry(
			self, textvariable=self.db_path_var, width=60
		)
		self.db_entry.grid(
			row=row, column=1, sticky="we", padx=5, pady=5
		)

		self.browse_button = ttk.Button(
			self, text="Browse",
			command=self._browse_db
		)
		self.browse_button.grid(
			row=row, column=2, padx=5, pady=5
		)

		self.read_button = ttk.Button(
			self, text="Read and Update",
			command=self._on_read_metrics
		)
		self.read_button.grid(
			row=row, column=3, padx=5, pady=5
		)

		self.columnconfigure(1, weight=1)

		row += 1

		# ==============================
		# Overview Metrics Frame
		# ==============================
		overview_frame = ttk.LabelFrame(self, text="Overview")
		overview_frame.grid(
			row=row, column=0, columnspan=4,
			sticky="we", padx=5, pady=5
		)

		self.total_images_var = tk.StringVar(value="—")
		self.total_faces_var = tk.StringVar(value="—")
		self.total_clusters_var = tk.StringVar(value="—")
		self.singleton_clusters_var = tk.StringVar(value="—")

		labels = [
			("Total Images:", self.total_images_var),
			("Total Faces:", self.total_faces_var),
			("Total Clusters:", self.total_clusters_var),
			("Singleton Clusters:", self.singleton_clusters_var),
		]

		for i, (label, var) in enumerate(labels):
			ttk.Label(overview_frame, text=label).grid(
				row=i, column=0, sticky="w", padx=5, pady=2
			)
			ttk.Label(overview_frame, textvariable=var).grid(
				row=i, column=1, sticky="w", padx=5, pady=2
			)

		row += 1

		# ==============================
		# Cluster Statistics Frame
		# ==============================
		stats_frame = ttk.LabelFrame(self, text="Cluster Statistics")
		stats_frame.grid(
			row=row, column=0, columnspan=4,
			sticky="we", padx=5, pady=5
		)

		self.avg_faces_var = tk.StringVar(value="—")
		self.min_faces_var = tk.StringVar(value="—")
		self.max_faces_var = tk.StringVar(value="—")

		stats = [
			("Average Faces / Cluster:", self.avg_faces_var),
			("Smallest Cluster Size:", self.min_faces_var),
			("Largest Cluster Size:", self.max_faces_var),
		]

		for i, (label, var) in enumerate(stats):
			ttk.Label(stats_frame, text=label).grid(
				row=i, column=0, sticky="w", padx=5, pady=2
			)
			ttk.Label(stats_frame, textvariable=var).grid(
				row=i, column=1, sticky="w", padx=5, pady=2
			)

		row += 1

		# ==============================
		# Cluster Size Distribution
		# ==============================
		dist_frame = ttk.LabelFrame(self, text="Cluster Size Distribution")
		dist_frame.grid(
			row=row, column=0, columnspan=4,
			sticky="nsew", padx=5, pady=5
		)

		self.distribution_listbox = tk.Listbox(
			dist_frame, height=8
		)
		self.distribution_listbox.grid(
			row=0, column=0, sticky="nsew", padx=5, pady=5
		)

		dist_scrollbar = ttk.Scrollbar(
			dist_frame, orient="vertical",
			command=self.distribution_listbox.yview
		)
		dist_scrollbar.grid(
			row=0, column=1, sticky="ns"
		)

		self.distribution_listbox.configure(
			yscrollcommand=dist_scrollbar.set
		)

		dist_frame.columnconfigure(0, weight=1)
		dist_frame.rowconfigure(0, weight=1)

		row += 1

		# ==============================
		# Recalibration
		# ==============================
		recal_frame = ttk.LabelFrame(self, text="Recalibration")
		recal_frame.grid(
			row=row, column=0, columnspan=4,
			sticky="we", padx=5, pady=5
		)

		ttk.Label(
			recal_frame,
			text="Recalibrate Clusters based on alternate tolerance"
		).grid(
			row=0, column=0, sticky="w", padx=5, pady=5
		)

		ttk.Label(recal_frame, text="Tolerance:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
		tol_frame = ttk.Frame(recal_frame)
		tol_frame.grid(row=1, column=1, sticky="w")
		ttk.Scale(tol_frame, from_=0.3, to=0.8, variable=self.tolerance_var, orient="horizontal", length=200).pack(side="left")
		self.tolerance_label = ttk.Label(tol_frame, textvariable=self.tolerance_var)
		self.tolerance_label.pack(side="left", padx=10)

		self.rebuild_button= ttk.Button(
			recal_frame,
			text="Rebuild Clusters",
			command=self._on_rebuild_clusters
		)
		self.rebuild_button.grid(row=2, column=0, sticky="w", padx=5, pady=5)
		self.cancel_button = ttk.Button(
			recal_frame,
			text="Cancel Rebuild",
			command=self._on_cancel_recalibration,
			state="disabled"  # initially disabled
		)
		self.cancel_button.grid(row=2, column=1, sticky="w", padx=5, pady=5)

		#status label
		self.status_var = tk.StringVar(value="Idle")
		ttk.Label(recal_frame, textvariable=self.status_var).grid(row=3, column=0, sticky="w", padx=5)
		# progress Percentage
		self.progress_percent_var = tk.StringVar(value="Progress: 0%")
		ttk.Label(recal_frame, textvariable=self.progress_percent_var).grid(row=4, column=0, sticky="w", padx=5)

		#progress bar
		self.progress_var = tk.DoubleVar(value=0)
		self.progress_bar = ttk.Progressbar(
			recal_frame,
			variable=self.progress_var,
			maximum=100,
			orient="horizontal",
			mode="determinate"
		)
		self.progress_bar.grid(row=5, column=0, sticky="ew", padx=5, pady=5)

	def _browse_db(self):
		path = filedialog.askopenfilename(
			title="Select database file",
			defaultextension=".db",
			filetypes=[("SQLite DB", "*.db *.sqlite")]
		)
		if path:
			self.db_path_var.set(path)


	def _on_read_metrics(self):
		db_path = self.db_path_var.get()
		if not db_path:
			return

		job = ReadMetricsJob(
			job_id="read_metrics",
			config=self.config,
			event_queue=self.event_queue,
			db_path=db_path
		)

		threading.Thread(target=job.run, daemon=True).start()

	def _apply_metrics(self, data):
		overview = data["overview"]
		stats = data["stats"]
		distribution = data["distribution"]

		# === Overview ===
		self.total_images_var.set(overview["images"])
		self.total_faces_var.set(overview["faces"])
		self.total_clusters_var.set(overview["clusters"])
		self.singleton_clusters_var.set(overview["singletons"])

		# === Stats ===
		self.avg_faces_var.set(
			f"{stats['avg']:.2f}" if stats["avg"] is not None else "—"
		)
		self.min_faces_var.set(stats["min"] if stats["min"] is not None else "—")
		self.max_faces_var.set(stats["max"] if stats["max"] is not None else "—")

		# === Distribution ===
		self.distribution_listbox.delete(0, "end")
		for row in distribution:
			self.distribution_listbox.insert(
				"end",
				f"{row['face_count']} faces → {row['cluster_count']} clusters"
			)


	def _on_rebuild_clusters(self):
		if not self.confirm_destructive_action(
			"Confirm Cluster Recalibration?",
			"This will DELETE all current cluster value association and REMAP.\n"
			"Are you SURE you want to recalibrate?\n"
			"This action CANNOT be undone."):
			self.emit("status", "Recalibration action cancelled by user.")
			return
		self.cancel_button.config(state="normal")
		self.rebuild_button.config(state="disabled")
		self.job = RecalibrateClustersJob(
			job_id="recalibrate_clusters",
			config=self.config,
			event_queue=self.event_queue,
			db_path=self.db_path_var.get(),
			tolerance=self.tolerance_var.get()
		)

		threading.Thread(target=self.job.run, daemon=True).start()		

	def confirm_destructive_action(self,title,message):
		return messagebox.askyesno(title,message)

	def handle_event(self, event):
		if event.job_id == "read_metrics":
			if event.event_type == "status":
				self.status_var.set(event.payload)
			elif event.event_type == "metrics":
				self._apply_metrics(event.payload)
			return

		if event.job_id == "recalibrate_clusters":
			if event.event_type == "status":
				self.status_var.set(event.payload)
				if "cancelled" in event.payload.lower():
					self.progress_var.set(0)
					self.progress_percent_var.set("Progress: 0%")
					self.cancel_button.config(state="disabled")
					self.rebuild_button.config(state="normal")				
			elif event.event_type == "progress":
				self.progress_var.set(event.payload)
				self.progress_percent_var.set(f"Progress: {event.payload}%")
			return

	def _on_cancel_recalibration(self):
		# print ("Cancel pressed, job object id: ", id(self.job))
		if self.job is not None:
			self.job.request_cancel()
			self.status_var.set("Canceled by user.")
			self.cancel_button.config(state="disabled")
			self.rebuild_button.config(state="normal")


## Mirror intake cancel
	def cancel_intake(self):
		if self.job:
			self.job.request_cancel()
			self.status_var.set("Cancellation requested...")