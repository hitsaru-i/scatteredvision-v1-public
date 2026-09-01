import os
import time
import sqlite3
import numpy as np
import face_recognition


from scatteredvision.jobs.base import BaseJob
from scatteredvision.jobs.config import SearchConfig
from scatteredvision.core.db_faces import decode_face_vector



class SearchJob(BaseJob):
	def __init__(self, job_id, config: SearchConfig, event_queue):
		super().__init__(job_id, config, event_queue)
		self.conn = None
		self.cursor = None

	def run(self):
		start_time = time.time()
		self.check_cancel()

		self.emit("JOB_STARTED", {
			"job_type": "SEARCH",
			"query_image": self.config.query_image_path
		})

		# --- Open database ---
		conn = sqlite3.connect(self.config.db_path)
		cursor = conn.cursor()

		# --- Load and encode query image ---
		try:
			image = face_recognition.load_image_file(self.config.query_image_path)
			locations = face_recognition.face_locations(image)
			encodings = face_recognition.face_encodings(image, locations)
		except Exception as e:
			self.emit("JOB_FAIL", {
				"exception": f"Failed to load query image: {e}"
			})
			return

		if not encodings:
			self.emit("JOB_FAIL", {
				"exception": "No faces detected in query image"
			})
			return

		if len(encodings) > 1:
			self.emit("JOB_LOG", {
				"message": f"Multiple faces detected ({len(encodings)}); using first face only"
			})

		query_encoding = encodings[0]

		self.emit("JOB_LOG", {
			"message": "Query face encoded successfully"
		})

		# --- Load all faces from DB ---
		cursor.execute(
			"""
			SELECT
				images.path,
				faces.encoding,
				faces.cluster_id
			FROM faces
			JOIN images ON faces.image_id = images.id
			"""
		)

		rows = cursor.fetchall()
		total_faces = len(rows)

		self.emit("JOB_LOG", {
			"message": f"Loaded {total_faces} face encodings from database"
		})

		# --- Distance evaluation ---
		best_matches = {}
		processed = 0

		for image_path, encoding_blob, cluster_id in rows:
			self.check_cancel()

			try:
				known_encoding = decode_face_vector(encoding_blob)
				distance = face_recognition.face_distance(
					[np.array(known_encoding)],
					query_encoding
				)[0]
			except Exception as e:
				self.emit("JOB_LOG", {
					"message": f"Distance calc failed for {image_path}: {e}"
				})
				continue

			if distance <= self.config.tolerance:
				if (
					image_path not in best_matches
					or distance < best_matches[image_path]["distance"]
				):
					best_matches[image_path] = {
						"distance": distance,
						"cluster_id": cluster_id
					}


			processed += 1
			if processed % 250 == 0:
				self.emit("PROGRESS", {
					"current": processed,
					"total": total_faces,
					"unit": "faces"
				})

		# --- Sort results ---

		results = [
			{
				"image_path": path,
				"distance": data["distance"],
				"cluster_id": data["cluster_id"]
			}
			for path, data in best_matches.items()
		]

		results.sort(key=lambda r: r["distance"])

		self.emit("SEARCH_RESULTS", {
			"count": len(results),
			"results": results
		})

		self.emit("JOB_FINISHED", {
			"elapsed": time.time() - start_time,
			"matches": len(results)
		})
		try:
			if conn:
				conn.close()
		except Exception:
			pass
