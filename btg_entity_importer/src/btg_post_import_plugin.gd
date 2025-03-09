## TODO
class_name BTGPostImportPlugin extends EditorScenePostImportPlugin

var run_btg_import = false


func _get_import_options(path):
    if path.get_extension() in ["blend", "glb"]:
        run_btg_import = true
        add_import_option_advanced(TYPE_STRING, "entity_definition", "", PROPERTY_HINT_FILE, "*.json")


func _post_process(scene):
    if not run_btg_import:
        return scene

    var entity_definition_path = get_option_value("entity_definition")
    if entity_definition_path.is_empty():
        return scene

    var godot_import_file = FileAccess.open(entity_definition_path, FileAccess.READ)
    if godot_import_file == null:
        push_error(error_string(FileAccess.get_open_error()))
        return scene

    var import_text = godot_import_file.get_as_text()

    var json = JSON.new()
    json.parse(import_text)
    var entity_def = json.data

    var num_failures = _import_entities_from_def(entity_def, scene)
    if num_failures > 0:
        print("Finished import with %d failures (see warnings)" % num_failures)

    return scene


## Recursively search through nodes and replace based on import JSON
static func _import_entities_from_def(entity_def: Dictionary, node: Node3D) -> int:
    var num_failures = 0
    var node_name = node.name

    # Verify that the class_name is valid
    var new_node = null
    var tscn_child_nodes = []
    if node_name in entity_def:
        var node_class_name = entity_def[node_name]["class"]
        var node_class_uid = entity_def[node_name]["uid"]

        # Populate new node
        var uid = ResourceUID.text_to_id(node_class_uid)
        var node_class_full_path = ResourceUID.get_id_path(uid)
        if node_class_full_path.get_extension() == "gd":
            new_node = load(node_class_uid).new()
        else:
            new_node = load(node_class_uid).instantiate()
            tscn_child_nodes = new_node.get_children()
        if new_node == null:
            new_node = ClassDB.instantiate(node_class_name)
            if new_node == null:
                push_warning(
                    (
                        "Class not defined: Failed on (Node: %s, class_name: %s, uid: %s)"
                        % [node_name, node_class_name, node_class_uid]
                    )
                )
                num_failures += 1

    # If the class_name is valid, continue copying from definition
    if new_node != null:
        new_node.transform = node.transform
        new_node.name = node.name

        # Replace and free
        node.replace_by(new_node, true)
        node.free()
        node = new_node

        # Set owner of new nodes
        for child in tscn_child_nodes:
            child.set_owner(node.get_owner())

        # Assign values
        var variables = entity_def[node_name]["variables"]
        for variable in variables:
            if not variable in node:
                push_warning("Missing variable definition! Failed on (Node: %s, variable: %s)" % [node_name, variable])
                num_failures += 1
                continue

            var type = variables[variable]["type"]
            var value = variables[variable]["value"]

            if type in ["int", "String", "bool", "float", "enum"]:
                node.set(variable, value)
            else:
                var converted_value = _cast_to_type(node, value, type)
                if converted_value == null:
                    push_warning(
                        (
                            "Failed to cast variable type! Failed on (Node: %s, type: %s, variable: %s)"
                            % [node_name, type, variable]
                        )
                    )
                    num_failures += 1
                    continue
                node.set(variable, converted_value)

    # Recursively search children
    if node.get_children().is_empty():
        return num_failures
    for child in node.get_children():
        num_failures += _import_entities_from_def(entity_def, child)

    return num_failures


static func _cast_to_type(node: Node, value, type: String):
    if type == "list":
        return str_to_var(value)
    if type == "Vector3":
        value = value.replace("(", "[")
        value = value.replace(")", "]")
        value = str_to_var(value)
        return Vector3(value[0], value[1], value[2])
    if type == "Vector3i":
        value = value.replace("(", "[")
        value = value.replace(")", "]")
        value = str_to_var(value)
        return Vector3i(value)
    if node.has_method(type):
        value = node.call(type, value)
        return value

    return null
