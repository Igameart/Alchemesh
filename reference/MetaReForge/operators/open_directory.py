import bpy
import sys
import os
import subprocess


def open_directory_in_file_explorer(directory_path: str):
    """
    Opens the specified directory in the system's default file explorer.

    :param directory_path: A string representing the path to the directory to open.
    """
    try:
        # Open the directory according to the operating system
        if sys.platform == "win32":  # Windows
            # Windows requires double backslashes in paths for the explorer command
            directory_path = os.path.normpath(directory_path)
            subprocess.run(['explorer', directory_path], check=True)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(['open', directory_path], check=True)
        elif sys.platform.startswith('linux'):  # Linux
            subprocess.run(['xdg-open', directory_path], check=True)
        else:
            print("Your operating system is not supported.")
    except Exception as e:
        print(f"An error occurred while trying to open the directory: {e}")


class MRF_OT_open_directory(bpy.types.Operator):
    bl_idname = "meta_reforge.open_directory"
    bl_label = "Open Directory"
    bl_description = "Open Directory"

    dir: bpy.props.StringProperty(name="Directory Path")

    def execute(self, context):
        open_directory_in_file_explorer(self.dir)
        return {'FINISHED'}  


classes = [
    MRF_OT_open_directory
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)    


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
