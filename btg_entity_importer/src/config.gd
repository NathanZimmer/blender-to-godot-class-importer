@tool
extends EditorPlugin

var _btg_importer


func _enter_tree() -> void:
    _btg_importer = preload("uid://bu1bg70u1dtyq").new()
    add_scene_post_import_plugin(_btg_importer)


func _exit_tree() -> void:
    remove_scene_post_import_plugin(_btg_importer)
    _btg_importer = null
