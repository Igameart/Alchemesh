import bpy
import numpy as np
import os, shutil
import sys
import subprocess
import importlib
import imp
import bmesh
import textwrap
import matplotlib.pyplot as plt
from collections import namedtuple
from mathutils import Vector
from sys import platform
import ctypes
import mathutils
import math
from bpy_extras import object_utils
from mathutils import Vector

current_dir = os.path.dirname(os.path.abspath(__file__))
dnacalib_dir = os.path.join(current_dir, 'dnacalib')
dll_path = os.path.join(dnacalib_dir, "dnacalib.dll")

sys.path.append(dnacalib_dir)

try:
	from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, JSONStreamWriter
	import dna
	import dnacalib as dnac
except ImportError as e:
	print(f"Failed to import from dna: {e}")
	
# Load the DLL
try:
	dna_dll = ctypes.CDLL(dll_path)
except OSError as e:
	print(f"Error loading DLL: {e}")
	dna_dll = None
	
def update_progress(job_title, progress):
	length = 60
	block = int(round(length * progress))
	msg = f"\r{job_title}: [{'#' * block + '-' * (length - block)}] {round(progress * 100, 2)}%"
	if progress >= 1:
		msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

def unload_dll():
	global dna_dll
	if dna_dll:
		del dna_dll
		dna_dll = None
		print("DLL unloaded successfully.")

def load_dna(path):
	stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
	reader = BinaryStreamReader(stream, DataLayer_All)
	reader.read()
	if not Status.isOk():
		status = Status.get()
		raise RuntimeError(f"Error loading DNA: {status.message}")
	return reader


def save_dna(reader, path):
	stream = FileStream(path, FileStream.AccessMode_Write, FileStream.OpenMode_Binary)
	writer = JSONStreamWriter(stream)
	writer.setFrom(reader)
	writer.write()

	if not Status.isOk():
		status = Status.get()
		raise RuntimeError(f"Error saving DNA: {status.message}")
		
def create_json_dna(input_path, output_path):
	dna_reader = load_dna(input_path)
	save_dna(dna_reader, output_path)

def rebind_armature(source_dna,output_dna,morphed_armature):
	# Load the DNA data
	dna_data = load_dna(source_dna)  # This function needs to be defined to load the DNA

	joint_count = dna_data.getJointCount()

	translations = []
	rotations = []

	for i in range(joint_count):
		joint_name = dna_data.getJointName(i)
		print(f"Calibrating Joint: {joint_name}")

		# Find the corresponding bone in the morphed armature
		# bone = morphed_armature.pose.bones.get(joint_name)
		# if bone:
			# # Get the translation and rotation in parent space
			# translation = bone.location
			# rotation = bone.rotation_euler

			# translations.append([translation.x, translation.y, translation.z])
			# rotations.append([rotation.x, rotation.y, rotation.z])

			# # Create and run translate and rotate commands
			# translate_cmd = dnac.TranslateCommand()
			# translate_cmd.setTranslation([translation.x, translation.y, translation.z])
			# translate_cmd.run(dna_data)

			# rotate_cmd = dnac.RotateCommand()
			# rotate_cmd.setRotation([rotation.x, rotation.y, rotation.z])
			# rotate_cmd.setOrigin([translation.x, translation.y, translation.z])
			# rotate_cmd.run(dna_data)

	# # Set neutral joint translations and rotations
	# set_translations_cmd = dnac.SetNeutralJointTranslationsCommand(translations)
	# set_translations_cmd.run(dna_data)

	# set_rotations_cmd = dnac.SetNeutralJointRotationsCommand(rotations)
	# set_rotations_cmd.run(dna_data)

	# # Save the modified DNA data to the output file
	# save_dna(output_dna, dna_data)  # This function needs to be defined to save the DNA
	
