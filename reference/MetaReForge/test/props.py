import bpy


class MRF_TextureProperties(bpy.types.PropertyGroup):

    basis_neutral: bpy.props.PointerProperty(
        name="Basis Neutral Texture",
        type=bpy.types.Image
    )
    basis_expression: bpy.props.PointerProperty(
        name="Basis Expression Texture",
        type=bpy.types.Image
    )
    target_neutral: bpy.props.PointerProperty(
        name="Target Neutral",
        type=bpy.types.Image
    )


classes = [
    MRF_TextureProperties
]


def register():
    for cl in classes:
        bpy.utils.register_class(cl)
    bpy.types.Scene.mrf_texture_properties = bpy.props.PointerProperty(type=MRF_TextureProperties)

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)
    del bpy.types.Scene.mrf_texture_properties
