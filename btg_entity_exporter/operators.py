"""
`bpy.types.Operator` inheriting classes
"""
import bpy
import json
import traceback


class EntityTemplateReader(bpy.types.Operator):
    """
    Read Godot entity template JSON and object entity definitions
    """
    bl_idname = 'json.read'
    bl_label = 'Read entity JSON'

    def execute(self, context):
        """
        Read entity template from JSON and initialize values for all scene objects
        """
        try:
            self.read_template_json()
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}

        # Clear old defs and refresh updated defs
        self.refresh_class_definitions()

        self.report({'DEBUG'}, f'{context.scene.entity_template=}')
        self.report({'INFO'}, 'Loaded JSON!')
        return {'FINISHED'}

    @staticmethod
    def read_template_json() -> None:
        """
        Read json from `scene.entity_def_path` into `scene.entity_template`
        """
        entity_def_path = bpy.context.scene.entity_def_path
        if entity_def_path[:2] == '//':
            entity_def_path = bpy.path.abspath('//') + entity_def_path[2:]
        with open(entity_def_path) as entity_json:
            # Place 'None' at the first index for defaulting
            bpy.context.scene.entity_template.reset({'None': ''} | json.load(entity_json))

    @staticmethod
    def refresh_class_definitions() -> None:
        """
        Compare `object.class_definition` values to `scene.entity_template`.
        Check if:
        * class was removed
        * class order was changed
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


class EntityImportWriter(bpy.types.Operator):
    """
    Write BTG import JSON from object entity defintions
    """
    bl_idname = 'json.write'
    bl_label = 'Write BTG import JSON'

    def execute(self, context):
        """
        Write entity definitions to Godot import JSON
        """
        json_types = (int, str, bool, float)  # Values that can be translated to JSON format

        # Construct JSON
        btg_json = {
            # Convert to Godot naming standards
            object.name.replace('.', '_'): {
                'class': object.class_name,
                'uid': context.scene.entity_template[object.class_name]['uid'],
                'variables': {
                    prop.name: {
                        'type': prop.godot_type,
                        'value': (
                            prop.value if type(prop.value) in json_types
                            else str(prop.value[0:])  # Convert non-JSON vartypes to string
                        )
                    }
                    for prop in object.class_definition
                }
            }
            for object in context.scene.objects if object.class_name != 'None'
        }

        # Write JSON
        try:
            btg_write_path = bpy.context.scene.btg_write_path
            if btg_write_path[:2] == '//':
                btg_write_path = bpy.path.abspath('//') + btg_write_path[2:]
            with open(btg_write_path, 'w+') as file:
                json.dump(btg_json, file)

            self.report({'DEBUG'}, f'{btg_json=}')
            self.report({'INFO'}, 'Wrote JSON!')
            return {'FINISHED'}
        except Exception:
            self.report(
                {'ERROR'}, f'Failed to write JSON file with exception:\n{traceback.format_exc()}'
            )
            return {'CANCELLED'}


def register():
    """
    Blender API function
    """
    bpy.utils.register_class(EntityTemplateReader)
    bpy.utils.register_class(EntityImportWriter)

def unregister():
    """
    Blender API function
    """
    bpy.utils.unregister_class(EntityTemplateReader)
    bpy.utils.unregister_class(EntityImportWriter)
