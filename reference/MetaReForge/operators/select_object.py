import bpy


class MRF_OT_select_object(bpy.types.Operator):
    bl_idname = "meta_reforge.select_object"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: bpy.props.StringProperty(name="Object Name")

    def execute(self, context: bpy.types.Context):
        try:
            obj = bpy.data.objects[self.object_name]
            obj.select_set(True)
            context.view_layer.objects.active = obj
            return {'FINISHED'}
        except Exception as ex:
            self.report({"ERROR"}, f"Cannot select: {str(ex)}")
            return {'CANCELLED'}

        
def register():
    bpy.utils.register_class(MRF_OT_select_object)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_select_object)  


if __name__ == '__main__':
    register()