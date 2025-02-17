import bpy
from bpy.app.handlers import persistent
import json
import traceback
from mathutils import Vector
import numpy as np

entity_template = {}

# %% GUI Classes
class BTGPanel(bpy.types.Panel):
    """
    Settings panel for the Blender to Godot pipeline
    """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Blender to Godot Pipeline'
    bl_category = 'Blender To Godot'

    def draw(self, context):
        """
        Define the layout of the panel
        """
        layout = self.layout
        active_object = context.active_object
        scene_props = context.scene.bl_rna.properties

        layout.label(text='Import and Export')
        import_export_box = layout.box()
        import_export_box.label(text=scene_props['entity_def_path'].name)
        import_export_box.prop(context.scene, 'entity_def_path', text='')
        import_export_box.operator('json.read')
        import_export_box.label(text=scene_props['btg_write_path'].name)
        import_export_box.prop(context.scene, 'btg_write_path', text='')
        import_export_box.operator('json.write')

        layout.label(text='Select Objects')
        misc = layout.box()
        misc.operator('select_popup.open')

        # Don't show properties if there is no object selected
        if active_object is None:
            return

        layout.label(text='Entity Properties')
        entity_box = layout.box()

        entity_box.label(text='Godot Class')
        entity_box.prop(active_object, 'class_name', text='')

        global entity_template
        # Don't get variable list if this object has no associated class
        if not active_object.class_name in entity_template or active_object.class_name == 'None':
            return

        # Loop through entity definition dictionary for the variables of this class
        object_variables = {
            f'{active_object.class_name}_{var_name}': var_val
            for var_name, var_val in entity_template[active_object.class_name].items()
        }
        for variable in object_variables.keys():
            var_name = active_object.bl_rna.properties[variable].name
            entity_box.label(text=var_name)
            entity_box.prop(context.active_object, variable, text='')


class SelectionPopup(bpy.types.Operator):
    """
    Search for objects in the scene based on class name or class variable value
    """
    bl_idname = "select_popup.open"
    bl_label = "Find objects by..."

    def execute(self, context):
        """
        Use search_ scene variables to select objects with the specified entity values
        """
        search_class = context.scene.search_class_name

        if context.scene.search_type == 'var_val' and search_class != 'None':
            search_var = context.scene.search_var
            search_val = context.scene.search_val

            if search_var == '':
                self.report({'WARNING'}, 'No search variable selected.')
                return {'CANCELLED'}

            for object in context.scene.objects:
                object_val = getattr(object, f'{search_class}_{search_var}')
                object.select_set(object.class_name == search_class and self.close(object_val, search_val))
        else:
            for object in context.scene.objects:
                object.select_set(object.class_name == search_class)

        if len(context.selected_objects) > 0 and context.active_object not in context.selected_objects:
            context.view_layer.objects.active = context.selected_objects[0]

        if len(context.selected_objects) == 0:
            self.report({'INFO'}, 'No objects found.')
        else:
            self.report({'INFO'}, 'Objects selected!')

        return {'FINISHED'}

    @staticmethod
    def close(x, y, delta=1.e-8):
        """
        Check if vars `x` and `y` are within `delta` distance
        """
        # If string, do regular equality
        if isinstance(x, str) or isinstance(y, str):
            return x == y

        return np.allclose(x, y, atol=delta)

    def invoke(self, context, _):
        """
        Invoke popup
        """
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """
        Define the layout of the sub-panel
        """
        layout = self.layout

        layout.label(text='Search by...')
        layout.prop(context.scene, 'search_type', text='')

        layout.label(text='Parameters')
        box = layout.box()
        box.prop(context.scene, 'search_class_name', text='')
        if context.scene.search_class_name == 'None':
            return

        if context.scene.search_type == 'var_val':
            box.prop(context.scene, 'search_var', text='')
            box.prop(context.scene, 'search_val', text='')


# %% Operator Classes
class EntityTemplateReader(bpy.types.Operator):
    """
    Read Godot entity template JSON and save to global `entity_template` dict
    """
    bl_idname = 'json.read'
    bl_label = 'Read entity JSON'

    def execute(self, _):
        """
        Read entity template from JSON and initialize values for all scene objects
        """
        # Putting this in a try-catch to prevent users from locking themselves out of loading
        # a new JSON
        global entity_template
        try:
            # Free variables from old def JSON
            free_object_variables(entity_template)
        except:
            self.report({'ERROR'}, 'Could not free variables')

        try:
            self.read_template_json()
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

        # Reinitialize after loading new entity template
        init()

        self.report({'DEBUG'}, f'{entity_template=}')
        self.report({'INFO'}, 'Loaded JSON!')
        return {'FINISHED'}

    @staticmethod
    def read_template_json():
        """
        Read json from scene var `entity_def_path` into scene var `entity_template_str` and global var `entity_template`
        """
        with open(bpy.context.scene.entity_def_path) as file:
            # Place 'None' at the first index for defaulting
            global entity_template
            entity_template = {'None': ''}
            entity_template |= json.load(file)

            # NOTE: Blender cannot store dict type objects, so this is a workaround
            # to preserve the dict between blender sessions.
            bpy.context.scene.entity_template_str = json.dumps(entity_template)


