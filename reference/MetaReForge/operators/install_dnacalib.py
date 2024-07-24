import bpy
import shutil
import os
import subprocess
import requests
import zipfile
from ..globals import (
    ADDON_DIRECTORY,
    DNA_CALIB_URL,
    DNA_CALIB_LOCAL_DIRECTORY,
    DNA_CALIB_FILES,
    DNA_CALIB_LIB_DIR,
    DNA_CALIB_SUPPORTED,
    SWIG_WIN_DOWNLOAD_LINK,
    DNA_CALIB_DOWNLOAD_LINK,
    DNA_CALIB_VTX_COLOR_PATH
)

def safe_decode(byte_data):
    try:
        # First, try UTF-8
        return byte_data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Try a common Windows encoding next
            return byte_data.decode('cp1252')
        except Exception:
            # Use a different encoding or handle the failure
            return byte_data.decode('utf-8', errors='ignore')  # Ignore errors or replace

    
def get_subfolder(folder: str) -> str:
    subfolders = [
        name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))
    ]
    if len(subfolders) == 1:
        return os.path.join(folder, subfolders[0])
    else:
        raise Exception("Should be only one subfolder. Clean the buld folder")


def delete_file(file_path):
    """
    Delete a single file.
    """
    if os.path.exists(file_path) and os.path.isfile(file_path):
        os.remove(file_path)
        print(f"File {file_path} deleted successfully!")
    else:
        print(f"File {file_path} not found.")

def download_file(url, filename):
    r = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def extract_archive(archive_path, extract_to='.'):
    with zipfile.ZipFile(archive_path, 'r') as archive:
        archive.extractall(extract_to)


def fix_dnacalib_py(source_path: str, save_path: str) -> None:
    with open(source_path, 'r') as source_file:
        lines = source_file.readlines()

    with open(save_path, 'w') as dest_file:
        for line in lines:
            if line.strip().startswith("import dna") and not line.strip().startswith("from . import dna"):
                dest_file.write("if __package__ or '.' in __name__:\n")
                dest_file.write("    from . import dna\n")
                dest_file.write("else:\n")
                dest_file.write("    import dna\n")
            else:
                dest_file.write(line)


def copy_lib(dnacalib_root_dir: str, build_dir: str = None) -> None:
    # Create 'dnacalib' directory if it doesn't exist
    os.makedirs(DNA_CALIB_LOCAL_DIRECTORY, exist_ok=True)
    
    lib_dir = os.path.join(dnacalib_root_dir, DNA_CALIB_LIB_DIR)
    for filename in DNA_CALIB_FILES:
        if os.path.splitext(filename)[1] == ".py" or not build_dir:
            source_path = os.path.join(lib_dir, filename)
        else:
            source_path = os.path.join(os.path.join(build_dir, "py3bin"), filename)
        save_path = os.path.join(DNA_CALIB_LOCAL_DIRECTORY, filename)
        
        if filename == 'dnacalib.py':
            fix_dnacalib_py(source_path, save_path)
        else:
            shutil.copy2(source_path, save_path)

    # Copy vtx_color.py
    source_path = os.path.join(dnacalib_root_dir, DNA_CALIB_VTX_COLOR_PATH)
    save_path = os.path.join(DNA_CALIB_LOCAL_DIRECTORY, "vtx_color.py")
    shutil.copy2(source_path, save_path)

    
