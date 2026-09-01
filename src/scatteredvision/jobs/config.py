class IntakeConfig:
	def __init__(self, root_dir, db_path, tolerance=0.50):
		self.root_dir = root_dir
		self.db_path = db_path
		self.tolerance = tolerance



class SearchConfig:
	def __init__(self, db_path, query_image_path, default_export_dir, tolerance=0.50):
		self.db_path = db_path
		self.query_image_path = query_image_path
		self.default_export_dir = default_export_dir
		self.tolerance = tolerance

class ClusterReviewConfig:
	def __init__(self, db_path, order):
		self.db_path = db_path
		self.order = order
