"""
The `bpy.types.Panel` inheriting classes that define the GUI of the addon
"""

import bpy
import numpy as np
from . import entity


class BTGPanel(bpy.types.Panel):
    """
    Settings panel for the Blender to Godot pipeline
    """

    bl_idname = 'OBJECT_PT_btg_panel'
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

        # Import and export UI
        layout.label(text='Import and Export')
        import_export_box = layout.box()
        import_export_box.label(text=scene_props['entity_template_path'].name)
        import_export_box.prop(context.scene, 'entity_template_path', text='')
        import_export_box.operator('json.read')
        import_export_box.label(text=scene_props['btg_write_path'].name)
        import_export_box.prop(context.scene, 'btg_write_path', text='')
        import_export_box.operator('json.write')
        import_export_box.prop(context.scene, 'export_on_save')

        # Search UI
        layout.label(text='Select Objects')
        misc = layout.box()
        misc.operator('select_popup.open')

        # Don't show properties if there is no object selected
        if active_object is None:
            return

        # Entity properties GUI
        layout.label(text='Entity Properties')
        entity_box = layout.box()
        entity_box.label(text='Godot Class')
        entity_box.prop(active_object, 'class_name', text='')
        # Don't show properties if there are none
        class_name = active_object.class_name
        if class_name in ('None', ''):
            return

        # Prevents editing fields of an object with a different class
        for object in context.selected_objects:
            if object.class_name != class_name:
                entity_box.label(text='...')
                return

        # Display class properties
        for property in active_object.class_definition:
            entity_box.label(text=f'{property.name} ({property.godot_type})')
            entity_box.prop(property, property.string_ref, text='')


# This is an operator, but it creates a GUI element, so it fits better here
class SelectionPopup(bpy.types.Operator):
    """
    Search for objects in the scene based on class name or class variable value
    """

    bl_idname = 'select_popup.open'
    bl_label = 'Find objects by...'

    def execute(self, context):
        """
        Use `search_` scene variables to select objects with the specified entity values
        """
        search_class = context.scene.search_class_name

        # Search for matching vars
        if context.scene.search_type == 'var_val' and search_class != 'None':
            search_var_name = context.scene.search_var_name
            search_property = context.scene.search_property

            if search_var_name == '':
                self.report({'WARNING'}, 'No search variable selected.')
                return {'CANCELLED'}

            for object in context.scene.objects:
                if object.class_name != search_class:
                    continue

                value = object.class_definition.get_properties()[search_var_name]['value']
                object.select_set(
                    object.class_name == search_class
                    and SelectionPopup.compare(value, search_property.value, context.scene.comparison_type)
                )
        # Search for matching classes
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
    def close(x: any, y: any, delta: float = 1.0e-8) -> bool:
        """
        Check if vars `x` and `y` are within `delta` distance
        """
        # If string, do regular equality
        if isinstance(x, str) or isinstance(y, str):
            return x == y

        return np.allclose(x, y, atol=delta)

    @staticmethod
    def compare(x: any, y: any, comp_type: str) -> bool:
        """
        Compares inputs `x` and `y` based on `comp_type`

        parameters
        ----------
        `x`, `y`: Inputs to compare
        `comp_type`: Method of comparison. Valid input: `'<', '<=', '==', '>', '>='`

        returns
        -------
        `result`: result of `x` compared to `y` by `comp_type`
        """
        match comp_type:
            case '<':
                return x < y
            case '<=':
                return x <= y
            case '==':
                return SelectionPopup.close(x, y)
            case '>':
                return x > y
            case '>=':
                return x >= y
            case '_':
                return SelectionPopup.close(x, y)

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
            box.prop(context.scene, 'search_var_name', text='')

            search_property = context.scene.search_property
            # Types that we want to show the expanded set of comparison options for
            expanded_compare_types = (
                entity.PropTypes.INT.value,
                entity.PropTypes.FLOAT.value,
            )
            if search_property.string_ref in expanded_compare_types:
                box.prop(context.scene, 'comparison_type', text='')

            box.prop(search_property, search_property.string_ref, text='')


def register():
    """
    Blender API function
    """
    bpy.utils.register_class(BTGPanel)
    bpy.utils.register_class(SelectionPopup)


def unregister():
    """
    Blender API function
    """
    bpy.utils.unregister_class(BTGPanel)
    bpy.utils.unregister_class(SelectionPopup)
