import bpy


class MRF_OT_setup_scene(bpy.types.Operator):
    bl_idname = "meta_reforge.setup_scene"
    bl_label = "Setup Scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 0.01
        scene.meta_reforge_config.export_running = False
        return {'FINISHED'}
    

def register():
    bpy.utils.register_class(MRF_OT_setup_scene)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_setup_scene)  


if __name__ == '__main__':
    register()
