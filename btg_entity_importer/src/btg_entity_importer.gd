## Blender-to-Godot entity importer. Reads from an entity definition JSON and
## assigns class/values to nodes in the Godot scene corresponding to the
## objects in Blender scene. [br]
## Runs BTG import on `.blend` and `.glb` files if the import options specifies an `entity_definition`
class_name BTGImporter extends EditorScenePostImportPlugin

var _run_btg_import := false


func _get_import_options(path):
    if path.get_extension() in ["blend", "glb"]:
        _run_btg_import = true
        add_import_option_advanced(
            TYPE_STRING, "entity_definition", "", PROPERTY_HINT_FILE, "*.json"
        )


func _post_process(scene):
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


## Recursively Navigate down node tree and assign classes/variables based on the
## entity definition JSON. [br]
## ## Parameters [br]
## `entity_def`: Dictionary rep of the entity definition JSON [br]
## `node`: The starting node for replacements (inclusive) [br]
## ## Returns [br]
## Number of nodes that failed to import from the end of
## the tree up to `node`.
static func _import_entities_from_def(
    entity_def: Dictionary,
    node: Node3D,
) -> int:
    var num_failures = 0
    # Need to keep track of these for setting owner later
    var tscn_children: Array[Node] = []

    var new_node = null
    if node.name in entity_def:
        var new_class = entity_def[node.name].get("class", "")
        var new_class_uid = entity_def[node.name].get("uid", "")

        if new_class_uid.is_empty():
            new_node = ClassDB.instantiate(new_class)
        else:
            var uid = ResourceUID.text_to_id(new_class_uid)
            var node_class_full_path = ResourceUID.get_id_path(uid)

            if node_class_full_path.get_extension() == "gd":
                new_node = load(new_class_uid).new()
            else:
                new_node = load(new_class_uid).instantiate()
                tscn_children = new_node.get_children()

        if new_node == null:
            push_warning(
                (
                    "Class not defined: Failed on (Node: %s, class_name: %s, uid: %s)"
                    % [node.name, new_class, new_class_uid]
                )
            )
            num_failures += 1

    # No early return because we still want to navigate through the whole tree
    if new_node != null:
        new_node.transform = node.transform
        new_node.name = node.name

        var mesh = node.get("mesh")
        if mesh != null:
            new_node.set("mesh", mesh)

        node.replace_by(new_node, true)
        node.free()
        node = new_node

        # If we don't set the owner of nodes from the new instantiated scene, they
        # will be deleted upon reloading this scene
        for child in tscn_children:
            _recursive_set_owner(child, node.get_owner())

        var variables = entity_def[node.name]["variables"]
        for variable in variables:
            if not variable in node:
                push_warning(
                    (
                        "Missing variable definition! Failed on (Node: %s, variable: %s)"
                        % [node.name, variable]
                    )
                )
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
                            % [node.name, type, variable]
                        )
                    )
                    num_failures += 1
                    continue
                node.set(variable, converted_value)

    if node.get_children().is_empty():
        return num_failures
    for child in node.get_children():
        num_failures += _import_entities_from_def(entity_def, child)

    return num_failures


## Set the owner of `node` and all nodes down its tree to `owner`
static func _recursive_set_owner(node: Node3D, owner: Node3D):
    node.set_owner(owner)
    var children = node.get_children()
    if children.is_empty():
        return
    for child in children:
        _recursive_set_owner(child, owner)


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
        return Vector3i(value[0], value[1], value[2])
    if type == "Vector2":
        value = value.replace("(", "[")
        value = value.replace(")", "]")
        value = str_to_var(value)
        return Vector2(value[0], value[1])
    if type == "Vector2i":
        value = value.replace("(", "[")
        value = value.replace(")", "]")
        value = str_to_var(value)
        return Vector2i(value[0], value[1])
    if node.has_method(type):
        value = node.call(type, value)
        return value

    return null
