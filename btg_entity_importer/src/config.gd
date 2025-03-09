@tool
extends EditorPlugin

var btg_post_import_plugin


func _enter_tree() -> void:
    add_custom_type(
        "BTGImporter",
        "Node3D",
        preload("res://addons/blender_to_godot_pipeline/src/btg_entity_importer.gd"),
        preload("res://addons/blender_to_godot_pipeline/icon.svg")
    )
    btg_post_import_plugin = preload("uid://bu1bg70u1dtyq").new()
    add_scene_post_import_plugin(btg_post_import_plugin)


func _exit_tree() -> void:
    remove_custom_type("BTGImporter")
    remove_scene_post_import_plugin(btg_post_import_plugin)
    btg_post_import_plugin = null
