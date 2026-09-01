import json
import os

DEFAULT_CONFIG = {
	"default_root_dir": "",
	"default_db_file": "",
	"default_tolerance": 0.5,
	"default_export_dir": ""
}

CONFIG_PATH = os.path.expanduser("~/.scatteredvision/config.json")

def load_config():
	# Ensure config directory exists
	config_dir = os.path.dirname(CONFIG_PATH)
	if not os.path.exists(config_dir):
		os.makedirs(config_dir)

	# If config file missing, create default
	if not os.path.exists(CONFIG_PATH):
		save_config(DEFAULT_CONFIG)

	with open(CONFIG_PATH, "r") as f:
		try:
			data = json.load(f)
		except json.JSONDecodeError:
			# fallback if file is corrupted
			data = DEFAULT_CONFIG
	return data

def save_config(config_dict):
	config_dir = os.path.dirname(CONFIG_PATH)
	if not os.path.exists(config_dir):
		os.makedirs(config_dir)
	with open(CONFIG_PATH, "w") as f:
		json.dump(config_dict, f, indent=4)

