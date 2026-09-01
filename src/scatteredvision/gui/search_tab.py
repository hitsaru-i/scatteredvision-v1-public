import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from threading import Thread
import threading
import uuid
import os
import shutil
from tkinter.scrolledtext import ScrolledText
from scatteredvision.core import config as cfg
from scatteredvision.jobs.config import SearchConfig
from scatteredvision.jobs.search import SearchJob
from scatteredvision.gui.image_viewer import ImageViewer

PREVIEW_SIZE = 300  # square preview size (px)


class SearchTab(ttk.Frame):
	def __init__(self, parent, event_queue):
		super().__init__(parent)

		self.event_queue = event_queue
		self.job= None

#		self.event_queue = event_queue

		defaults = cfg.load_config()		

		self.query_image_path = tk.StringVar()
		self.status_var = tk.StringVar(value="Status: Idle")
		self.db_path_var = tk.StringVar(value=defaults.get("default_db_file", ""))
		self.export_dir_var = tk.StringVar(value=defaults.get("default_export_dir", ""))
		self.tolerance_var = tk.DoubleVar(value=defaults.get("default_tolerance", 0.5))



		# Keep references to PhotoImage objects
		self._query_photo = None
		self._result_photo = None

		self._build_ui()

	# ---------------- UI BUILD ---------------- #

	def _build_ui(self):
		row = 0

		#Database designation

		# Database file
		ttk.Label(self, text="Database File:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		ttk.Entry(self, textvariable=self.db_path_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
		ttk.Button(self, text="Browse", command=self._browse_db).grid(row=row, column=2, padx=5)
		row += 1	

		#export dir	
		ttk.Label(self, text="Export Directory:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		ttk.Entry(self, textvariable=self.export_dir_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
		ttk.Button(self, text="Browse", command=self._browse_export_dir).grid(row=row, column=2, padx=5)
		row += 1	

		# Query image selection
		ttk.Label(self, text="Query Image:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		ttk.Entry(self, textvariable=self.query_image_path, width=50).grid(
			row=row, column=1, sticky="ew", padx=5
		)
		ttk.Button(self, text="Browse", command=self._browse_query_image).grid(
			row=row, column=2, padx=5
		)
		row += 1
	

		# Tolerance slider
		ttk.Label(self, text="Tolerance:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
		tol_frame = ttk.Frame(self)
		tol_frame.grid(row=row, column=1, sticky="w")
		ttk.Scale(
			tol_frame,
			from_=0.30,
			to=0.80,
			variable=self.tolerance_var,
			orient="horizontal",
			length=200,
		).pack(side="left")
		ttk.Label(tol_frame, textvariable=self.tolerance_var).pack(side="left", padx=10)
		row += 1

		# Action buttons (single row)
		button_frame = ttk.Frame(self)
		button_frame.grid(row=row, column=0, columnspan=3, pady=10, sticky="ew")
		row += 1

		button_frame.columnconfigure((0, 1, 2, 3), weight=1)


		# View image button
		self.view_button = ttk.Button(
			button_frame,
			text="View Full Image",
			command=self._open_image_viewer,
			state="disabled"
		)
		self.view_button.grid(row=0, column=0, padx=5)

		self.export_button = ttk.Button(
			button_frame,
			text="Save to Output",
			command=self._export_selected_image,
			state="disabled"
		)
		self.export_button.grid(row=0, column=1, padx=5)

		self.export_all_button = ttk.Button(
			button_frame,
			text="Export all Images to Output",
			command=self._export_all_images,
			state="disabled"
		)
		self.export_all_button.grid(row=0, column=2, padx=5)

		# Start search button (stub)
		self.search_button = ttk.Button(button_frame, text="Start Search", command=self.start_search_job)
		self.search_button.grid(row=0, column=3, padx=5)


		row += 1

		# Preview frames (side-by-side)
		preview_frame = ttk.Frame(self)
		preview_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
		row += 1

		self._build_previews(preview_frame)
		# Status line
		ttk.Label(self, textvariable=self.status_var).grid(
			row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5
		)
		row += 1

		#Cluster lines
		self.cluster_id_var = tk.StringVar(value="—")

		ttk.Label(self, text="Cluster ID:").grid(
			row=row, column=0, sticky="w", padx=5
		)
		ttk.Label(self, textvariable=self.cluster_id_var).grid(
			row=row, column=1, sticky="w", padx=5
		)

		row += 1

		# Results listbox
		ttk.Label(self, text="Results:").grid(row=row, column=0, sticky="w", padx=5)
		row += 1

		results_frame = ttk.Frame(self)
		results_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
		scrollbar = ttk.Scrollbar(results_frame, orient="vertical")
		self.results_listbox = tk.Listbox(results_frame,yscrollcommand=scrollbar.set,height=10)
		self.results_listbox.grid(row=0, column=0, sticky="nsew")
		scrollbar.config(command=self.results_listbox.yview)
		scrollbar.grid(row=0,column=1, sticky="ns")
		results_frame.columnconfigure(0, weight=1)
		results_frame.rowconfigure(0, weight=1)



#		self.results_listbox = tk.Listbox(self, height=8)
#		self.results_listbox.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5)
# self.results_listbox.bind("<<ListboxSelect>>", self._on_result_select)
		self.results_listbox.bind("<<ListboxSelect>>", self._on_result_select)

		row += 1

		# Status line
		ttk.Label(self, textvariable=self.status_var).grid(
			row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5
		)

		# Grid behavior
		self.columnconfigure(1, weight=1)

	# ---------------- PREVIEW BUILD ---------------- #

	def _build_previews(self, parent):
		parent.columnconfigure(0, weight=1)
		parent.columnconfigure(1, weight=1)

		# Query preview
		self.query_preview_frame = self._create_preview_frame(
			parent, "Query Image", column=0
		)

		# Result preview
		self.result_preview_frame = self._create_preview_frame(
			parent, "Matching Image", column=1
		)

	def _create_preview_frame(self, parent, title, column):
		container = ttk.Frame(parent)
		container.grid(row=0, column=column, padx=10)

		ttk.Label(container, text=title).pack(pady=(0, 5))

		frame = ttk.Frame(container, width=PREVIEW_SIZE, height=PREVIEW_SIZE, relief="sunken")
		frame.pack()
		frame.grid_propagate(False)

		label = ttk.Label(
			frame,
			text="No image",
			anchor="center",
			justify="center",
		)
		label.place(relx=0.5, rely=0.5, anchor="center")

		return {
			"frame": frame,
			"label": label,
		}

	# ---------------- IMAGE HANDLING ---------------- #

	def _load_and_scale_image(self, path):
		img = Image.open(path)
		img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
		return ImageTk.PhotoImage(img)


	def _update_preview(self, preview, image_path=None, placeholder=None, is_query=False):
		label = preview["label"]

		if image_path and os.path.exists(image_path):
			photo = self._load_and_scale_image(image_path)
			label.configure(image=photo, text="")
			label.image = photo

			if is_query:
				self._query_photo = photo
			else:
				self._result_photo = photo
		else:
			label.configure(image="", text=placeholder or "No image")
			label.image = None

	# ---------------- CALLBACKS ---------------- #

	def _browse_query_image(self):
		path = filedialog.askopenfilename(
			title="Select query image",
			filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.JPG, *.JPEG, *.PNG *.BMP")],
		)
		if not path:
			return

		self.query_image_path.set(path)
		self._update_preview(
			self.query_preview_frame,
			image_path=path,
			is_query=True,
		)

	def start_search_job(self):
		if self.job is not None:
			self.status_var.set("Status: Previous search still cleaning up...")
			return

		if not self.db_path_var.get():
			self.status_var.set("Status: Select database file")
			return

		if not self.query_image_path.get():
			self.status_var.set("Status: Select query image")
			return

		if self.event_queue is None:
			self.status_var.set("Status: No event queue configured")
			return

		config = SearchConfig(
			db_path=self.db_path_var.get(),
			query_image_path=self.query_image_path.get(),
			default_export_dir=self.export_dir_var.get(),
			tolerance=self.tolerance_var.get()
		)

		self.job = SearchJob(
			job_id=str(uuid.uuid4()),
			config=config,
			event_queue=self.event_queue
		)

		self.status_var.set("Status: Searching…")
		self.results_listbox.delete(0, "end")

		Thread(target=self.job.run, daemon=True).start()	

	def _on_result_select(self, event):
		if not self.results_listbox.curselection():
			self.view_button.config(state="disabled")			
			return

		self.view_button.config(state="normal")
		self.export_button.config(state="normal")

		idx = self.results_listbox.curselection()[0]
		result = self.results[idx]
		self._update_preview(
			self.result_preview_frame,
			image_path=result["image_path"],
			is_query=False
		)
		selected = self.results[idx]
		self.cluster_id_var.set(
			f"{selected['cluster_id']}"
			if selected.get("cluster_id") is not None
			else "Cluster ID: —"
		)		

		#image_path = self.results[idx]["image_path"]

		#self._load_preview_image(image_path)

	def handle_event(self, event):
#		print("SearchTab.handle_event thread:", threading.current_thread().name)		
		if event.job_id != getattr(self.job, "job_id", None):
			return

		event_type = event.event_type
		payload = event.payload or {}

		if event_type == "JOB_STARTED":
			self.status_var.set("Status: Search started")

		elif event_type == "JOB_LOG":
#			self.log(payload.get("message", ""))
			pass

		# elif event_type == "PROGRESS":
		# 	current = payload.get("current", 0)
		# 	total = payload.get("total", 1)
		# 	percent = (current / total) * 100
		# 	self.progress_var.set(percent)
		# 	self.progress_percent_var.set(f"Progress: {percent:.1f}%")

		elif event_type == "SEARCH_RESULTS":
			self._populate_results(payload["results"])
			self.status_var.set(f"Status: {payload['count']} matches found")

		elif event_type == "JOB_FINISHED":
#			self.progress_var.set(100)
			self.status_var.set("Status: Search complete")
			self.job = None

		elif event_type == "JOB_FAIL":
			self.status_var.set("Status: Search failed")
#			self.log(payload.get("exception", "Unknown error"))
			self.job = None

	def _populate_results(self, results):
		self.results = results  # keep reference for preview lookup
		self.results_listbox.delete(0, "end")

		for r in results:
			display = f"{r['distance']:.3f}  |  {r['image_path']}"
			self.results_listbox.insert("end", display)		
		if results:
			self.export_all_button.config(state="normal")
		else:
			self.export_all_button.config(state="disabled")


	def _browse_db(self):
		path = filedialog.askopenfilename(
			title="Select database file",
			defaultextension=".db",
			filetypes=[("SQLite DB", "*.db *.sqlite")]
		)
		if path:
			self.db_path_var.set(path)



	def _open_image_viewer_old(self):
		if not self.results_listbox.curselection():
			return

		idx = self.results_listbox.curselection()[0]
		image_path = self.results[idx]["image_path"]

		if not os.path.exists(image_path):
			self.status_var.set("Status: Image file not found")
			return

		# Create new window
		win = tk.Toplevel(self)
		win.title(os.path.basename(image_path))
		win.geometry("800x600")

		# Canvas for image
		canvas = tk.Canvas(win, bg="black")
		canvas.pack(fill="both", expand=True)

		# Load image
		try:
			pil_img = Image.open(image_path)
		except Exception as e:
			self.status_var.set(f"Status: Failed to open image: {e}")
			win.destroy()
			return

		# Fit image to window
		win.update_idletasks()
		max_w = win.winfo_width()
		max_h = win.winfo_height()

		img = pil_img.copy()
		img.thumbnail((max_w, max_h), Image.LANCZOS)

		photo = ImageTk.PhotoImage(img)

		# Keep reference
		canvas.image = photo

		# Draw centered
		canvas.create_image(
			max_w // 2,
			max_h // 2,
			image=photo,
			anchor="center"
		)

	def _open_image_viewer(self):
		if not self.results_listbox.curselection():
			return

		idx = self.results_listbox.curselection()[0]
		image_path = self.results[idx]["image_path"]

		if not os.path.exists(image_path):
			self.status_var.set("Status: Image file not found")
			return

		ImageViewer(self, image_path)


	def _browse_export_dir(self):
		path = filedialog.askdirectory(title="Select export directory")
		if path:
			self.export_dir_var.set(path)


	def _export_images(self, results):
		export_base = self.export_dir_var.get()
		if not export_base:
			self.status_var.set("Status: No export directory selected")
			return
		os.makedirs(export_base, exist_ok=True)
		query_name = os.path.basename(self.query_image_path.get())
		query_dir = os.path.join(export_base, query_name)

		os.makedirs(query_dir, exist_ok=True)


		for r in results:
			src_path = r["image_path"]
			distance = r["distance"]

			if not os.path.exists(src_path):
				continue

			base_name = os.path.basename(src_path)
			prefix = f"{distance:.3f}-"
			dest_name = prefix + base_name

			dest_path = self._resolve_collision(
				os.path.join(query_dir, dest_name)
			)

			shutil.copy2(src_path, dest_path)

	def _resolve_collision(self, path):
		base, ext = os.path.splitext(path)
		counter = 1

		while os.path.exists(path):
			path = f"{base}_{counter}{ext}"
			counter += 1

		return path



	def _export_images_old(self, image_paths):
		"""
		Copies image files into:
		<export_dir>/<query_image_name>/<filename>
		Appends _N if filename already exists.
		"""
		if not image_paths:
			self.status_var.set("Status: No images to export")
			return

		export_root = self.export_dir_var.get()
		if not export_root:
			self.status_var.set("Status: No export directory set")
			return

		query_name = os.path.splitext(
			os.path.basename(self.query_image_path.get())
		)[0]

		target_dir = os.path.join(export_root, query_name)
		os.makedirs(target_dir, exist_ok=True)

		for src_path in image_paths:
			try:
				base = os.path.basename(src_path)
				name, ext = os.path.splitext(base)

				dest_path = os.path.join(target_dir, base)
				counter = 1

				while os.path.exists(dest_path):
					dest_path = os.path.join(
						target_dir,
						f"{name}_{counter}{ext}"
					)
					counter += 1

				shutil.copy2(src_path, dest_path)

				self.status_var.set(f"Exported: {os.path.basename(dest_path)}")

			except Exception as e:
				self.status_var.set("Status: Export error")
				# optionally emit a log event here




	def _export_selected_image(self):
		if not self.results_listbox.curselection():
			self.status_var.set("Status: No image selected")
			return

		idx = self.results_listbox.curselection()[0]
#		image_path = self.results[idx]["image_path"]

#		self._export_images([image_path])
		self._export_images([self.results[idx]])


	def _export_all_images(self):
		if not self.results:
			return
		self._export_images(self.results)
		# if not getattr(self, "results", None):
		# 	self.status_var.set("Status: No results to export")
		# 	return

		# image_paths = [r["image_path"] for r in self.results]
		# self._export_images(image_paths)







	def _export_selected_image_old(self):
		if not self.results_listbox.curselection():
			self.status_var.set("Status: No result selected")
			return

		export_root = self.export_dir_var.get()
		if not export_root:
			self.status_var.set("Status: Select export directory")
			return

		idx = self.results_listbox.curselection()[0]
		source_path = self.results[idx]["image_path"]

		if not os.path.exists(source_path):
			self.status_var.set("Status: Source file missing")
			return

		# Build target directory
		query_name = os.path.basename(self.query_image_path.get())
		target_dir = os.path.join(export_root, query_name)

		os.makedirs(target_dir, exist_ok=True)

		target_path = os.path.join(
			target_dir,
			os.path.basename(source_path)
		)

		try:
			shutil.copy2(source_path, target_path)
		except Exception as e:
			self.status_var.set("Status: Export failed")
#			self.emit(f"Export failed: {e}")
			return

		self.status_var.set("Status: Image exported")
#		self.emit(f"Exported to {target_path}")
