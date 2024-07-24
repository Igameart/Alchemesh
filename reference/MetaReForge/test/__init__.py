from . import props, textures, profiler


modules = [props, profiler, textures]

def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
