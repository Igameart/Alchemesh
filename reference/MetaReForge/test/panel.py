import bpy
from ..test.textures import MRF_TextureOperator
from ..test.profiler import MRF_ProfilerOperator


class MRF_PT_test_panel(bpy.types.Panel):
    """
    Addon main menu (N-Panel)
    """
    bl_label = 'MetaReForge.Test'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MRF"
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        layout.operator(MRF_ProfilerOperator.bl_idname)
        config = context.scene.mrf_texture_properties
        layout.prop(config, "basis_neutral")
        layout.prop(config, "basis_expression")
        layout.prop(config, "target_neutral")
        layout.operator(MRF_TextureOperator.bl_idname)
        

classes = [
    MRF_PT_test_panel
]   
            

def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()