def create_armatures_from_dna(source_dna):
	# Load the DNA data
	dna_data = load_dna(source_dna)  # Function to load DNA data
	lod_count = dna_data.getLODCount()
	
	# Load all LODs
	lods = []
	for lod_index in range(lod_count):  # Assuming there are 6 LODs (0 to 5)
		joint_indices = dna_data.getJointIndicesForLOD(lod_index)
		joint_names = [dna_data.getJointName(i) for i in joint_indices]
		joint_count = len(joint_names)

		# Create a new armature for this LOD
		armature = bpy.data.armatures.new(name=f"MH_Armature_Lod{lod_index}")
		armature_obj = bpy.data.objects.new(f"MH_Armature_Obj_Lod{lod_index}", armature)

		# Create or get the collection for this LOD
		collection_name = f"MH_Lod_{lod_index}"
		if collection_name not in bpy.data.collections:
			collection = bpy.data.collections.new(collection_name)
			bpy.context.scene.collection.children.link(collection)
		else:
			collection = bpy.data.collections[collection_name]

		# Link the object to the appropriate collection
		bpy.ops.object.select_all(action="DESELECT")
		collection.objects.link(armature_obj)
		bpy.context.view_layer.objects.active = armature_obj
		bpy.ops.object.mode_set(mode='EDIT')

		# Create bones
		bones = {}
		for i in range(joint_count):
			joint_name = joint_names[i]
			joint_index = joint_indices[i]
			joint_translation = (
				dna_data.getNeutralJointTranslationXs()[joint_index],
				dna_data.getNeutralJointTranslationYs()[joint_index],
				dna_data.getNeutralJointTranslationZs()[joint_index]
			)
			joint_rotation = (
				dna_data.getNeutralJointRotationXs()[joint_index],
				dna_data.getNeutralJointRotationYs()[joint_index],
				dna_data.getNeutralJointRotationZs()[joint_index]
			)

			# Add bone
			bone = armature.edit_bones.new(joint_name)
			direction_x = math.cos(joint_rotation[1]) * math.cos(joint_rotation[2])
			direction_y = math.cos(joint_rotation[1]) * math.sin(joint_rotation[2])
			direction_z = math.sin(joint_rotation[1])

			bone.head = (joint_translation[0], joint_translation[1], joint_translation[2])
			bone.tail = (
				joint_translation[0] + direction_x,
				joint_translation[1] + direction_y,
				joint_translation[2] + direction_z
			)
			bones[joint_name] = bone

		# Set parent-child relationships
		for i in range(joint_count):
			joint_name = joint_names[i]
			parent_index = dna_data.getJointParentIndex(joint_indices[i])
			if parent_index in joint_indices:
				parent_name = joint_names[joint_indices.index(parent_index)]
				if parent_name in bones:
					bones[joint_name].parent = bones[parent_name]

		bpy.ops.object.mode_set(mode='OBJECT')
		lods.append(armature_obj)
		armature_obj.rotation_euler.x = math.pi * 0.5

	return lods
	
def create_metahuman_meshes(source_dna):
	# Load the DNA data
	dna_data = load_dna(source_dna)  # Ensure this function is defined elsewhere

	# Initialize mapping and LOD count
	mesh_lod_map = {}
	lod_count = dna_data.getLODCount()  # Assuming LODs from 0 to 5

	# Map mesh indices to LODs
	for lod_index in range(lod_count):
		mesh_indices = dna_data.getMeshIndicesForLOD(lod_index)
		for mesh_index in mesh_indices:
			mesh_lod_map[mesh_index] = lod_index

	# Process each mesh index
	for mesh_index in range(dna_data.getMeshCount()):
		lod_index = mesh_lod_map.get(mesh_index, 0)  # Default to LOD 0 if not found
		mesh_name = dna_data.getMeshName(mesh_index)
		print(f"Processing Mesh: {mesh_name} at LOD {lod_index}...")

		# Gather vertex data
		vertex_count = dna_data.getVertexPositionCount(mesh_index)
		vertex_positions_x = dna_data.getVertexPositionXs(mesh_index)
		vertex_positions_y = dna_data.getVertexPositionYs(mesh_index)
		vertex_positions_z = dna_data.getVertexPositionZs(mesh_index)

		# Gather faces
		face_count = dna_data.getFaceCount(mesh_index)
		faces = []
		verts = []

		for vertex_index in dna_data.getVertexLayoutPositionIndices(mesh_index):
			vert = Vector((vertex_positions_x[vertex_index], vertex_positions_y[vertex_index], vertex_positions_z[vertex_index]))
			verts.append(vert)

		for face_index in range(face_count):
			update_progress("Creating faces", face_index / face_count)
			face = dna_data.getFaceVertexLayoutIndices(mesh_index, face_index)
			faces.append(face)

		# Check if an object with the same name already exists
		if mesh_name in bpy.data.objects:
			print(f"Object {mesh_name} already exists. Skipping...")
			continue

		# Create a new mesh and object
		mesh = bpy.data.meshes.new(name=mesh_name)
		obj = bpy.data.objects.new(mesh_name, mesh)

		# Create mesh from vertices and faces
		mesh.from_pydata(verts, [], faces)
		mesh.update()

		# Create or get the collection for this LOD
		collection_name = f"MH_Lod_{lod_index}"
		if collection_name not in bpy.data.collections:
			collection = bpy.data.collections.new(collection_name)
			bpy.context.scene.collection.children.link(collection)
		else:
			collection = bpy.data.collections[collection_name]

		# Link the object to the appropriate collection
		bpy.ops.object.select_all(action="DESELECT")
		collection.objects.link(obj)
		bpy.context.view_layer.objects.active = obj
		obj.select_set(True)
		obj.rotation_euler.x = math.pi * 0.5
