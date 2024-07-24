bl_info = {
    "name" : "MetaReForge",
    "author" : "Mykyta Petrenko (Squeezy Pixels)",
    "description" : "",
    "blender" : (3, 3, 0),
    "version" : (1, 1, 0, 4),
    "location" : "",
    "warning": "",
    "wiki_url": "https://mykytapetrenko.github.io/MetaReForge-Docs/",
    "category" : "Mesh"
}
from . import operators
from . import props
from . import ui
from . import test
from . import icons
import bpy


modules = [
    props,
    ui,
    operators,
    test
]

def register():
    icons.load_icons()
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
    icons.unload_icons()


if __name__ == '__main__':
    register()
