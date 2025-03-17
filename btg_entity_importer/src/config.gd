@tool
extends EditorPlugin

var btg_importer


func _enter_tree() -> void:
    btg_importer = preload("uid://bu1bg70u1dtyq").new()
    add_scene_post_import_plugin(btg_importer)


func _exit_tree() -> void:
    remove_scene_post_import_plugin(btg_importer)
    btg_importer = null
