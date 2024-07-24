import bpy


class MRF_OT_scan_nonzero_shape_keys(bpy.types.Operator):
    """Operator to scan for nonzero shape keys in specified objects"""
    bl_idname = "meta_reforge.scan_nonzero_shape_keys"
    bl_label = "Scan Nonzero Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Access the property where the objects are stored
        edit_meshes = context.scene.meta_reforge_config.edit_meshes

        # Clear existing entries in the shape_keys property
        nonzero_shape_keys = context.scene.meta_reforge_config.nonzero_shape_keys
        nonzero_shape_keys.clear()

        # Iterate through each object in edit_meshes
        for item in edit_meshes:
            obj = item.final_object
            if not obj.data.shape_keys:
                continue
            key_blocks = obj.data.shape_keys.key_blocks

            # Iterate through each shape key
            for sk in key_blocks:
                # Check if the shape key's value is nonzero
                if sk.value >= 0.001:
                    # Add a new entry to the nonzero_shape_keys property
                    new_item = nonzero_shape_keys.add()
                    new_item.object = obj
                    new_item.shape_key_name = sk.name

        return {'FINISHED'}
    

class MRF_OT_edit_shape_key(bpy.types.Operator):
    """
    Enables shape key editing in edit or sculpt mode
    """
    bl_idname = "meta_reforge.edit_shape_key"
    bl_label = "Edit Shape Key"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: bpy.props.StringProperty(options={"HIDDEN"})
    shape_key_name: bpy.props.StringProperty(options={"HIDDEN"})
    mode: bpy.props.StringProperty(options={"HIDDEN"}, default="EDIT")

    def execute(self, context):
        # Select the specified object
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
            return {'CANCELLED'}
        
        # Switch to object mode
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        obj.select_set(True)

        # Check if the object has shape keys
        if obj.data.shape_keys and self.shape_key_name in obj.data.shape_keys.key_blocks:
            # Activate the specified shape key
            obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(self.shape_key_name)
        else:
            self.report({'ERROR'}, f"Shape key '{self.shape_key_name}' not found in object '{self.object_name}'")
            return {'CANCELLED'}

        if self.mode == "SCULPT":
            # Enter mesh sculpt mode
            bpy.ops.object.mode_set(mode='SCULPT')
        else:
            # Enter mesh edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            obj.use_shape_key_edit_mode = True
            # Enable modifiers edit mode preview for all modifiers of the object
            for modifier in obj.modifiers:
                modifier.show_in_editmode = True
                modifier.show_on_cage = True

        return {'FINISHED'}
    

class MRF_OT_check_shape_key(bpy.types.Operator):
    """
    Enadles the shape key transfer in the syncronization list.
    """
    bl_idname = "meta_reforge.check_shape_key"
    bl_label = "Edit Shape Key"
    bl_options = {'REGISTER', 'UNDO'}

    shape_key_name: bpy.props.StringProperty(options={"HIDDEN"})

    def execute(self, context):
        config = context.scene.meta_reforge_config
        config.sync_enable_shape_keys = True
        for sk_item in config.sync_shape_keys_to_transfer:
            if sk_item.shape_key_name == self.shape_key_name:
                sk_item.checked = True
                return {'FINISHED'}

        item = config.sync_shape_keys_to_transfer.add()
        item.shape_key_name = self.shape_key_name
        item.checked = True
        return {'FINISHED'}
        


classes = [MRF_OT_scan_nonzero_shape_keys, MRF_OT_edit_shape_key, MRF_OT_check_shape_key]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
