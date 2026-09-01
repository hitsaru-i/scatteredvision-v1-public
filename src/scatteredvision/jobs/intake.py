import os
import time
import face_recognition
from PIL import Image

from scatteredvision.jobs.base import BaseJob
from scatteredvision.core.database import init_db
from scatteredvision.core.files import is_image, file_md5
from scatteredvision.core.db_faces import (
	np,
	load_face_clusters,
	create_face_cluster,
	insert_face,
	encode_face_vector,
)

def is_supported_image(filename):
	ext = os.path.splitext(filename)[1].lower()
	return ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_readable_image(path):
	try:
		with Image.open(path) as img:
			img.verify()
		return True
	except Exception:
		return False


class IntakeJob(BaseJob):
	def run(self):
		try:
			start_time = time.time()
			self.emit("JOB_STARTED", {
				"job_type": "INTAKE",
				"root_dir": self.config.root_dir
			})
			self.conn = init_db(self.config.db_path)
			self.cursor = self.conn.cursor()

		##### Load known face clusters once per job
			face_clusters = load_face_clusters(self.conn)

			files_processed = 0
			images_found = 0

			# Pre-count files (best effort)
			self.emit("STATUS", {"message": "Calculating total files. This may take a long time"})
			self.emit("PROGRESS", {"current": 0, "total": 1, "unit":"files"})
			total_files = sum(
				1
				for _, _, files in os.walk(self.config.root_dir)
				for name in files
				if is_supported_image(name)
			)

			for root, _, files in os.walk(self.config.root_dir):
				self.check_cancel()
				self.emit("STATUS", {"message": f"Scanning {root}"})

				for name in files:
					self.check_cancel()
					files_processed += 1

					full_path = os.path.join(root, name)

					self.emit("PROGRESS", {
						"current": files_processed,
						"total": total_files,
						"unit": "files"
					})

					if not is_image(full_path):
						continue

					if not is_readable_image(full_path):
						self.emit("JOB_LOG", {
							"message": f"Unreadable or corrupt image skipped",
							"path": full_path
						})
						continue
				

					try:
						md5 = file_md5(full_path)
						mtime = os.path.getmtime(full_path)

						self.cursor.execute(
							"""
							INSERT OR IGNORE INTO images
							(path, md5, mtime, ingested_at)
							VALUES (?, ?, ?, ?)
							""",
							(full_path, md5, mtime, time.time())
						)

						is_new_image = self.cursor.rowcount == 1
						if self.cursor.rowcount:
							images_found += 1
							self.emit("PREVIEW_DATA", {
								"image_path": full_path
							})

						self.conn.commit()
						# Validate image as new from md5
						if not is_new_image:
							continue


	#####			##### Fetch image_id
						self.cursor.execute(
							"SELECT id FROM images WHERE path = ?",
							(full_path,)
						)
						row = self.cursor.fetchone()
						if not row:
							return
						image_id = row[0]
						try:
							image = face_recognition.load_image_file(full_path)
							locations = face_recognition.face_locations(image)
							encodings = face_recognition.face_encodings(image, locations)
							self.emit("JOB_LOG", {
								"message": f"Faces detected: {len(encodings)}",
								"path": full_path
							})

						except Exception as e:
							self.emit("JOB_LOG", {
								"message": f"Face scan failed: {full_path} ({e})"
							})
#							return
							continue

						for encoding, (top, right, bottom, left) in zip(encodings, locations):
							cluster_id = None

							if face_clusters:
								known_ids, known_encs = zip(*face_clusters)
								distances = face_recognition.face_distance(
									np.array(known_encs),
									encoding
								)

								best_idx = np.argmin(distances)
								if distances[best_idx] <= self.config.tolerance:
									cluster_id = known_ids[best_idx]

							if cluster_id is None:
								cluster_id = create_face_cluster(
									self.conn,
									encode_face_vector(encoding),
									time.time()
								)
								face_clusters.append((cluster_id, encoding))


							insert_face(
								self.conn,
								image_id,
								cluster_id,
								encode_face_vector(encoding),
								top,
								right,
								bottom,
								left,
								time.time()
							)
					except Exception as e:
						self.emit("ERROR", {
							"code": "FILE_PROCESS_FAIL",
							"path": full_path,
							"exception": str(e)
						})
		except RuntimeError as e:
			if str(e) == "Job cancelled":
				self.emit("JOB_CANCELLED")
			else:
				raise
		finally:
			self.conn.close()

		self.emit("JOB_COMPLETED", {
			"files_scanned": files_processed,
			"images_recorded": images_found,
			"duration_seconds": round(time.time() - start_time, 2)
		})
