from typing import Set, Union, List
import bpy
import os
from bpy.types import Context, Event
from ..enums import BodyPart
from ..utils.blender.keep_state import EditorState
from ..utils.blender.object import ensure_objects_visible


def get_available_name(name: str) -> str:
    if name not in bpy.data.objects:
        return name
    return get_next_available_name(name)


def get_next_available_name(name: str) -> str:
    i = 1
    while f"{name}.{str(i).zfill(3)}" in bpy.data.objects:
        i += 1

    return f"{name}.{str(i).zfill(3)}"


def export_lod_as_fbx(
        context: bpy.types.Context,
        armature: bpy.types.Object,
        meshes: List[bpy.types.Object],
        path: str
    ) -> None:
    config = context.scene.meta_reforge_config
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    if armature.name != "root":
        root_obj = bpy.data.objects.get("root")
        if root_obj:
            root_obj.name = get_next_available_name("root")
        armature.name = "root"
    output_dir = os.path.dirname(path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if not os.path.isdir(output_dir):
        raise Exception("Output path should be directory")

    bpy.context.view_layer.objects.active = meshes[0]
    for mesh in meshes:
        mesh.select_set(True)

    # Select the armature
    armature.select_set(True)
    
    # Export the selected objects (armature and single LOD) as FBX
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        axis_forward='Y',
        axis_up='Z',
        add_leaf_bones=False,
        mesh_smooth_type='FACE',
        use_tspace=True,
        use_mesh_modifiers=False
    )

    # bpy.data.objects.remove(joined_obj, do_unlink=True)
    # bpy.ops.outliner.orphans_purge(do_recursive=True)


class MRF_OT_export_fbx(bpy.types.Operator):
    """
    Export objects as FBX
    """
    bl_idname = "meta_reforge.export_fbx"
    bl_label = "Export FBX"
    bl_options = {'REGISTER', 'UNDO'}

    _steps = 100
    _current_step = 0
    _timer = None
    _actions = None
    _error = False
    _initial_state = None

    @classmethod
    def poll(cls, context: bpy.types.Context):
        config = context.scene.meta_reforge_config
        if (
            not config.fbx_export_head and 
            not config.fbx_export_body and 
            not config.fbx_export_clothes
        ):
            return False
        if config.fbx_export_head:
            if len(config.fbx_head_lods) == 0 or config.fbx_head_armature is None:
                return False 
        if config.fbx_export_body:
            if len(config.fbx_body_lods) == 0 or config.fbx_body_armature is None:
                return False
        return True

    def invoke(self, context: Context, event: Event) -> Union[Set[str], Set[int]]:
        try:
            config = context.scene.meta_reforge_config
            output_path = config.absolute_output_path
            self._initial_state = EditorState.capture_current_state()
            objects = list()
            context.window_manager.modal_handler_add(self)
            self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
            self._actions = list()
            if config.fbx_export_head:
                armature = config.fbx_head_armature
                objects.append(armature)
                for lod_index, lod_item in enumerate(config.fbx_head_lods):
                    meshes = [mesh_item.final_object for mesh_item in lod_item.mesh_items]
                    objects.extend(meshes)
                    filename = f"{config.export_name}_face_LOD{lod_index}.fbx"
                    path = os.path.join(output_path, filename)
                    self._actions.append((armature, meshes, path))

            if config.fbx_export_body:
                armature = config.fbx_body_armature
                objects.append(armature)
                for lod_index, lod_item in enumerate(config.fbx_body_lods):
                    meshes = [mesh_item.final_object for mesh_item in lod_item.mesh_items]
                    objects.extend(meshes)
                    filename = f"{config.export_name}_body_LOD{lod_index}.fbx"
                    path = os.path.join(output_path, filename)
                    self._actions.append((armature, meshes, path))

            if config.fbx_export_clothes:
                for cloth_item in config.cloth_items:
                    armature = cloth_item.armature
                    objects.append(armature)
                    for lod_index, mesh_item in enumerate(cloth_item.lod_items):
                        meshes = [mesh_item.final_object]
                        objects.extend(meshes)
                        filename = f"{cloth_item.item_name}_LOD{lod_index}.fbx"
                        path = os.path.join(output_path, filename)
                        self._actions.append((armature, meshes, path))
                        
            ensure_objects_visible(objects)
            self._current_step = 0
            config.view_group.export_running = True
            self._steps = len(self._actions)
            context.view_layer.update()
        except Exception as ex:
            if self._initial_state:
                self._initial_state.try_restore()
            self._error = True
        return {'RUNNING_MODAL'}

        
    def modal(self, context, event):
        if self._error:
            config.view_group.export_running = False
            if self._initial_state:
                self._initial_state.try_restore()
            return {"FINISHED"}
        if event.type == "TIMER":
            config = context.scene.meta_reforge_config
            if self._actions:
                armature, meshes, path = self._actions.pop(0)
                try:
                    export_lod_as_fbx(context, armature, meshes, path=path)
                except Exception as ex:
                    self.report({'ERROR'}, f"Export operation failed: {str(ex)}")
                self._current_step += 1
                config.view_group.export_progress = self._current_step / self._steps * 100
                context.area.tag_redraw()
            else:
                config.view_group.export_progress = 0.0
                context.area.tag_redraw()
                context.window_manager.event_timer_remove(self._timer)
                config.view_group.export_running = False
                if self._initial_state:
                    self._initial_state.try_restore()
                return {'FINISHED'}
        return {'PASS_THROUGH'}
    

def register():
    bpy.utils.register_class(MRF_OT_export_fbx)  


def unregister():
    bpy.utils.unregister_class(MRF_OT_export_fbx)  


if __name__ == '__main__':
    register()
