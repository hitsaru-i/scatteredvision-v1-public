
import tkinter as tk
from PIL import Image, ImageTk
import os


class ImageViewer(tk.Toplevel):
	def __init__(self, parent, image_path):
		super().__init__(parent)

		self.title(os.path.basename(image_path))
		self.geometry("800x600")
		self.zoom = 1.0
		self.min_zoom = 0.1
		self.max_zoom = 5.0

		self.offset_x = 0
		self.offset_y = 0

		self._drag_start_x = None
		self._drag_start_y = None		

		self.zoom_percent = 100

		self.image_path = image_path

		# Canvas
		self.canvas = tk.Canvas(self, bg="black")
		self.canvas.pack(fill="both", expand=True)

		self._load_image(image_path)

		# Zoom Label
		self.zoom_label = tk.Label(
		 	self.canvas,
			text="100%",  # initial zoom
			bg="black",
		 	fg="white",
			font=("Arial", 12, "bold"),
			bd=1,
			relief="solid"
		)
		# place it top-right
		self.zoom_label.place(relx=0.98, rely=0.02, anchor="ne")

		# Mouse wheel zoom bindings
		# self.canvas.bind("<MouseWheel>", self._on_mousewheel)      # Windows
		# self.canvas.bind("<Button-4>", self._on_mousewheel)        # Linux scroll up
		# self.canvas.bind("<Button-5>", self._on_mousewheel)        # Linux scroll down
		#Mouse wheel zoom bindings
		self.canvas.bind("<MouseWheel>", self._on_mousewheel)      # Windows
		self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.1))  # Linux
		self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 0.9))
		# Keyboard zoom bindings
		self.bind("<plus>", lambda e: self._zoom_in())
		self.bind("<minus>", lambda e: self._zoom_out())
		# # Fallbacks (keyboard/layout safety)
		self.bind("<KeyPress-equal>", lambda e: self._zoom_in())  # Shift+=
		self.bind("<KeyPress-minus>", lambda e: self._zoom_out())	
		# Numpad zoom bindings
		self.bind("<KP_Add>", lambda e: self._zoom_in())
		self.bind("<KP_Subtract>", lambda e: self._zoom_out())			
		# Mouse Pan Bindings
		self.canvas.bind("<ButtonPress-1>", self._start_pan)
		self.canvas.bind("<B1-Motion>", self._do_pan)
		self.canvas.bind("<ButtonRelease-1>", self._end_pan)
		# Reset zoom postion actions
		self.canvas.bind("<Double-Button-1>", lambda e: self.reset_view())
		self.bind("<r>", lambda e: self.reset_view())
		self.bind("<R>", lambda e: self.reset_view())		
		self.focus_set()

		# Load original image ONCE
		self.original_image = Image.open(self.image_path)


		# Render after layout
		self.after(50, self._render_image)

	def _update_zoom_label(self):
	    self.zoom_percent = int(self.zoom * 100)
	    self.zoom_label.config(text=f"{self.zoom_percent}%")


	def _render_image(self):
		canvas_width = self.canvas.winfo_width()
		canvas_height = self.canvas.winfo_height()

		if canvas_width <= 1 or canvas_height <= 1:
			self.after(50, self._render_image)
			return

		# Calculate scaled size
		base_w, base_h = self.original_image.size
		scaled_w = int(base_w * self.zoom)
		scaled_h = int(base_h * self.zoom)

		img = self.original_image.resize(
			(scaled_w, scaled_h),
			Image.LANCZOS
		)

		self.photo = ImageTk.PhotoImage(img)

		self.canvas.delete("all")
		self.canvas.create_image(
			canvas_width // 2 + self.offset_x,
			canvas_height // 2 + self.offset_y,
			image=self.photo,
			anchor="center"
		)

	def _zoom_in(self, event=None):
		self.zoom = min(self.zoom * 1.1, self.max_zoom)
		self._render_image()
		self._update_zoom_label()

	def _zoom_out(self, event=None):
		self.zoom = max(self.zoom / 1.1, self.min_zoom)
		self._render_image()
		self._update_zoom_label()

	def _on_mousewheel(self, event):
		if event.delta > 0 or event.num == 4:
			self._zoom_in()
		else:
			self._zoom_out()

	def _start_pan(self, event):
		self.focus_set()
		self._drag_start_x = event.x
		self._drag_start_y = event.y

	def _do_pan(self, event):
		if self._drag_start_x is None:
			return

		dx = event.x - self._drag_start_x
		dy = event.y - self._drag_start_y

		self.offset_x += dx
		self.offset_y += dy

		self._drag_start_x = event.x
		self._drag_start_y = event.y

		self._render_image()

	def _end_pan(self, event):
		self._drag_start_x = None
		self._drag_start_y = None

	def reset_view(self):
		self.zoom = 1.0
		self.offset_x = 0
		self.offset_y = 0
		self._render_image()

	def _on_mousewheel(self, event):
		if event.delta > 0:
			self._zoom_at(event.x, event.y, 1.1)
		else:
			self._zoom_at(event.x, event.y, 0.9)

	def _zoom_at(self, cursor_x, cursor_y, zoom_factor):
		old_zoom = self.zoom
		new_zoom = self.zoom * zoom_factor

		# Clamp zoom
		new_zoom = max(0.1, min(new_zoom, 10.0))
		zoom_factor = new_zoom / old_zoom

		if zoom_factor == 1.0:
			return

		# Canvas center
		canvas_w = self.canvas.winfo_width()
		canvas_h = self.canvas.winfo_height()
		center_x = canvas_w // 2
		center_y = canvas_h // 2

		# Vector from image center to cursor
		dx = cursor_x - (center_x + self.offset_x)
		dy = cursor_y - (center_y + self.offset_y)

		# Adjust offset so cursor stays fixed
		self.offset_x -= dx * (zoom_factor - 1)
		self.offset_y -= dy * (zoom_factor - 1)

		self.zoom = new_zoom
		self._render_image()
		self._update_zoom_label()

	def _load_image(self, path):
			try:
				pil_img = Image.open(path)
			except Exception as e:
				print(f"Failed to load image: {e}")
				self.destroy()
				return
			self.image_original = pil_img
			self.photo = ImageTk.PhotoImage(pil_img)
			self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
