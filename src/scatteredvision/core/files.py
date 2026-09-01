import hashlib
import os

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}

def is_image(path):
	return os.path.splitext(path.lower())[1] in IMAGE_EXTENSIONS

def file_md5(path, chunk_size=8192):
	hash_md5 = hashlib.md5()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(chunk_size), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()
