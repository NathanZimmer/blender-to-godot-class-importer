"""
`bpy.types.Operator` inheriting classes
"""

import bpy
import json
import traceback
from pathlib import Path
# import shutil
from . import utilities


class EntityTemplateReader(bpy.types.Operator):
    """
    Read Godot entity template JSON and refresh object entity definitions
    """

    bl_idname = 'json.read'
    bl_label = 'Read entity template'

    def execute(self, context):
        """
        Read entity template from JSON and initialize values for all scene objects
        """
        try:
            self.read_template_json()
        except Exception:
            self.report({'ERROR'}, f'Failed to load JSON file with exception:\n{traceback.format_exc()}')
            return {'CANCELLED'}

        # Clear old defs and refresh updated defs
        utilities.refresh_class_definitions()

        self.report({'DEBUG'}, f'{context.scene.entity_template=}')
        self.report({'INFO'}, 'Loaded JSON!')
        return {'FINISHED'}

    @staticmethod
    def read_template_json() -> None:
        """
        Read json from `scene.entity_template_path` into `scene.entity_template`
        """
        entity_template_path = bpy.context.scene.entity_template_path
        if entity_template_path[:2] == '//':
            entity_template_path = bpy.path.abspath('//') + entity_template_path[2:]
        with open(entity_template_path) as entity_json:
            # Place 'None' at the first index for defaulting
            bpy.context.scene.entity_template.reset({'None': ''} | json.load(entity_json))


class EntityImportWriter(bpy.types.Operator):
    """
    Write import JSON from object entity defintions
    """

    bl_idname = 'json.write'
    bl_label = 'Write entity definition'

    def execute(self, context):
        """
        Write entity definitions import JSON used by Godot
        """

        # Construct JSON
        btg_json = {
            # Convert to Godot naming standards
            object.name.replace('.', '_'): {
                'class': object.class_name,
                'uid': context.scene.entity_template[object.class_name].get('uid', ''),
                'variables': {
                    prop.name: {
                        'type': prop.godot_type,
                        'value': utilities.to_json_type(prop),
                    }
                    for prop in object.class_definition
                },
            }
            for object in context.scene.objects
            if object.class_name != 'None'
        }

        # Write JSON
        try:
            if bpy.context.scene.btg_write_path[:2] == '//':
                btg_write_path = Path(bpy.path.abspath('//') + bpy.context.scene.btg_write_path[2:])
            else:
                btg_write_path = Path(bpy.context.scene.btg_write_path)

            # if btg_write_path.exists():
            #     shutil.copy(btg_write_path, btg_write_path.as_posix() + '1')

            with btg_write_path.open('w+') as file:
                json.dump(btg_json, file, indent=4)

            self.report({'DEBUG'}, f'{btg_json=}')
            self.report({'INFO'}, 'Wrote JSON!')
            return {'FINISHED'}
        except Exception:
            self.report({'ERROR'}, f'Failed to write JSON file with exception:\n{traceback.format_exc()}')
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
