import os
import bpy
import sys
from typing import List
from ..operators.install_dnacalib import (
    MRF_OT_open_dnacalib_github,
    MRF_OT_copy_binaries,
    MRF_OT_build_dnacalib,
    MRF_OT_get_dnacalib,
    MRF_OT_get_swig
)
from ..operators.open_directory import (
    MRF_OT_open_directory
)
from ..globals import (
    ADDON_DIRECTORY,
    DNA_CALIB_SUPPORTED,
    DNA_CALIB_NOT_SUPPORTED_REASON,
    DNA_CALIB_LOCAL_DIRECTORY,
    DNA_CALIB_FILES
)
from ..dna.libimport import DNA_IMPORT_EX
from ..globals import PYTHON_VERSIONS

# Default CMake path
_cmake_path = ""

# Check the default installation path first
default_cmake_path = os.path.join(os.environ.get('ProgramFiles', ''), 'CMake')
if os.path.isdir(default_cmake_path):
    _cmake_path = default_cmake_path
else:
    # Versions of Visual Studio to check
    vs_versions = ["2022", "2019", "2017", "2015"]

    # Base path for Visual Studio installations
    vs_base_path = os.path.join(os.environ.get('ProgramFiles', ''), 'Microsoft Visual Studio')

    # Loop through each version to check for CMake
    for version in vs_versions:
        cmake_path = os.path.join(vs_base_path, version, 'Community', 'Common7', 'IDE', 'CommonExtensions', 'Microsoft', 'CMake', 'CMake')
        if os.path.isdir(cmake_path):
            _cmake_path = cmake_path
            break

# Output the found path or indicate it wasn't found
if _cmake_path:
    print(f"CMake found at: {_cmake_path}")
else:
    print("CMake not found.")


def check_dnacalib_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    
    if not os.path.exists(os.path.join(path, "README.md")):
        return False
    
    return True

def check_cmake_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    
    if not os.path.exists(os.path.join(path, "bin", "cmake.exe")):
        return False
    return True

def check_swig_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    
    if not os.path.exists(os.path.join(path, "swig.exe")):
        return False
    return True


def check_files(directory: str, files_list: List[str]):
    """Check if all files in the list are present in the given directory."""
    for filename in files_list:
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            return False
    return True


_none_python = (
    "NONE",
    "Not specified",
    "Not specified, parameter -DPYTHON3_EXACT_VERSION will not be set",
    0
)
_python_versions = [_none_python] + [(v, v, f"Python {v}", i+1) for i, v in enumerate(PYTHON_VERSIONS)]

def get_python_default_version():
    python_best_match = None
    for v in PYTHON_VERSIONS:
        v_split = v.split(".")
        if len(v_split) != 3:
            continue
        major, minor, micro = int(v_split[0]), int(v_split[1]), int(v_split[2])
        if sys.version_info.major == major and sys.version_info.minor == minor:
            if not python_best_match:
                python_best_match = v
            else:
                best_micro = int(v.split(".")[2])
                if abs(micro - sys.version_info.micro) < abs(best_micro - sys.version_info.micro):
                    python_best_match = v
    return python_best_match if python_best_match else "NONE"

_default_python_version = get_python_default_version()
        

_toolsets = [
    ("NONE", "Not specified", "Not specified, parameter -T will not be set", 0),
    ("v142", "v142", "v142", 1),
    ("v143", "v143", "v143", 2)
]

