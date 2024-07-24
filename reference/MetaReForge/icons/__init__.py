import bpy
import os
from bpy.utils import previews

# Global variable to store icons
custom_icons = None

icons = {
    "MRF_IMPORT": "import.png",
    "MRF_EXPORT": "export.png",
    "MRF_FEM_HEAD": "fem_head.png",
    "MRF_FEM_BODY": "fem_body.png",
    "MRF_EDIT_CHARACTER": "edit_character.png",
    "MRF_DNA": "dna.png",
    "MRF_SYNC": "sync.png",
    "MRF_LOGO": "logo.png",
    "MRF_VIEW": "view.png",
    "MRF_T_SHIRT": "t-shirt.png"
    
}

def load_icons():
    global custom_icons
    custom_icons = previews.new()

    # Path to your custom icon PNG file
    icons_dir = os.path.join(os.path.dirname(__file__))
    for k, v in icons.items():
        path = os.path.join(icons_dir, v)
        custom_icons.load(k, path, 'IMAGE')

def unload_icons():
    global custom_icons
    bpy.utils.previews.remove(custom_icons)


def get_icon(name: str) -> str:
    return custom_icons[name].icon_id
