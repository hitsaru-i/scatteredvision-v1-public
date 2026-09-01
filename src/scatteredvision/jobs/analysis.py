import sqlite3
import os

from scatteredvision.core.db_faces import (
	load_analysis_overview,
	load_cluster_stats,
	load_cluster_distribution,
	recalibrate_clusters
)

from scatteredvision.jobs.base import BaseJob



class ReadMetricsJob(BaseJob):
	def __init__(self, job_id, config, event_queue, db_path):
		super().__init__(job_id, config, event_queue)
		self.db_path = db_path

	def run(self):
		self.emit("status", "Reading analysis metrics")

		conn = sqlite3.connect(self.db_path)
		try:
			overview = load_analysis_overview(conn)
			stats = load_cluster_stats(conn)
			distribution = load_cluster_distribution(conn)
		finally:
			conn.close()

		self.emit("metrics", {
			"overview": overview,
			"stats": stats,
			"distribution": distribution
		})

		self.emit("status", "Analysis metrics updated")


class RecalibrateClustersJob(BaseJob):
	def __init__(self, job_id, config, event_queue, db_path, tolerance):
		super().__init__(job_id, config, event_queue)
		self.db_path = db_path
		self.tolerance = tolerance

	def _progress_cb(self, current, total):
		percent = int((current / total) * 100)
		self.emit("progress", percent)
		self.emit("status", f"Rebuilding clusters: {current}/{total}")

	def _status_cb(self, msg):
		self.emit("status", msg) 



	def run(self):
		self.emit("status", "Starting cluster recalibration")
		self.emit("status", f"Using tolerance={self.tolerance}")
		# print ("Run Starting, Job object id: ", id(self))

		def cancel_cb():
#			print ("CANCEL CHECK")
			self.check_cancel()
		conn = sqlite3.connect(self.db_path)
		try:
			recalibrate_clusters(
				conn,
				self.tolerance,
				progress_cb=self._progress_cb,
				status_cb=self._status_cb,
				cancel_cb=cancel_cb
			)
		except RuntimeError as e:
			if str(e) == "Job cancelled":
				self.emit("status", "Recalibration cancelled by user")
				return
			else:
				raise
		finally:
			conn.close()
		self.emit("progress", 100)
		self.emit("status", "Recalibration complete")