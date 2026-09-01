import sqlite3

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS images (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	path TEXT UNIQUE NOT NULL,
	md5 TEXT NOT NULL,
	mtime REAL NOT NULL,
	ingested_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_images_md5 ON images(md5);

CREATE TABLE IF NOT EXISTS face_clusters (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	representative_encoding BLOB NOT NULL,
	created_at REAL NOT NULL,
	label TEXT
);

CREATE TABLE IF NOT EXISTS faces (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	image_id INTEGER NOT NULL,
	cluster_id INTEGER NOT NULL,
	encoding BLOB NOT NULL,
	bbox_top INTEGER NOT NULL,
	bbox_right INTEGER NOT NULL,
	bbox_bottom INTEGER NOT NULL,
	bbox_left INTEGER NOT NULL,
	detected_at REAL NOT NULL,

	FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE,
	FOREIGN KEY(cluster_id) REFERENCES face_clusters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_faces_image_id ON faces(image_id);
CREATE INDEX IF NOT EXISTS idx_faces_cluster_id ON faces(cluster_id);

"""

def init_db(db_path):
	conn = sqlite3.connect(db_path)
	conn.executescript(SCHEMA_SQL)
	conn.commit()
	return conn
