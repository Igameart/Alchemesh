from . import items, scene_config, view_group, control_rig


modules = [
    view_group,
    items,
    scene_config,
    control_rig
]

def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
