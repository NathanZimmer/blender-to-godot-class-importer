import bpy
from bpy.app.handlers import persistent
import json
import traceback
from mathutils import Vector
import numpy as np

entity_dict = {}


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
        entity_box.prop(active_object, 'class_type', text='')

        global entity_dict
        # Don't get variable list if this object has no associated class
        if not active_object.class_type in entity_dict or active_object.class_type == 'None':
            return

        # Loop through entity definition dictionary for the variables of this class
        object_variables = {
            f'{active_object.class_type}_{var_name}': var_val
            for var_name, var_val in entity_dict[active_object.class_type].items()
        }
        for variable in object_variables.keys():
            var_name = active_object.bl_rna.properties[variable].name
            entity_box.label(text=var_name)
            entity_box.prop(context.active_object, variable, text='')


class SelectionPopup(bpy.types.Operator):
    """
    Search for objects in the scene based on class name and/or variable definition
    """
    bl_idname = "select_popup.open"
    bl_label = "Find objects by..."

    def execute(self, context):
        """
        TODO
        """
        search_class = context.scene.class_type_search

        if context.scene.search_type == 'var_val' and search_class != 'None':
            search_var = context.scene.var_type_search
            search_val = context.scene.search_val
            for object in context.scene.objects:
                object_val = getattr(object, search_var)
                object.select_set(object.class_type == search_class and self.close(object_val, search_val))
        else:
            for object in context.scene.objects:
                object.select_set(object.class_type == search_class)

        if len(context.selected_objects) > 0 and context.active_object not in context.selected_objects:
            context.view_layer.objects.active = context.selected_objects[0]
        elif len(context.selectable_objects) == 0:
            self.report({'INFO'}, 'No objects found.')

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
        TODO
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
        box.prop(context.scene, 'class_type_search', text='')
        if context.scene.class_type_search == 'None':
            return

        if context.scene.search_type == 'var_val':
            box.prop(context.scene, 'var_type_search', text='')
            box.prop(context.scene, 'search_val', text='')


class ReadJson(bpy.types.Operator):
    """
    Read Godot entity definition JSON
    """
    bl_idname = 'json.read'
    bl_label = 'Read entity JSON'

    def execute(self, context):
        """
        Read entity definition from JSON and initialize values for all scene objects
        """
        # Putting this in a try-catch to prevent users from locking themselves out of loading
        # a new JSON
        try:
            # Free variables from old def JSON
            global entity_dict
            free_object_variables(entity_dict)
        except:
            self.report({'ERROR'}, 'Could not free variables')

        try:
            read_json(context)
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

        # Initialize objects with class_name and variables from the entity JSON
        init_objects(context.scene)

        self.report({'INFO'}, 'Loaded JSON!')
        # self.report({'INFO'}, f'{context.scene.entity_def=}')
        return {'FINISHED'}


class WriteJson(bpy.types.Operator):
    """
    Write Blender to Godot import JSON
    """
    bl_idname = 'json.write'
    bl_label = 'Write BTG import JSON'

    def execute(self, context):
        """
        Write scene object classes and variables to Godot import JSON
        """
        btg_json = {}
        global entity_dict
        json_types = (int, str, bool, float)  # Values that can be translated to JSON format

        for object in context.scene.objects:
            # Ignore objects with no class
            if object.class_type == 'None':
                continue

            # Get list of variable names to use
            object_variables = entity_dict[object.class_type]
            object_name = object.name.replace('.', '_')  # Convert to Godot naming standards
            class_type = object.class_type

            btg_json[object_name] = {
                'class': class_type,
                'variables': {
                    var_name: [var_vals[0], getattr(object, f'{class_type}_{var_name}')] if isinstance(getattr(object, f'{class_type}_{var_name}'), json_types)
                    # Convert non-JSON vartypes to string
                    else [var_vals[0], str(getattr(object, var_name)[0:])]
                    for var_name, var_vals in object_variables.items()
                }
            }

        try:
            with open(context.scene.btg_write_path, 'w+') as file:
                json.dump(btg_json, file)

            # self.report({'INFO'}, f'{btg_json=}')
            self.report({'INFO'}, 'Wrote JSON!')
            return {'FINISHED'}
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to write JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}


def read_json(context):
    """
    Read json from path `entity_def_path` scene variable into `entity` scene variable

    Parameters
    ----------
    `context`: The bpy context to read `entity_def_path` from.
    """
    with open(context.scene.entity_def_path) as file:
        # Place 'None' at the first index for defaulting
        global entity_dict
        entity_dict = {'None': ''}
        entity_dict |= json.load(file)

        # NOTE: Blender cannot store dict type objects, so this is a workaround
        # to preserve the dict between blender sessions.
        context.scene.entity_def = json.dumps(entity_dict)

