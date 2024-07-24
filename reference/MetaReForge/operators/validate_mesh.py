import bpy
import bmesh


def PopupMessage(
        message: str = "",
        title: str = "Message Box",
        icon: str = 'INFO',
        align: bool = True
) -> None:

    def draw(self, context):
        col = self.layout.column(align=align)
        lines = message.split("\n")
        for line in lines:
            col.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def find_edges_with_more_than_two_faces(mesh_object: bpy.types.Object, select: bool = False) -> int:
    if mesh_object.type != 'MESH':
        raise ValueError("mesh_object is not a mesh")

    bm = bmesh.new()
    bm.from_mesh(mesh_object.data)

    # Counter for issues
    invalid_edges_count = 0
    if select:
        for edge in bm.edges:
            if len(edge.link_faces) > 2:
                invalid_edges_count += 1
                edge.select_set(True)
            else:
                edge.select_set(False)
    else:
        for edge in bm.edges:
            if len(edge.link_faces) > 2:
                invalid_edges_count += 1

    if select:
        bm.to_mesh(mesh_object.data)
    bm.free()
    return invalid_edges_count


def find_concave_faces(mesh_object: bpy.types.Object, select: bool = False) -> int:
    if mesh_object.type != 'MESH':
        raise ValueError("mesh_object is not a mesh")

    bm = bmesh.new()
    bm.from_mesh(mesh_object.data)

    # Counter for issues
    concave_faces_count = 0

    if select:
        for face in bm.faces:
            concave = False
            for loop in face.loops:
                if not loop.is_convex:
                    concave = True
                    break
            if concave:
                concave_faces_count += 1
                face.select_set(True)
            else:
                face.select_set(False)
    else:
        for face in bm.faces:
            for loop in face.loops:
                if not loop.is_convex:
                    concave_faces_count += 1
                    break


    if select:
        bm.to_mesh(mesh_object.data)
    bm.free()
    return concave_faces_count


class MRF_OT_validate_edit_meshes_edges(bpy.types.Operator):
    """
    Check and select edges in the edit meshes that are linked to more than two faces. 
    """
    bl_idname = "meta_reforge.validate_edit_meshes_edges"
    bl_label = "Check Edges"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        config = context.scene.meta_reforge_config
        warnings = []
        for edit_mesh in config.edit_meshes:
            invalid_edges = find_edges_with_more_than_two_faces(edit_mesh.final_object, True)
            if invalid_edges:
                warnings.append(f"{edit_mesh.final_object.name}: {invalid_edges}")
        if warnings:
            PopupMessage(title="Invalid edges are found", message="\n".join(warnings), icon="ERROR")
        else:
            PopupMessage(title="Invalid edges are not found", icon="CHECKMARK")
        return {'FINISHED'}
    

class MRF_OT_validate_edit_meshes_faces(bpy.types.Operator):
    """
    Check and select concave faces in the specified edit meshes.
    """
    bl_idname = "meta_reforge.validate_edit_meshes_faces"
    bl_label = "Check Concave"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        config = context.scene.meta_reforge_config
        warnings = []
        for edit_mesh in config.edit_meshes:
            invalid_faces = find_concave_faces(edit_mesh.final_object, True)
            if invalid_faces:
                warnings.append(f"{edit_mesh.final_object.name}: {invalid_faces}")
            
        if warnings:
            PopupMessage(title="Invalid faces are found", message="\n".join(warnings), icon="ERROR")
        else:
            PopupMessage(title="Invalid faces are not found", icon="CHECKMARK")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MRF_OT_validate_edit_meshes_edges)
    bpy.utils.register_class(MRF_OT_validate_edit_meshes_faces)


def unregister():
    bpy.utils.unregister_class(MRF_OT_validate_edit_meshes_edges)
    bpy.utils.unregister_class(MRF_OT_validate_edit_meshes_faces)
