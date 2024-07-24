import bpy


LIST_ACTIONS = [
    ('REMOVE', 'Remove', '', 0),
    ('ADD', 'Add', '', 1),
    ('MOVE_UP', 'Move Up', '', 2),
    ('MOVE_DOWN', 'Move Down', '', 3),
    ('CLEAR', 'Clear', '', 4)
]


class MRF_OT_list_action(bpy.types.Operator):
    bl_idname = "meta_reforge.list_action"
    bl_label = "List Action"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(items=LIST_ACTIONS, options={'HIDDEN'})
    propname: bpy.props.StringProperty(options={'HIDDEN'})
    active_propname: bpy.props.StringProperty(options={'HIDDEN'})
    data_propname: bpy.props.StringProperty(options={'HIDDEN'})
    
    def execute(self, context):
        config = context.scene.meta_reforge_config
        if self.data_propname:
            data_ptr = eval(f"config.{self.data_propname}")
        else:
            data_ptr = config
        
        collection = getattr(data_ptr, self.propname, None)
        if collection is None:
            raise ValueError("TODO")
        
        active_index = getattr(data_ptr, self.active_propname, None)
        max_idx = len(collection) - 1
        if active_index is None:
            raise ValueError("TODO")

        if self.action == 'ADD':
            collection.add()
        elif self.action == 'REMOVE':
            collection.remove(active_index)
        elif self.action == 'MOVE_UP':
            if active_index > 0:
                collection.move(active_index, active_index - 1)
                setattr(data_ptr, self.active_propname, active_index - 1)
        elif self.action == 'MOVE_DOWN':
            if active_index < max_idx:
                collection.move(active_index, active_index + 1)
                setattr(data_ptr, self.active_propname, active_index + 1)
        elif self.action == 'CLEAR':
            pass
        else:
            raise ValueError("Invalid list action")
            
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MRF_OT_list_action)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_list_action)
