import time
import sqlite3

from scatteredvision.jobs.config import ClusterReviewConfig
from scatteredvision.core.db_faces import load_clusters_with_image_counts
from scatteredvision.jobs.base import BaseJob


class ClusterReviewJob(BaseJob):
	def __init__(self, job_id, config: ClusterReviewConfig, event_queue):
		super().__init__(job_id, config, event_queue)

	def run(self):
		start_time = time.time()
		conn = None

		self.check_cancel()

		self.emit("JOB_STARTED", {
			"job_type": "CLUSTER_REVIEW"
		})

		try:
			conn = sqlite3.connect(self.config.db_path)

			clusters = load_clusters_with_image_counts(
				conn,
				order=self.config.order
			)

			self.emit("CLUSTER_RESULTS", {
				"count": len(clusters),
				"clusters": clusters
			})

			self.emit("JOB_FINISHED", {
				"elapsed": time.time() - start_time,
				"clusters": len(clusters)
			})

		except Exception as e:
			self.emit("JOB_FAIL", {
				"exception": f"Failed to load clusters: {e}"
			})

		finally:
			if conn:
				conn.close()