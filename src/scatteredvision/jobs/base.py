import time

class BaseJob:
	def __init__(self, job_id, config, event_queue):
		self.job_id = job_id
		self.config = config
		self.event_queue = event_queue
		self._cancel = False

	def emit(self, event_type, payload=None):
		from scatteredvision.core.events import JobEvent
		self.event_queue.put(JobEvent(self.job_id, event_type, payload))

	def request_cancel(self):
		self._cancel = True

	def check_cancel(self):
		# print("check_cancel called, _cancel =", self._cancel)		
		if self._cancel:
			raise RuntimeError("Job cancelled")

	def run(self):
		raise NotImplementedError
