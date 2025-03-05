@tool
extends EditorPlugin


func _enter_tree() -> void:
	add_custom_type(
		"BTGImporter",
		"Node3D",
		preload("res://addons/btg_entity_importer/src/btg_entity_importer.gd"),
		preload("res://addons/btg_entity_importer/icon.svg")
	)


func _exit_tree() -> void:
	remove_custom_type("BTGImporter")
