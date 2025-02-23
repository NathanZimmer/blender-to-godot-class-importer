@tool
extends EditorPlugin

var editor_button_plugin: EditorButtonPlugin


func _enter_tree() -> void:
	editor_button_plugin = EditorButtonPlugin.new()
	add_inspector_plugin(editor_button_plugin)


func _exit_tree() -> void:
	if is_instance_valid(editor_button_plugin):
		remove_inspector_plugin(editor_button_plugin)
		editor_button_plugin = null