class EntityImportWriter(bpy.types.Operator):
    """
    Write BTG import JSON from entity defintions
    """
    bl_idname = 'json.write'
    bl_label = 'Write BTG import JSON'

    def execute(self, context):
        """
        Write entity definitions to Godot import JSON
        """
        btg_json = {}
        global entity_template
        json_types = (int, str, bool, float)  # Values that can be translated to JSON format

        for object in context.scene.objects:
            # Ignore objects with no class
            if object.class_name == 'None':
                continue

            # Get list of variable names to use
            class_name = object.class_name
            object_variables = entity_template[class_name]
            object_name = object.name.replace('.', '_')  # Convert to Godot naming standards

            # NOTE: The blender api does NOT like OOP, so we have to do some shenanigans with
            # prepending class_name to var names to avoid collisions with other classes.
            get_var = lambda var_name: getattr(object, f'{class_name}_{var_name}')

            btg_json[object_name] = {
                'class': class_name,
                'variables': {
                    var_name: [var_vals[0], get_var(var_name)] if isinstance(get_var(var_name), json_types)
                    # Convert non-JSON vartypes to string
                    else [var_vals[0], str(get_var(var_name)[0:])]
                    for var_name, var_vals in object_variables.items()
                }
            }

        try:
            with open(context.scene.btg_write_path, 'w+') as file:
                json.dump(btg_json, file)

            self.report({'DEBUG'}, f'{btg_json=}')
            self.report({'INFO'}, 'Wrote JSON!')
            return {'FINISHED'}
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to write JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

# %% Utility Function
# NOTE: Weird/unused function params come from API input requirements
@persistent
def init(file=None):
    """
    Initialize global `entity_template` dict, search variables, and object entity definitions
    """
    global entity_template
    entity_template = json.loads(bpy.context.scene.entity_template_str)

    bpy.context.scene.search_class_name = get_entity_list()[0][0]

    # Populate entity-definition object vars
    for class_name, class_def in entity_template.items():
        if class_name == 'None':
            continue

        for var_name, var_vals in class_def.items():
            var_type, var_default, var_desc, var_items = var_vals

            prop_class, default = get_blender_prop(var_type, var_default)

            prop_params = {
                'name': f'{var_name}: {var_type}',
                'description': var_desc,
                'default': default,
            }
            if var_type == 'enum':
                prop_params['items'] = [(key, key, key) for key in var_items]

            # NOTE: The blender api does NOT like OOP, so we have to do some shenanigans with
            # prepending class_name to var names to avoid collisions with other classes.
            setattr(
                bpy.types.Object,
                f'{class_name}_{var_name}',
                prop_class(**prop_params)
            )

def reset_search_var(self=None, context=bpy.context):
    """
    Reset scene variable `search_var` to its default for switching `search_class_name`
    """
    context.scene.search_var = get_var_search_list()[0][0]

def set_search_val(self=None, context=bpy.context):
    """
    Set the scene `search_val` variable based on the scene variables 'search_class_name' `search_var`
    """
    search_class_name = context.scene.search_class_name
    search_var = context.scene.search_var
    var_type, var_default, var_desc, var_items = entity_template[search_class_name][search_var]

    prop_class, default = get_blender_prop(var_type, var_default)
    prop_params = {
        'name': f'{search_var}: {var_type}',
        'description': var_desc,
    }
    if var_type == 'enum':
        prop_params['items'] = [(key, key, key) for key in var_items]

    bpy.types.Scene.search_val = prop_class(**prop_params)
    context.scene.search_val = default

# TODO: Add support for Vector2
# TODO: Add support for Array
def get_blender_prop(var_type: str, default: any = None) -> tuple:
    """
    Get Blender `bpy.props` type object and a correctly-typed default

    Parameters
    ----------
    `var_type`: A type from the entity template
    `default`: Optional default to return as a correctly-typed default

    Returns
    -------
    `(prop_class, prop_default)`: A Blender `bpy.props` Property and
    a correctly-typed default value
    """
    match(var_type):
        case 'int':
            prop_class = bpy.props.IntProperty
            prop_default = 0 if default is None else int(default)
        case 'float':
            prop_class = bpy.props.FloatProperty
            prop_default = 0.0 if default is None else float(default)
        case 'Vector3':
            prop_class = bpy.props.FloatVectorProperty
            prop_default = Vector((0.0, 0.0, 0.0)) if default is None else Vector(default)
        case 'Vector3i':
            prop_class = bpy.props.IntVectorProperty
            prop_default = Vector((0, 0, 0)) if default is None else Vector(default)
        case 'bool':
            prop_class = bpy.props.BoolProperty
            prop_default = False if default is None else bool(default)
        case 'enum':
            prop_class = bpy.props.EnumProperty
            prop_default = None if default is None else str(default)
        case _:
            prop_class = bpy.props.StringProperty
            prop_default = '' if default is None else str(default)

    return prop_class, prop_default

