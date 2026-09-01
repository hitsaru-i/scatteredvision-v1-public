#!/usr/bin/env bash
#! TODO add install for gcc, cmake
#! TODO add install for python3-tk


set -euo pipefail

########################################
# Scattered Vision – Environment Setup #
########################################

echo "Scattered Vision – Environment Setup"
echo "Linux / Ubuntu-based systems only"
echo

########################################
# 1. Guardrails
########################################

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
	echo "ERROR: Do not run this script inside an active virtual environment."
	exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
	echo "ERROR: Do not run this script as root."
	echo "Use a regular user account."
	exit 1
fi

########################################
# 2. Platform Verification
########################################

if [[ "$(uname -s)" != "Linux" ]]; then
	echo "ERROR: This project supports Linux only."
	exit 1
fi

if [[ -f /etc/os-release ]]; then
	if ! grep -qiE 'ubuntu|debian' /etc/os-release; then
		echo "WARNING: This system does not appear to be Ubuntu/Debian-based."
		echo "Proceeding is unsupported and may fail."
	fi
else
	echo "WARNING: Cannot determine distribution type."
fi

########################################
# 3. Python Discovery & Validation
########################################

if command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python3)"
else
	echo "ERROR: python3 not found in PATH."
	exit 1
fi

PYTHON_VERSION="$($PYTHON_BIN - <<'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
EOF
)"

PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
PYTHON_MINOR="${PYTHON_VERSION##*.}"

if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 10) )); then
	echo "ERROR: Python >= 3.10 is required."
	echo "Detected: Python ${PYTHON_VERSION}"
	exit 1
fi

if [[ "${PYTHON_VERSION}" == "3.12" ]]; then
	echo "WARNING: Python 3.12 support is experimental."
	echo "face_recognition may fail depending on system toolchain."
fi

echo "Using Python ${PYTHON_VERSION}"


########################################
# 4. Toolchain Checks & Dependencies
########################################

echo "Checking required system dependencies..."

REQUIRED_PACKAGES=(
	build-essential
	cmake
	python3-dev
	python3-tk
)

MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
	if ! dpkg -s "$package" >/dev/null 2>&1; then
		MISSING_PACKAGES+=("$package")
	fi
done

if (( ${#MISSING_PACKAGES[@]} > 0 )); then
	echo "Installing missing system packages:"
	printf '  %s\n' "${MISSING_PACKAGES[@]}"

	sudo apt-get update
	sudo apt-get install -y "${MISSING_PACKAGES[@]}"
fi

GCC_VERSION="$(gcc -dumpversion)"
echo "Detected gcc ${GCC_VERSION}"

CMAKE_VERSION="$(cmake --version | head -n1 | awk '{print $3}')"
echo "Detected cmake ${CMAKE_VERSION}"

echo "System dependencies satisfied."


########################################
# 5. Virtual Environment Creation
########################################

VENV_PATH="./venv"

if [[ ! -d "${VENV_PATH}" ]]; then
	echo "Creating virtual environment at ${VENV_PATH}"
	"$PYTHON_BIN" -m venv "${VENV_PATH}"
else
	if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
		echo "ERROR: ${VENV_PATH} exists but is not a valid virtual environment."
		exit 1
	fi

	VENV_PYTHON_VERSION="$("${VENV_PATH}/bin/python" - <<'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
EOF
)"

	if [[ "${VENV_PYTHON_VERSION}" != "${PYTHON_VERSION}" ]]; then
		echo "ERROR: Existing venv uses Python ${VENV_PYTHON_VERSION},"
		echo "but system Python is ${PYTHON_VERSION}."
		exit 1
	fi

	echo "Reusing existing virtual environment."
fi

########################################
# 6. Activate venv (local to script)
########################################

# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"

########################################
# 7. Dependency Installation
########################################

echo "Upgrading pip tooling..."
pip install --upgrade pip setuptools wheel

echo "Installing base requirements..."
pip install -r requirements/base.txt

echo "Installing face recognition requirements..."
pip install -r requirements/face.txt

########################################
# 8. Post-Install Validation
########################################

echo "Validating face_recognition installation..."

python - <<'EOF'
import sys
import numpy as np
import face_recognition

# Create a dummy image (no face expected, but encoding pipeline should run)
dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)

try:
	encodings = face_recognition.face_encodings(dummy_image)
except Exception as e:
	print("ERROR: face encoding call failed:", e)
	sys.exit(1)

print("face_recognition import and execution succeeded.")
EOF

########################################
# 9. Install ScatteredVision pip
########################################

echo "[+] Installing ScatteredVision (editable)"
pip install -e .

########################################
# 10. Success Summary
########################################

echo
echo "Environment setup successful."
echo "Python version: ${PYTHON_VERSION}"
echo "Virtual environment: ${VENV_PATH}"
echo
echo "Next steps:"
echo "Activate venv:"
echo "  source venv/bin/activate"
echo "Invoke Scattered Vision in venv:"
echo "  scatteredvision"

exit 0
