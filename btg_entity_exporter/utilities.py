"""
Utilitiy functions for operating on `bpy.context` `scene` and `object` variables defined in `__init__.register()`
"""

import bpy


def refresh_class_definitions() -> None:
    """
    Compare `object.class_definition` values to `scene.entity_template`.
    Check if:
    * class was removed from entity template
    * class order was changed in entity template
    * class variables were reordered/changed
    """
    scene = bpy.context.scene

    for object in scene.objects:
        # If object is None, it has no vars to clear
        if object.class_name == 'None':
            continue

        # If class was removed from template, clear its definition
        if object.class_name_backup not in scene.entity_template:
            object.class_name = 'None'
            object.class_definition.clear()
            continue

        # If class def was updated, re-assign values from previous def
        # Grab old variables
        old_props = object.class_definition.get_properties()
        # Reset class_name to backup in-case class definition order has changed
        object.class_name = object.class_name_backup
        # refill common vars between previous and current template iterations
        for prop in object.class_definition:
            name = prop.name
            type = prop.godot_type
            if name in old_props and type == old_props[name]['type']:
                prop.value = old_props[name]['value']


def reset_class_definition(self, context) -> None:
    """
    Reset `self.class_definition` and populate with new variables
    from new `context.scene.entity_template[self.class_name]`

    Parameters
    ----------
    `self`: Caller of this function

    `context`: Context of the caller of this function
    """
    self.class_definition.clear()
    self.class_name_backup = self.class_name

    if self.class_name == 'None':
        return
    # elif self.data:
    #     # If this object has a mesh, display warning
    #     draw_func = lambda self, _: self.layout.label(
    #         text= (
    #                 "Object mesh data will be deleted on import if this Object's class "
    #                 'does not inherit from MeshInstance3D'
    #             )
    #     )
    #     bpy.context.window_manager.popup_menu(
    #         draw_func=draw_func, title="Warning", icon='ERROR',
    #     )

    class_def = context.scene.entity_template[self.class_name]

    for var_name, var_def in class_def['variables'].items():
        # var_type, var_default, var_desc, var_items = var_def
        var_type = var_def['type']
        var_default = var_def['default']
        var_desc = var_def['description']
        var_desc = var_def.get('description', '')
        var_items = var_def.get('options', [])

        self.class_definition.add(
            name=var_name,
            type=var_type,
            value=var_default,
            description=var_desc,
            items=var_items,
        )


def set_search_property(self, _) -> None:
    """
    Set the Scene search property based on `scene.search_class_name` and
    `scene.search_var_name`

    Parameters
    ----------
    `self`: Caller of this function
    """
    class_name = self.search_class_name
    var_name = self.search_var_name
    var_def = self.entity_template[class_name]['variables'][var_name]
    var_type = var_def['type']
    var_val = var_def['default']
    var_desc = var_def.get('description', '')
    var_items = var_def.get('options', [])

    self.comparison_type = '=='

    self.search_property.init(
        name=var_name,
        type=var_type,
        value=var_val,
        description=var_desc,
        items=var_items,
    )


def get_variable_search_list(self, _) -> list[tuple[str, str, str]]:
    """
    Get the keys for `scene.search_class_name` in blender ENUM format

    Parameters
    ----------
    `self`: Caller of this function
    """
    search_class = self.entity_template[self.search_class_name]
    return [(key, key, key) for key in search_class['variables'].keys()]


def get_entity_list(_, context) -> list[tuple[str, str, str]]:
    """
    Get the keys for `context.object.class_name` in blender ENUM format

    Parameters
    ----------
    `context`: Context of the caller of this function
    """
    return [(key, key, key) for key in context.scene.entity_template.keys()]


@bpy.app.handlers.persistent
def load_template(_) -> None:
    """
    Load entity template at the start of each session
    """
    bpy.context.scene.entity_template.init_dict()


def export_on_save(_) -> None:
    """
    Export entity definition whenever the file is saved
    if `scene.export_on_save == True`
    """
    if bpy.context.scene.export_on_save:
        bpy.ops.json.write()
