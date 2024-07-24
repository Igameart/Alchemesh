
import bpy
import time
from ..dna.rig_executor import get_executor


def update_control(self, context):
    t1 = time.time()
    rig_logic = get_executor()
    rig_logic.full_update(context.scene)
    t2 = time.time()
    print(f"Update time: {t2 - t1}")
    


class MRF_control(bpy.types.PropertyGroup):
    control_name: bpy.props.StringProperty(name="Control Name")
    index: bpy.props.IntProperty(name="Control Index")
    value: bpy.props.FloatProperty(name="Control Value", min=0, max=1) # , update=update_control)


class MRF_RigLogicProperty(bpy.types.PropertyGroup):
    raw_controls: bpy.props.CollectionProperty(type=MRF_control)
    raw_controls_index: bpy.props.IntProperty(default=0)
    control_rig: bpy.props.PointerProperty(type=bpy.types.Object, name="Control Rig")


classes = [
    MRF_control,
    MRF_RigLogicProperty
]


def register():
    for cl in classes:
        bpy.utils.register_class(cl)
    bpy.types.Scene.meta_reforge_rig_logic = bpy.props.PointerProperty(type=MRF_RigLogicProperty)

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
    del bpy.types.Scene.meta_reforge_rig_logic