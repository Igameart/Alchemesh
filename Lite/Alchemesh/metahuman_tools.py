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

print("Python version")
print(sys.version)
print("Version info.")
print(sys.version_info)

current_dir = os.path.dirname(os.path.abspath(__file__))
dnacalib_dir = os.path.join(current_dir, 'dnacalib')

sys.path.append(dnacalib_dir)

try:
	from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, JSONStreamWriter
	import dna
	import dnacalib as dnac
except ImportError as e:
	print(f"Failed to import from dna: {e}")

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