# def reset_object_vars(self, context):
#     """
#     Reset the vars of this object to their defaults
#     """
#     global entity_template
#     entity_template = json.loads(context.scene.entity_template_str)

#     for class_name, class_def in entity_template.items():
#         if class_name == 'None':
#             continue

#         for var_name, var_vals in class_def.items():
#             var_type, var_default, _ = var_vals

#             if var_type == 'int':
#                 default = int(var_default)
#             elif var_type == 'float':
#                 default = float(var_default)
#             elif var_type == 'Vector3':
#                 default = Vector(var_default)
#             elif var_type == 'Vector3i':
#                 default = Vector(var_default)
#             elif var_type == 'bool':
#                 default = bool(var_default)
#             # TODO: add enum
#             else:
#                 default = str(var_default)

#             self[var_name] = default

def get_entity_list(self=None, context=None):
    """
    Get the keys from `entity_dict` in blender ENUM format
    """
    global entity_template
    return [(key, key, key) for key in entity_template.keys()]

def get_var_search_list(self=None, context=bpy.context):
    """
    Get the vars for `context.scene.search_class_name` in blender ENUM format
    """
    global entity_template
    search_class = entity_template[context.scene.search_class_name]
    return [(key, key, key) for key in search_class.keys()]

def free_object_variables(entity_template: dict):
    """
    Free entity JSON defined variables for switching entity template or unloading addon
    """
    for class_name, class_def in entity_template.items():
        if class_name == 'None':
            continue

        for var_name in class_def.keys():
            delattr(bpy.types.Object, var_name)

# %% Blender API Setup
def register():
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(SelectionPopup)
    bpy.utils.register_class(EntityTemplateReader)
    bpy.utils.register_class(EntityImportWriter)

    if not init in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(init)

    # File IO
    bpy.types.Scene.entity_def_path = bpy.props.StringProperty(
        name = 'Godot entity definition path',
        description = 'The path of your Godot entity definition JSON',
        subtype = 'FILE_PATH',
    )
    bpy.types.Scene.btg_write_path = bpy.props.StringProperty(
        name = 'BTG import write-path',
        description = (
            'The path to write your BTG import JSON. You have to write '
            'this JSON in order to use the import script in Godot.'
        ),
        subtype = 'FILE_PATH',
    )

    # Entity definition
    bpy.types.Object.class_name = bpy.props.EnumProperty(
        name='Godot Entities',
        description='ENUM for each object\'s class selection',
        items=get_entity_list,
        default=0,
    )
    bpy.types.Scene.entity_template_str = bpy.props.StringProperty(
        name='Godot Entity JSON',
        description=(
            'Stores the entity definition for use between blender sessions. This is'
            'only read from on startup and only written to when a new def is loaded'
        ),
        default='{"None": ""}',
    )

    # Property searching
    bpy.types.Scene.search_type = bpy.props.EnumProperty(
        items=[
            ('class', 'Class', 'Select all objects of this class'),
            ('var_val', 'Variable value', 'Select all objects with this variable value')
        ],
        description='ENUM for selecting search option',
        default=0,
    )
    bpy.types.Scene.search_class_name = bpy.props.EnumProperty(
        name='Godot Entities',
        description='ENUM for searching for classes',
        items=get_entity_list,
        update=reset_search_var,
        default=0,
    )
    bpy.types.Scene.search_var = bpy.props.EnumProperty(
        name='Godot Entity variables',
        description='ENUM for searching for variable values',
        items=get_var_search_list,
        update=set_search_val,
        default=0,
    )

def unregister():
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(SelectionPopup)
    bpy.utils.unregister_class(EntityTemplateReader)
    bpy.utils.unregister_class(EntityImportWriter)

    if init in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(init)

    # File IO
    del bpy.types.Scene.entity_def_path
    del bpy.types.Scene.btg_write_path

    # Entity definition
    del bpy.types.Object.class_name
    # Free entity definition variables loaded from the JSON
    global entity_template
    free_object_variables(entity_template)
    del bpy.types.Scene.entity_template_str

    # Property searching
    del bpy.types.Scene.search_class_name
    if 'search_val' in bpy.context.scene:
        del bpy.types.Scene.search_val

bl_info = {
    'name': 'Nathan\'s Blender To Godot (BTG) Pipeline',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()