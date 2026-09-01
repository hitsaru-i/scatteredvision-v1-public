import time

class JobEvent:
	def __init__(self, job_id, event_type, payload=None):
		self.job_id = job_id
		self.event_type = event_type
		self.payload = payload or {}
		self.timestamp = time.time()

	def get(self, key, default=None):
		# Proxy to payload dict
		return self.payload.get(key, default)