class MRF_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__.split(".")[0]  # this refers to the name of the current module

    dnacalib_dir: bpy.props.StringProperty(
        name="DNA-Calibration Directory",
        subtype="DIR_PATH",
        default=""
    )

    swig_dir: bpy.props.StringProperty(
        name="Swig Directory",
        subtype="DIR_PATH",
        default=""
    )

    cmake_dir: bpy.props.StringProperty(
        name="CMake Directory",
        subtype="DIR_PATH",

        default=_cmake_path
    )

    python_version: bpy.props.EnumProperty(
        name="Python Version",
        description="Python version to be specified for CMake as parameter "
                    "\"-DPYTHON3_EXACT_VERSION <PYTHON_VERSION>\"",
        items=_python_versions,
        default=_default_python_version
    )
    
    toolset: bpy.props.EnumProperty(
        name="VSC Toolset",
        description="VSC Toolset to be specified for CMake as parameter "
                    "\"-T <TOOLSET_VERSION>\"",
        items=_toolsets,
        default="v143"
    )

    def draw(self, context):
        layout = self.layout
        if not DNA_CALIB_SUPPORTED:
            row = layout.row()
            col = row.column()
            col.label(icon="ERROR", text="")
            col = row.column(align=True)
            col.label(text="DNA Calibration library is not supported on your system.")
            col.label(text="The addon functionality is limited")
            col.label(text=f"REASON: {DNA_CALIB_NOT_SUPPORTED_REASON}")
            return
        
        lib_files_ok = check_files(DNA_CALIB_LOCAL_DIRECTORY, DNA_CALIB_FILES)
        vtx_file_ok = check_files(DNA_CALIB_LOCAL_DIRECTORY, ["vtx_color.py"])
        row = layout.row()
        row.label(text="MetaHuman-DNA-Calibration", icon="RNA")
        row.operator(MRF_OT_open_dnacalib_github.bl_idname, icon="URL")
        
        # DEPENDENCIES CHECK
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Dependencies check:", icon="LINKED")
        # Check if the directory exists
        if os.path.exists(DNA_CALIB_LOCAL_DIRECTORY):
            props = row.operator(MRF_OT_open_directory.bl_idname, text="Reveal in File Exlorer")
            props.dir = DNA_CALIB_LOCAL_DIRECTORY
        col = box.column(align=True)
        if not vtx_file_ok:
            col.label(text="vtx_color.py is Missing", icon="ERROR")
        if sys.version_info.minor in [7, 9]:
            if lib_files_ok:
                col.label(text="Library files are found", icon="CHECKMARK")
                if DNA_IMPORT_EX is None:
                    col.label(text="Library files are linked", icon="CHECKMARK")
                else:
                    col.label(text="Library files are NOT LINKED", icon="ERROR")
                    col.label(text="")
                    col.label(text="The addon functionality is limited")
            else:
                col.label(text="Library files are missing", icon='ERROR')
                col.label(text="Library files are NOT LINKED", icon="ERROR")
                col.label(text="")
                col.label(text="The addon functionality is limited")
                col.label(text="Library files can be copied from the Maya plugin in the official repository folder")
            
        else:            
            if lib_files_ok:
                col.label(text="Library files are found", icon="CHECKMARK")
                if DNA_IMPORT_EX is None:
                    col.label(text="Library files are linked", icon="CHECKMARK")
                else:
                    col.label(text="Library files are NOT LINKED", icon="ERROR")
                    col.label(text="")
                    col.label(text="The addon functionality is limited")
                col.label(text="Сlear addon/third_party/dnacalib directory if you want to build/rebuild")
            else:
                py_version = ".".join(map(str, sys.version_info))
                col.label(text="Library files are missing", icon='ERROR')
                col.label(text="Library files are NOT LINKED", icon="ERROR")
                col.label(text="The addon functionality is limited")
                col.label(text=f"Building DNA-Calibration is required to get all functionality.")

        # BUILD/INSTALL SETTIONGS
        box = layout.box()
        if sys.version_info.minor in [7, 9]:
            box.label(text="Installation Settings:", icon="MOD_BUILD")
            row = box.row(align=True)
            row.label(icon="CHECKMARK" if check_dnacalib_dir(self.dnacalib_dir) else "ERROR")
            row.prop(self, "dnacalib_dir", text="DNA Calibration")
            props = row.operator(MRF_OT_get_dnacalib.bl_idname, icon="IMPORT", text="")
            props.path = self.dnacalib_dir
            props = box.operator(MRF_OT_copy_binaries.bl_idname, text="Copy Binaries from Maya plugin")
            props.dnacalib_dir = self.dnacalib_dir
        else:
            box.label(text="Build Settings:", icon="MOD_BUILD")
            
            col = box.column(align=True)
            row = col.row(align=True)
            row.label(icon="CHECKMARK" if check_cmake_dir(self.cmake_dir) else "ERROR")
            row.prop(self, "cmake_dir", text="CMake")

            row = col.row(align=True)
            row.label(icon="CHECKMARK" if check_swig_dir(self.swig_dir) else "ERROR")
            row.prop(self, "swig_dir", text="Swig")
            props = row.operator(MRF_OT_get_swig.bl_idname, icon="IMPORT", text="")
            props.path = self.swig_dir

            row = col.row(align=True)
            row.label(icon="CHECKMARK" if check_dnacalib_dir(self.dnacalib_dir) else "ERROR")
            row.prop(self, "dnacalib_dir", text="DNA Calibration")
            props = row.operator(MRF_OT_get_dnacalib.bl_idname, icon="IMPORT", text="")
            props.path = self.dnacalib_dir

            col = box.column(align=True)
            row = col.row()
            row.label(text="Python version")
            row.prop(self, "python_version", text="")
            row.label(text="VSC Toolset")
            row.prop(self, "toolset", text="")

            col = box.column(align=True)
            if not self.dnacalib_dir:
                col.label(text="DNA Calibration Directory is not valid")
            elif not self.cmake_dir:
                col.label(text="CMake Directory is not valid")
            elif not self.swig_dir:
                col.label(text="Swig Directory is not valid")
            else:
                props = col.operator(MRF_OT_build_dnacalib.bl_idname, text="Build DNA-Calibration")
                props.dnacalib_dir = self.dnacalib_dir
                props.cmake_dir = self.cmake_dir
                props.swig_dir = self.swig_dir
                props.python_version = self.python_version if self.python_version != "NONE" else ""
                props.toolset = self.toolset if self.toolset != "NONE" else ""
        

def register():
    bpy.utils.register_class(MRF_AddonPreferences)


def unregister():
    bpy.utils.unregister_class(MRF_AddonPreferences)
