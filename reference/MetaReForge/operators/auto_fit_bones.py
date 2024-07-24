import bpy
import json

from ..utils.blender.unsorted import add_armature_modifier
from ..utils.blender.armature import set_pose


def select_bones_by_names(armature: bpy.types.Armature, bone_list: list) -> None:
    edit_bones = armature.edit_bones
    for bone in edit_bones:
        bone.select = bone.name in bone_list  # Corrected condition
        

class MRF_OT_auto_fit_bones(bpy.types.Operator):
    bl_idname = "meta_reforge.auto_fit_bones"
    bl_label = "Fit Bones"
    bl_description = "Automatically fits bones"
    bl_options = {'REGISTER', 'UNDO'}

    config_path: bpy.props.StringProperty(name="Bones Config", subtype="FILE_PATH", options={"HIDDEN"})
    force_rebind: bpy.props.BoolProperty(name="Force Rebind", default=False, options={"HIDDEN"})

    def execute(self, context):
        config = context.scene.meta_reforge_config
        armature = context.active_object
        # Read json config
        try:
            with open(bpy.path.abspath(self.config_path), 'r') as f:
                fit_config = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read bones config: {str(e)}")
            return {'CANCELLED'}

        basis_armature = config.edit_armature.basis_object

        for action in fit_config:
            action_name = action.get("NAME", "untitled")
            method = action.get("METHOD")
            edit_id = action.get("EDIT_ID", None)
            bone_names = action.get("BONES", list())
            preserve_orientation = action.get("PRESERVE_ORIENTATION", True)
            if bone_names == "ALL":
                bone_names = [bone.name for bone in armature.data.bones]
            
            if not bone_names:
                print("Warning: The bone list is empty")
                continue
            
            select_bones_by_names(armature.data, bone_names)

            if method == "INTERPOLATE_BONES":
                origin_bone = action.get("ORIGIN", None)
                end_bone = action.get("END", None)
                bpy.ops.meta_reforge.interpolate_bones(
                    origin_bone=origin_bone,
                    end_bone=end_bone,
                    reference_armature=basis_armature.name
                )
            if edit_id: 
                objects = [(mi.basis_object, mi.final_object) for mi in config.edit_meshes if mi.edit_id == edit_id]
                if len(objects) == 0:
                    print(f"WARNING: Cannot get objects with edit_id=\"{edit_id}\"")
                    continue
                elif len(objects) > 1:
                    print(
                        f"WARNING: Too many edit objects with the same edit_id(\"{edit_id}\"). "
                        "Only the first one will be processed"
                    )
                basis_object, final_object = objects[0]
                if method == "GEOMETRY_CENTER":
                    bpy.ops.meta_reforge.fit_geo_center(object_name=final_object.name)
                elif method == "SURFACE_DEFORM" or "MESH_DEFORM":
                    force_rebind = action.get("FORCE_REBIND", False)
                    proxy_name = f"{action_name}_PROXY"
                    proxy = bpy.data.objects.get(proxy_name)
                    if not proxy or force_rebind or self.force_rebind:
                        bind_pose = action.get("BIND_POSE", None)
                        if bind_pose:
                            # Make sure armature deform modifier exists
                            arm_mod = None
                            for mod in basis_object.modifiers:
                                if mod.type == "ARMATURE" and not arm_mod:
                                    arm_mod = mod
                                    if arm_mod.object.name != basis_armature.name:
                                        arm_mod.object = basis_armature
                                else:
                                    basis_object.modifiers.remove(mod)

                            if not arm_mod:
                                add_armature_modifier(basis_object, basis_armature)
                                    
                            set_pose(basis_armature, bind_pose, reset=False)
                            context.view_layer.update()
                    
                        if method == "SURFACE_DEFORM":
                            bpy.ops.meta_reforge.init_surface_deform_proxy(
                                falloff=config.surface_deform_falloff,
                                proxy_name=proxy_name,
                                basis_mesh_name=basis_object.name,
                                basis_armature_name=basis_armature.name
                            )
                        else:
                            bpy.ops.meta_reforge.init_mesh_deform_proxy(
                            precision=config.mesh_deform_precision,
                            proxy_name=proxy_name,
                            basis_mesh_name=basis_object.name,
                            basis_armature_name=basis_armature.name
                        )

                        context.view_layer.update()
                        if bind_pose:
                            set_pose(basis_armature, bind_pose, reset=True)
                            context.view_layer.update()
                        
                    bpy.ops.meta_reforge.fit_bones(
                        proxy_name=proxy_name,
                        basis_mesh_name=basis_object.name,
                        final_mesh_name=final_object.name,
                        basis_armature_name=basis_armature.name,
                        lock_rotation=preserve_orientation
                    )

        return {'FINISHED'}
    

classes = [MRF_OT_auto_fit_bones]
    

def register():
    for c in classes:
        bpy.utils.register_class(c)   


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)  


if __name__ == '__main__':
    register()
