import bpy


# Function to create texture setup for normal maps
def setup_normal_map(nodes, links, image_name, location):
    x_location, y_location = location
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = bpy.data.images[image_name]
    tex_node.location = location
    sep_node = nodes.new('ShaderNodeSeparateRGB')

    sep_node.location = (x_location + 300, y_location - 100)
    links.new(tex_node.outputs['Color'], sep_node.inputs['Image'])

    # Inverting the green channel
    inv_node = nodes.new('ShaderNodeInvert')
    inv_node.location = (x_location + 500, y_location - 100)
    links.new(sep_node.outputs['G'], inv_node.inputs['Color'])

    comb_node = nodes.new('ShaderNodeCombineRGB')
    comb_node.location = (x_location + 700, y_location - 100)
    links.new(sep_node.outputs['R'], comb_node.inputs['R'])
    links.new(inv_node.outputs['Color'], comb_node.inputs['G'])
    links.new(sep_node.outputs['B'], comb_node.inputs['B'])

    norm_node = nodes.new('ShaderNodeNormalMap')
    norm_node.location = (location[0] + 900, y_location - 100)
    links.new(comb_node.outputs['Image'], norm_node.inputs['Color'])

    return norm_node.outputs['Normal']

class MRF_TextureOperator(bpy.types.Operator):
    bl_idname = "object.my_texture_operator"
    bl_label = "My Texture Operator"

    def execute(self, context):
        config = context.scene.mrf_texture_properties

        # Set render engine to Cycles
        bpy.context.scene.render.engine = 'CYCLES'

        # Create a new plane for baking
        bpy.ops.mesh.primitive_plane_add()
        bake_plane = bpy.context.active_object
        bake_plane.name = "BakePlane"

        # Create a new material with nodes
        mat = bpy.data.materials.new(name="BakeMaterial")
        mat.use_nodes = True
        bake_plane.data.materials.append(mat)

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Set up nodes for each texture
        normal_basis_neutral = setup_normal_map(nodes, links, config.basis_neutral.name, (-1000, 300))
        normal_basis_expression = setup_normal_map(nodes, links, config.basis_expression.name, (-1000, 0))
        normal_target_neutral = setup_normal_map(nodes, links, config.target_neutral.name, (-1000, -300))

        # Vector math for dot product, cross product, and rotation
        dot_node = nodes.new('ShaderNodeVectorMath')
        dot_node.operation = 'DOT_PRODUCT'
        dot_node.location = 300, 200
        links.new(normal_basis_neutral, dot_node.inputs[0])
        links.new(normal_basis_expression, dot_node.inputs[1])

        cross_node = nodes.new('ShaderNodeVectorMath')
        cross_node.operation = 'CROSS_PRODUCT'
        cross_node.location = 300, -100
        links.new(normal_basis_neutral, cross_node.inputs[0])
        links.new(normal_basis_expression, cross_node.inputs[1])

        # Calculate rotation axis and angle
        arccos_node = nodes.new('ShaderNodeMath')
        arccos_node.operation = 'ARCCOSINE'
        arccos_node.location = 500, 200
        links.new(dot_node.outputs[1], arccos_node.inputs[0]) # Linking dot product to arccosine

        normalize_node = nodes.new('ShaderNodeVectorMath')
        normalize_node.operation = 'NORMALIZE'
        normalize_node.location = 500, -100
        links.new(cross_node.outputs[0], normalize_node.inputs[0]) # Linking cross product to normalize

        # Vector Rotate node to rotate target_neutral normal vector
        rotate_node = nodes.new('ShaderNodeVectorRotate')
        rotate_node.inputs['Center'].default_value = (0.0, 0.0, 0.0)  # Adjust as needed
        rotate_node.location = 900, -300
        links.new(normal_target_neutral, rotate_node.inputs['Vector'])
        links.new(normalize_node.outputs[0], rotate_node.inputs['Axis'])
        links.new(arccos_node.outputs[0], rotate_node.inputs['Angle'])        

        # Output node (Emission node connected to Material Output is typically used for baking)
        emission_node = nodes.new('ShaderNodeEmission')
        emission_node.location = 1600, 0
        links.new(rotate_node.outputs['Vector'], emission_node.inputs['Color'])

        output_node = nodes.new('ShaderNodeOutputMaterial')
        output_node.location = 1800, 0
        links.new(emission_node.outputs[0], output_node.inputs[0])

        # Set up and perform baking
        bpy.context.view_layer.objects.active = bake_plane
        # bpy.ops.object.bake(type='EMIT')

        # Save the baked image (additional code needed to handle saving)

        return {'FINISHED'}

def register():
    bpy.utils.register_class(MRF_TextureOperator)

def unregister():
    bpy.utils.unregister_class(MRF_TextureOperator)

if __name__ == "__main__":
    register()

    # Test the operator
    bpy.ops.object.my_texture_operator()