def run_command(command):
    print(f"Running command: {command}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    print(safe_decode(stdout))
    if stderr:
        print("Error:", safe_decode(stderr))


class MRF_OT_open_dnacalib_github(bpy.types.Operator):
    bl_idname = "meta_reforge.open_dnacalib_github"
    bl_label = "Visit official Epic Games repository"
    bl_description = "Visit official Epic Games repository"

    @classmethod
    def poll(cls, context):
        return DNA_CALIB_SUPPORTED

    def execute(self, context):
        bpy.ops.wm.url_open(url=DNA_CALIB_URL)  
        return {'FINISHED'}


class MRF_OT_build_dnacalib(bpy.types.Operator):
    bl_idname = "meta_reforge.build_dnacalib"
    bl_label = "Build dnacalib "
    bl_description = "Build DNA-Calibration"

    dnacalib_dir: bpy.props.StringProperty(name="DNA-Calibration Directory", subtype="DIR_PATH", default="")
    swig_dir: bpy.props.StringProperty(name="Swig Directory", subtype="DIR_PATH", default="")
    cmake_dir: bpy.props.StringProperty(name="CMake Directory", subtype="DIR_PATH", default="")
    python_version: bpy.props.StringProperty(name="Python Version", default="")
    toolset: bpy.props.StringProperty(name="Toolset Specification", default="")

    @classmethod
    def poll(cls, context):
        return DNA_CALIB_SUPPORTED

    def execute(self, context):
        # Update path
        original_path = os.environ["PATH"].split(os.pathsep)
        original_wd = os.getcwd()
        new_path = [
            os.path.join(self.cmake_dir, "bin"),
            self.swig_dir
        ]

        os.environ["PATH"] = os.pathsep.join(new_path + original_path)
        # Make a new directory named "build"
        build_dir = os.path.join(self.dnacalib_dir, "dnacalib", "build")

        # Define your build directory
        if os.path.exists(build_dir):
            # Remove the build directory to clear all the CMake cache and generated files
            print(f"Clearing build directory: {build_dir}")
            run_command(f'rmdir /S /Q {build_dir}')

        os.makedirs(build_dir, exist_ok=True)

        # Change the current working directory to "build"
        os.chdir(build_dir)

        python_version = f"-DPYTHON3_EXACT_VERSION={self.python_version}" if self.python_version else ""
        toolset = f"-T {self.toolset}" if self.toolset else ""
        run_command(f"cmake {toolset} {python_version} -DDNAC_LIBRARY_TYPE=SHARED ..")

        run_command("cmake --build . --config Release")

        copy_lib(self.dnacalib_dir, build_dir)
        
        os.environ["PATH"] = os.pathsep.join(original_path)
        os.chdir(original_wd)
        return {'FINISHED'}
    

class MRF_OT_copy_binaries(bpy.types.Operator):
    bl_idname = "meta_reforge.copy_dnacalib_binaries"
    bl_label = "Copy dnacalib Binaries"
    bl_description = "Copy necessary files for the addon"

    dnacalib_dir: bpy.props.StringProperty(
        name="DNA-Calibration Directory",
        subtype="DIR_PATH",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return DNA_CALIB_SUPPORTED and DNA_CALIB_FILES is not None and DNA_CALIB_LIB_DIR is not None

    def execute(self, context):     
        copy_lib(self.dnacalib_dir)        
        return {'FINISHED'}


class MRF_OT_get_dnacalib(bpy.types.Operator):
    bl_idname = "meta_reforge.get_dnacalib_library"
    bl_label = "Get DNA Calibration Library"
    bl_description = "Get DNA Calibration Library from the official Github repository"

    path: bpy.props.StringProperty(
        name="Path",
        subtype="DIR_PATH",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):     
        dnacalib_zip_path = os.path.join(self.path, "dnacalib.zip")
        dnacalib_path = os.path.join(self.path, 'dnacalib')

        print("Downloading MetaHuman-DNA-Calibration...")
        download_file(DNA_CALIB_DOWNLOAD_LINK, dnacalib_zip_path)
        print("Unzipping MetaHuman-DNA-Calibration...")
        extract_archive(dnacalib_zip_path, dnacalib_path)

        dnacalib_path = get_subfolder(dnacalib_path)
        addon_name = __package__.split(".")[0]
        addon_prefs = context.preferences.addons[addon_name].preferences
        addon_prefs.dnacalib_dir = dnacalib_path
        return {'FINISHED'} 


class MRF_OT_get_swig(bpy.types.Operator):
    bl_idname = "meta_reforge.get_swig"
    bl_label = "Get Swig"
    bl_description = "Get Swig from the official website"

    path: bpy.props.StringProperty(
        name="Path",
        subtype="DIR_PATH",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):     
        swig_zip_path = os.path.join(self.path, "swig.zip")
        swig_path = os.path.join(self.path, "swig")

        print("Downloading Swig...")
        download_file(SWIG_WIN_DOWNLOAD_LINK, swig_zip_path)
        print("Unzipping Swig...")
        extract_archive(swig_zip_path, swig_path)
        swig_path = get_subfolder(swig_path)

        addon_name = __package__.split(".")[0]
        addon_prefs = context.preferences.addons[addon_name].preferences
        addon_prefs.swig_dir = swig_path
        return {'FINISHED'}     


classes = [
    MRF_OT_open_dnacalib_github,
    MRF_OT_copy_binaries,
    MRF_OT_build_dnacalib,
    MRF_OT_get_dnacalib,
    MRF_OT_get_swig
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)    


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
