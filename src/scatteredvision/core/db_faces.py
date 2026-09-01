
import numpy as np
import time
import face_recognition

def encode_face_vector(vec):
	return vec.astype(np.float32).tobytes()

def decode_face_vector(blob):
	return np.frombuffer(blob, dtype=np.float32)

def load_face_clusters(conn):
	cursor = conn.execute(
		"SELECT id, representative_encoding FROM face_clusters"
	)
	clusters = []
	for cluster_id, encoding_blob in cursor.fetchall():
		encoding = decode_face_vector(encoding_blob)
		clusters.append((cluster_id, encoding))
	return clusters	

def create_face_cluster(conn, encoding_blob, created_at):
	cursor = conn.execute(
		"""
		INSERT INTO face_clusters (representative_encoding, created_at)
		VALUES (?, ?)
		""",
		(encoding_blob, created_at)
	)
	return cursor.lastrowid

def insert_face(
	conn,
	image_id,
	cluster_id,
	encoding_blob,
	bbox_top,
	bbox_right,
	bbox_bottom,
	bbox_left,
	detected_at
):
	conn.execute(
		"""
		INSERT INTO faces (
			image_id,
			cluster_id,
			encoding,
			bbox_top,
			bbox_right,
			bbox_bottom,
			bbox_left,
			detected_at
		)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		""",
		(
			image_id,
			cluster_id,
			encoding_blob,
			bbox_top,
			bbox_right,
			bbox_bottom,
			bbox_left,
			detected_at,
		)
	)

def insert_image(conn, path, md5, mtime, ingested_at):
	cursor = conn.execute(
		"""
		INSERT OR IGNORE INTO images (path, md5, mtime, ingested_at)
		VALUES (?, ?, ?, ?)
		""",
		(path, md5, mtime, ingested_at)
	)
	return cursor.lastrowid


### Cluster review--

def load_clusters_with_image_counts(conn, order="id"):
	if order == "asc":
		order_clause = "image_count ASC"
	elif order == "desc":
		order_clause = "image_count DESC"
	else:
		order_clause = "cluster_id ASC"

	cursor = conn.execute(
		f"""
		SELECT
			fc.id AS cluster_id,
			COUNT(DISTINCT f.image_id) AS image_count,
			fc.label
		FROM face_clusters fc
		JOIN faces f ON f.cluster_id = fc.id
		GROUP BY fc.id
		ORDER BY {order_clause}
		"""
	)

	return [
		{
			"cluster_id": row[0],
			"image_count": row[1],
			"label": row[2],
		}
		for row in cursor.fetchall()
	]

def load_images_for_cluster(conn, cluster_id):
	cursor = conn.execute(
		"""
		SELECT DISTINCT i.id, i.path
		FROM images i
		JOIN faces f ON f.image_id = i.id
		WHERE f.cluster_id = ?
		ORDER BY i.path
		""",
		(cluster_id,)
	)
	return [{"image_id": r[0], "path": r[1]} for r in cursor.fetchall()]


#######

def get_database_overview(conn):
	cursor = conn.execute(
		"""
		SELECT
			(SELECT COUNT(*) FROM images) AS total_images,
			(SELECT COUNT(*) FROM faces) AS total_faces,
			(SELECT COUNT(*) FROM face_clusters) AS total_clusters,
			(SELECT MAX(ingested_at) FROM images) AS last_ingest
		"""
	)

	row = cursor.fetchone()
	return {
		"total_images": row[0],
		"total_faces": row[1],
		"total_clusters": row[2],
		"last_ingest": row[3],
	}

def get_cluster_size_stats(conn):
	cursor = conn.execute(
		"""
		SELECT
			AVG(face_count),
			MIN(face_count),
			MAX(face_count)
		FROM (
			SELECT COUNT(*) AS face_count
			FROM faces
			GROUP BY cluster_id
		)
		"""
	)

	row = cursor.fetchone()
	return {
		"avg_faces_per_cluster": row[0],
		"min_faces_per_cluster": row[1],
		"max_faces_per_cluster": row[2],
	}

def get_singleton_cluster_count(conn):
	cursor = conn.execute(
		"""
		SELECT COUNT(*)
		FROM (
			SELECT cluster_id
			FROM faces
			GROUP BY cluster_id
			HAVING COUNT(*) = 1
		)
		"""
	)
	return cursor.fetchone()[0]