@persistent
# TODO: Add support for Vector2
# TODO: Condense the three functions that all loop over var_type. Adding in new vars
# will be annoying until this is done.
def init_objects(_):
    """
    Initialize global entity_dict and object classes and varaibles
    """
    global entity_dict
    entity_dict = json.loads(bpy.context.scene.entity_def)

    for class_name, class_def in entity_dict.items():
        if class_name == 'None':
            continue

        for var_name, var_vals in class_def.items():
            var_type, var_default, var_desc = var_vals

            if var_type == 'int':
                prop_class = bpy.props.IntProperty
                default = int(var_default)
            elif var_type == 'float':
                prop_class = bpy.props.FloatProperty
                default = float(var_default)
            elif var_type == 'Vector3':
                prop_class = bpy.props.FloatVectorProperty
                default = Vector(var_default)
            elif var_type == 'Vector3i':
                prop_class = bpy.props.IntVectorProperty
                default = Vector(var_default)
            elif var_type == 'bool':
                prop_class = bpy.props.BoolProperty
                default = bool(var_default)
            # TODO: add enum
            else:
                prop_class = bpy.props.StringProperty
                default = str(var_default)

            setattr(
                bpy.types.Object,
                f'{class_name}_{var_name}',
                prop_class(
                    name=f'{var_name}: {var_type}',
                    description=var_desc,
                    default=default,
                )
            )

# FIXME: Switching from a bool to a vector does not update `search_val`, which causes an
# error when evaluating equality
def set_search_prop(_, context):
    var_type = (
        entity_dict[context.scene.class_type_search][context.scene.var_type_search][0]
    )
    if var_type == 'int':
        prop_class = bpy.props.IntProperty
        default = 0
    elif var_type == 'float':
        prop_class = bpy.props.FloatProperty
        default = 0.0
    elif var_type == 'Vector3':
        prop_class = bpy.props.FloatVectorProperty
        default = Vector((0.0, 0.0, 0.0))
    elif var_type == 'Vector3i':
        prop_class = bpy.props.IntVectorProperty
        default = Vector((0, 0, 0))
    elif var_type == 'bool':
        prop_class = bpy.props.BoolProperty
        default = False
    # TODO: add enum
    else:
        prop_class = bpy.props.StringProperty
        default = ''

    bpy.types.Scene.search_val = prop_class(
        name='search value',
    )
    context.scene.search_val = default

def reset_object_vars(self, context):
    """
    Reset the vars of this object to their defaults
    """
    global entity_dict
    entity_dict = json.loads(context.scene.entity_def)

    for class_name, class_def in entity_dict.items():
        if class_name == 'None':
            continue

        for var_name, var_vals in class_def.items():
            var_type, var_default, _ = var_vals

            if var_type == 'int':
                default = int(var_default)
            elif var_type == 'float':
                default = float(var_default)
            elif var_type == 'Vector3':
                default = Vector(var_default)
            elif var_type == 'Vector3i':
                default = Vector(var_default)
            elif var_type == 'bool':
                default = bool(var_default)
            # TODO: add enum
            else:
                default = str(var_default)

            self[var_name] = default

def get_entity_list(_, _0):
    """
    Get the keys from `entity_dict` in blender ENUM format
    """
    global entity_dict
    return [(key, key, key) for key in entity_dict.keys()]

def get_var_search_list(_, context):
    """
    Get the vars for `context.scene.class_type_search` in blender ENUM format
    """
    global entity_dict
    search_class = entity_dict[context.scene.class_type_search]
    return [(key, key, key) for key in search_class.keys()]

def free_object_variables(entity_dict: dict):
    """
    Free entity JSON defined variables for switching entity def or unloading addon
    """
    for class_name, class_def in entity_dict.items():
        if class_name == 'None':
            continue

        for var_name in class_def.keys():
            variable = getattr(bpy.types.Object, var_name)
            del variable

def register():
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(ReadJson)
    bpy.utils.register_class(WriteJson)
    bpy.utils.register_class(SelectionPopup)

    if not init_objects in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(init_objects)

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
    bpy.types.Object.class_type = bpy.props.EnumProperty(
        name='Godot Entities',
        description='ENUM for each object\'s class selection',
        items=get_entity_list,
        update=reset_object_vars,
        default=0,
    )
    bpy.types.Scene.entity_def = bpy.props.StringProperty(
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
    bpy.types.Scene.class_type_search = bpy.props.EnumProperty(
        name='Godot Entities',
        description='ENUM for searching for classes',
        items=get_entity_list,
        default=0,
    )
    bpy.types.Scene.var_type_search = bpy.props.EnumProperty(
        name='Godot Entity variables',
        description='ENUM for searching for classes',
        items=get_var_search_list,
        update=set_search_prop,
        default=0,
    )

def unregister():
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(ReadJson)
    bpy.utils.unregister_class(WriteJson)
    bpy.utils.unregister_class(SelectionPopup)

    if init_objects in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(init_objects)

    # File IO
    del bpy.types.Scene.entity_def_path
    del bpy.types.Scene.btg_write_path

    # Entity definition
    del bpy.types.Object.class_type
    # Free entity definition variables loaded from the JSON
    global entity_dict
    free_object_variables(entity_dict)
    del bpy.types.Scene.entity_def

    # Property searching
    del bpy.types.Object.class_type_search
    del bpy.types.Scene.class_type_search
    if 'search_val' in bpy.context.scene:
        del bpy.types.Scene.search_val

bl_info = {
    'name': 'Nathan\'s Blender To Godot (BTG) Pipeline',
    'blender': (2, 80, 0),
    'category': 'Object',
}

if __name__ == '__main__':
    register()