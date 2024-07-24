import os
import sys
from .utils.find_pythons import find_python_versions_windows


PYTHON_VERSIONS = find_python_versions_windows()
FBX_HEAD_COLLECTION = "FBX_HEAD"
FBX_BODY_COLLECTION = "FBX_BODY"
FBX_CLOTH_COLLECTION = "FBX_CLOTH"
INITIAL_SHAPE_COLLECTION = "INIT_SHAPE"
FINAL_SHAPE_COLLECTION = "FINAL_SHAPE"
SYSTEM_COLLECTION = "MRF_SYSTEM_OBJECTS"
DEFAULT_EDIT_ID = "skin"

SWIG_WIN_DOWNLOAD_LINK = "http://prdownloads.sourceforge.net/swig/swigwin-4.1.1.zip"

DNA_CALIB_DOWNLOAD_LINK = "https://github.com/EpicGames/MetaHuman-DNA-Calibration/archive/refs/tags/1.2.0.zip"

DNA_CALIB_URL = "https://github.com/EpicGames/MetaHuman-DNA-Calibration"

DNA_CALIB_VTX_COLOR_PATH = "data/vtx_color.py"
DNA_CALIB_WIN_PY39_SUBFOLDER = "lib/Maya2023/windows/"
DNA_CALIB_WIN_PY37_SUBFOLDER = "lib/Maya2022/windows/"
DNA_CALIB_LIN_PY37_SUBFOLDER = "lib/Maya2022/linux/"
DNA_CALIB_LIN_PY39_SUBFOLDER = "lib/Maya2023/linux/"

DNA_CALIB_WIN_FILES = [
    "_py3dna.pyd",
    "_py3dnacalib.pyd",
    "dna.py",
    "dnacalib.py",
    "dnacalib.dll"
]

DNA_CALIB_LIN_FILES = [
    "_py3dna.so",
    "_py3dnacalib.so",
    "dna.py",
    "dnacalib.py",
    "libdnacalib.so.6"
]

DNA_CALIB_SUPPORTED = True
DNA_CALIB_NOT_SUPPORTED_REASON = ""

DNA_CALIB_FILES = None
DNA_CALIB_LIB_DIR = None


if sys.version_info.major != 3:
    DNA_CALIB_SUPPORTED = False
    DNA_CALIB_NOT_SUPPORTED_REASON = "Python 2 is not supported"

else:
    if sys.platform == "win32":
        DNA_CALIB_FILES = DNA_CALIB_WIN_FILES
        if sys.version_info.minor == 7:
            DNA_CALIB_LIB_DIR = DNA_CALIB_WIN_PY37_SUBFOLDER
        elif sys.version_info.minor >= 9:
            DNA_CALIB_LIB_DIR = DNA_CALIB_WIN_PY39_SUBFOLDER
    elif sys.platform == "linux":
        DNA_CALIB_FILES = DNA_CALIB_LIN_FILES
        if sys.version_info.minor == 7:
            DNA_CALIB_LIB_DIR = DNA_CALIB_LIN_PY37_SUBFOLDER
        elif sys.version_info.minor >= 9:
            DNA_CALIB_LIB_DIR = DNA_CALIB_LIN_PY39_SUBFOLDER
    else:
        DNA_CALIB_SUPPORTED = False
        DNA_CALIB_NOT_SUPPORTED_REASON = f"{sys.platform} is not supported. The only platform with a full support is Windows"



ADDON_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
DNA_CALIB_LOCAL_DIRECTORY = os.path.join(ADDON_DIRECTORY, "third_party/dnacalib")
AUTO_FIT_CONFIG_DIRECTORY = os.path.join(ADDON_DIRECTORY, "configs", "auto_fit")