def get_cluster_size_distribution(conn):
	cursor = conn.execute(
		"""
		SELECT
			face_count,
			COUNT(*) AS cluster_count
		FROM (
			SELECT COUNT(*) AS face_count
			FROM faces
			GROUP BY cluster_id
		)
		GROUP BY face_count
		ORDER BY face_count ASC
		"""
	)

	return [
		{
			"face_count": row[0],
			"cluster_count": row[1],
		}
		for row in cursor.fetchall()
	]


def load_analysis_overview(conn):
	cursor = conn.cursor()

	total_images = cursor.execute(
		"SELECT COUNT(*) FROM images"
	).fetchone()[0]

	total_faces = cursor.execute(
		"SELECT COUNT(*) FROM faces"
	).fetchone()[0]

	total_clusters = cursor.execute(
		"SELECT COUNT(*) FROM face_clusters"
	).fetchone()[0]

	singletons = cursor.execute(
		"""
		SELECT COUNT(*) FROM (
			SELECT cluster_id
			FROM faces
			GROUP BY cluster_id
			HAVING COUNT(*) = 1
		)
		"""
	).fetchone()[0]

	return {
		"images": total_images,
		"faces": total_faces,
		"clusters": total_clusters,
		"singletons": singletons,
	}


def load_cluster_stats(conn):
	cursor = conn.cursor()

	row = cursor.execute(
		"""
		SELECT
			AVG(face_count),
			MIN(face_count),
			MAX(face_count)
		FROM (
			SELECT COUNT(*) AS face_count
			FROM faces
			GROUP BY cluster_id
		)
		"""
	).fetchone()

	return {
		"avg": row[0],
		"min": row[1],
		"max": row[2],
	}

def load_cluster_distribution(conn):
	cursor = conn.cursor()

	cursor.execute(
		"""
		SELECT
			face_count,
			COUNT(*) AS cluster_count
		FROM (
			SELECT COUNT(*) AS face_count
			FROM faces
			GROUP BY cluster_id
		)
		GROUP BY face_count
		ORDER BY face_count ASC
		"""
	)

	return [
		{
			"face_count": row[0],
			"cluster_count": row[1],
		}
		for row in cursor.fetchall()
	]


def recalibrate_clusters(conn, tolerance, progress_cb=None, status_cb=None, cancel_cb=None):
	cursor = conn.cursor()

	# Load immutable face data
	cursor.execute("""
		SELECT
			image_id,
			encoding,
			bbox_top,
			bbox_right,
			bbox_bottom,
			bbox_left,
			detected_at
		FROM faces
	""")

	raw_faces = cursor.fetchall()

	decoded_faces = [
		(
			row[0],
			decode_face_vector(row[1]),
			row[2:6],
			row[6]
		)
		for row in raw_faces
	]
	total = len(decoded_faces)
	conn.execute("BEGIN")
	if status_cb:
		status_cb("Clearing existing clusters")
	conn.execute("DELETE FROM faces")
	conn.execute("DELETE FROM face_clusters")
	if status_cb:
		status_cb("Rebuilding face relationships")
	face_clusters = []
	try:
		for idx, (image_id, encoding, bbox, detected_at) in enumerate(decoded_faces):
		#for image_id, encoding, bbox, detected_at in decoded_faces:
			cluster_id = None

			if face_clusters:
				ids, encs = zip(*face_clusters)
				distances = face_recognition.face_distance(
					np.array(encs),
					encoding
				)
				best_idx = np.argmin(distances)

				if distances[best_idx] <= tolerance:
					cluster_id = ids[best_idx]

			if cluster_id is None:
				cluster_id = create_face_cluster(
					conn,
					encode_face_vector(encoding),
					time.time()
				)
				face_clusters.append((cluster_id, encoding))

			insert_face(
				conn,
				image_id,
				cluster_id,
				encode_face_vector(encoding),
				*bbox,
				detected_at
			)
			if progress_cb:
				progress_cb(idx +1, total)
			if cancel_cb:
				# print ("cancel check idx: ", idx)
				cancel_cb()

		conn.commit()
	except RuntimeError:
		conn.rollback()
		raise