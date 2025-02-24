@tool
extends EditorPlugin


func _enter_tree() -> void:
	add_custom_type(
		"BTGImporter",
		"Node3D",
		preload("res://addons/blender_to_godot_pipeline/src/core/btg_importer.gd"),
		preload("res://addons/blender_to_godot_pipeline/icon.svg")
	)


func _exit_tree() -> void:
	remove_custom_type("BTGImporter")