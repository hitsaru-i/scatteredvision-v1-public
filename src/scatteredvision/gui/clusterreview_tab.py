import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from threading import Thread
import threading
import sqlite3
import os
import uuid
from scatteredvision.core.db_faces import (
	load_clusters_with_image_counts,
	load_images_for_cluster
)
from scatteredvision.core import config as cfg
from scatteredvision.jobs.clusterreview import ClusterReviewJob
from scatteredvision.jobs.config import ClusterReviewConfig
from scatteredvision.gui.image_viewer import ImageViewer
from scatteredvision.core.events import JobEvent

class ClusterReviewTab(ttk.Frame):
	def __init__(self, parent, event_queue):
		super().__init__(parent)

		self.event_queue = event_queue
		self.job= None

		defaults = cfg.load_config()	

		self.db_path_var = tk.StringVar(value=defaults.get("default_db_file", ""))
		self.status_var = tk.StringVar(value="Status: Idle")

		# --- Row counter for grid placement ---
		row = 0
		self.cluster_results = []
		self.cluster_images = []

		self.preview_width = 400
		self.preview_height = 400

		self.preview_image = None      # PIL image (optional but useful)
		self.preview_photo = None      # ImageTk.PhotoImage (must persist)		

		#  Database selection
		ttk.Label(self, text="Database:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
		self.db_path_var = tk.StringVar(value=defaults.get("default_db_file", ""))
#		self.db_path_var = tk.StringVar()
		self.db_entry = ttk.Entry(self, textvariable=self.db_path_var, width=60)
		self.db_entry.grid(row=row, column=1, sticky="we", padx=5, pady=2)
		ttk.Button(self, text="Browse", command=self._browse_db).grid(row=row, column=2, padx=5, pady=2)
		row += 1

		## Status Bar: Added
		ttk.Label(self, textvariable=self.status_var).grid(
			row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5
		)
		row += 1		

		#  Action buttons
		button_frame = ttk.Frame(self)
		button_frame.grid(row=row, column=0, columnspan=3, sticky="we", padx=5, pady=5)

		button_frame.columnconfigure((0,1,2,3,), weight=1)


		self.view_image_button = ttk.Button(button_frame, text="View Full Image",command=self._open_image_viewer, state="disabled")
		self.view_image_button.grid(row=0, column=0, padx=5)

		self.cluster_call_ordered_button = ttk.Button(button_frame, text="Cluster Call Ordered", command=lambda: self.start_cluster_call_job(order="id"))
			#lambda: self._load_clusters(order="id"))
		self.cluster_call_ordered_button.grid(row=0, column=1, padx=5)

		self.cluster_call_asc_button = ttk.Button(button_frame, text="Cluster Call ASC", command=lambda: self.start_cluster_call_job(order="asc"))
		#lambda: self._load_clusters(order="asc"))
		self.cluster_call_asc_button.grid(row=0, column=2, padx=5)

		self.cluster_call_desc_button = ttk.Button(button_frame, text="Cluster Call DESC", command=lambda: self.start_cluster_call_job(order="desc"))
			#lambda: self._load_clusters(order="desc"))
		self.cluster_call_desc_button.grid(row=0, column=3, padx=5)
		row += 1




		#  Preview pane
		preview_frame = ttk.Frame(self, relief="sunken", borderwidth=2)
		preview_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
		self.preview_canvas = tk.Canvas(preview_frame, width=self.preview_width, height=self.preview_height, relief="sunken")
#		self.preview_canvas.pack(fill="both", expand=True)
		self.preview_canvas.pack()
		row += 1

		# Directly under preview frame
		self.preview_filename_var = tk.StringVar(value="Viewing: None")
		self.preview_filename_label = ttk.Label(
			self, 
			textvariable=self.preview_filename_var,
			anchor="w"
		)
		self.preview_filename_label.grid(
			row=row,  # row immediately under preview frame
			column=0,
			columnspan=3,
			sticky="we",
			padx=5,
			pady=2
		)		
		row += 1
		# Cluster ID label
		self.cluster_id_var = tk.StringVar(value="—")

		ttk.Label(self, text="Cluster ID:").grid(
			row=row, column=0, sticky="w", padx=5
		)
		ttk.Label(self, textvariable=self.cluster_id_var).grid(
			row=row, column=1, sticky="w", padx=5
		)
		row += 1

		#  Cluster & Image panes
		panes_frame = ttk.Frame(self)
		panes_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

		# Left: Cluster Data
		cluster_frame = ttk.Frame(panes_frame)
		cluster_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
		ttk.Label(cluster_frame, text="Cluster Data:").pack(anchor="w")
		self.cluster_listbox = tk.Listbox(cluster_frame, height=10)
		self.cluster_listbox.pack(fill="both", expand=True, side="left")
		cluster_scrollbar = ttk.Scrollbar(cluster_frame, orient="vertical", command=self.cluster_listbox.yview)
		cluster_scrollbar.pack(side="right", fill="y")
		self.cluster_listbox.config(yscrollcommand=cluster_scrollbar.set)

		self.cluster_listbox.bind("<<ListboxSelect>>", self._on_cluster_select)

		# Right: Image Paths
		image_frame = ttk.Frame(panes_frame)
		image_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
		ttk.Label(image_frame, text="Image Paths:").pack(anchor="w")
		self.image_listbox = tk.Listbox(image_frame, height=10)
		self.image_listbox.pack(fill="both", expand=True, side="left")
		image_scrollbar = ttk.Scrollbar(image_frame, orient="vertical", command=self.image_listbox.yview)
		image_scrollbar.pack(side="right", fill="y")
		self.image_listbox.config(yscrollcommand=image_scrollbar.set)

		self.image_listbox.bind("<<ListboxSelect>>", self._on_image_select)

		#  Optional: name association input (bottom placeholder)
		# row += 1
		# ttk.Label(self, text="Associate Name:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
		# self.name_var = tk.StringVar()
		# ttk.Entry(self, textvariable=self.name_var, width=40).grid(row=row, column=1, sticky="we", padx=5, pady=2)
		# self.associate_button = ttk.Button(self, text="Add Name Association To Cluster").grid(row=row, column=2, padx=5, pady=2)
		# row += 1

		# --- Configure resizing behavior ---
		self.columnconfigure(1, weight=1)
		self.rowconfigure(row, weight=1)
		panes_frame.rowconfigure(0, weight=1)
		panes_frame.columnconfigure(0, weight=1)
		panes_frame.columnconfigure(1, weight=1)


### PROTOTYPE CALLBACK JOB HANDLER

	def start_cluster_call_job(self, order="id"):
		if self.job is not None:
			self.status_var.set("Status: Previous cluster review still cleaning up...")
			return

		if not self.db_path_var.get():
			self.status_var.set("Status: Select database file")
			return

		if self.event_queue is None:
			self.status_var.set("Status: No event queue configured")
			return

		config = ClusterReviewConfig(
			db_path=self.db_path_var.get(),
			order=order
		)

		self.job = ClusterReviewJob(
			job_id=str(uuid.uuid4()),
			config=config,
			event_queue=self.event_queue
		)

		self.status_var.set("Status: Loading clusters...")

		Thread(target=self.job.run, daemon=True).start()



##### End GUI BLOCK

	def _browse_db(self):
		path = filedialog.askopenfilename(
			title="Select database file",
			defaultextension=".db",
			filetypes=[("SQLite DB", "*.db *.sqlite")]
		)
		if path:
			self.db_path_var.set(path)

	def _populate_clusters(self, clusters):
		self.cluster_listbox.delete(0, tk.END)
		self.cluster_results = clusters

		for cluster in clusters:
			display_text = f"{cluster['cluster_id']} ({cluster['image_count']} images)"
			if cluster["label"]:
				display_text += f" [{cluster['label']}]"
			self.cluster_listbox.insert(tk.END, display_text)

	def _on_cluster_select(self, event):
		# 1. Clear current preview 
		# 2. Ensure a selection exists
		if not self.cluster_listbox.curselection():
			return

		# 3. Resolve selected cluster
		idx = self.cluster_listbox.curselection()[0]
		cluster = self.cluster_results[idx]
		cluster_id = cluster["cluster_id"]
		self.cluster_id_var.set(str(cluster_id))

		# 4. Open database connection
		conn = sqlite3.connect(self.db_path_var.get())

		try:
			# 5. Load images for cluster
			self.cluster_images = load_images_for_cluster(conn, cluster_id)
		finally:
			conn.close()

		# 6. Populate image listbox
		self.image_listbox.delete(0, "end")
		for img in self.cluster_images:
			self.image_listbox.insert("end", img["path"])

		# 7. Reset preview / disable buttons
		self._clear_preview()
		self.view_image_button.config(state="disabled")

	def _on_image_select(self, event):
		selection = self.image_listbox.curselection()
		if not selection:
			return

		index = selection[0]
		image_path = (self.cluster_images[index])["path"]
		self._update_preview(image_path)

	def _update_preview(self, image_path):
		try:
			img = Image.open(image_path)
			img.thumbnail((self.preview_width, self.preview_height))
			self.preview_photo = ImageTk.PhotoImage(img)

			self.preview_canvas.delete("all")
			self.preview_canvas.create_image(
				self.preview_width // 2,
				self.preview_height // 2,
				image=self.preview_photo,
				anchor="center"
			)

			self.view_image_button.config(state="normal")
			filename = os.path.basename(image_path)
			self.preview_filename_var.set(f"Viewing: {filename}")			

		except Exception as e:
			print(f"Preview load failed: {e}")			


	def _clear_preview(self):
		self.preview_canvas.delete("all")
		self.preview_photo = None
		self.preview_image = None
		self.preview_filename_var.set("Viewing: None")		

	def _open_image_viewer(self):
		if not self.image_listbox.curselection():
			return
		idx = self.image_listbox.curselection()[0]
		image_path = self.cluster_images[idx]["path"]
		ImageViewer(self, image_path)

	def handle_event(self, event):
		if event.job_id != getattr(self.job, "job_id", None):
			return

		event_type = event.event_type
		payload = event.payload or {}

		if event_type == "JOB_STARTED":
			self.status_var.set("Status: Cluster loading started")

		elif event_type == "CLUSTER_RESULTS":
			self._populate_clusters(payload["clusters"])
			self.status_var.set(
				f"Status: {payload['count']} clusters loaded"
			)

		elif event_type == "JOB_FINISHED":
			self.status_var.set("Status: Cluster loading complete")
			self.job = None

		elif event_type == "JOB_FAIL":
			self.status_var.set("Status: Cluster loading failed")
			self.job = None
