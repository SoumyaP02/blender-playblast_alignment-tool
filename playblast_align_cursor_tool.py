bl_info = {
    "name": "Animation Tools_soumya",
    "author": "Custom",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Anim Tab",
    "description": "Cursor tools and playblast utilities for animation",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

import bpy
import os
from mathutils import Matrix


# =============================================================================
# CURSOR TOOLS OPERATORS
# =============================================================================

class OBJECT_OT_cursor_to_selected_with_rotation(bpy.types.Operator):
    bl_idname = "view3d.cursor_to_selected_with_rotation"
    bl_label = "Cursor to Selected"
    bl_description = "Move 3D Cursor to selected object or bone and match rotation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        if obj.mode == 'POSE':
            bone = context.active_pose_bone
            if bone is None:
                self.report({'WARNING'}, "No active bone selected")
                return {'CANCELLED'}
            # Move cursor to bone head
            context.scene.cursor.location = obj.matrix_world @ bone.head
            context.scene.cursor.rotation_mode = 'QUATERNION'
            context.scene.cursor.rotation_quaternion = obj.matrix_world.to_quaternion() @ bone.matrix.to_quaternion()
        else:
            # Object Mode
            context.scene.cursor.location = obj.location
            context.scene.cursor.rotation_mode = 'QUATERNION'
            context.scene.cursor.rotation_quaternion = obj.matrix_world.to_quaternion()
        
        return {'FINISHED'}


class OBJECT_OT_snap_to_cursor_with_keyframe(bpy.types.Operator):
    bl_idname = "view3d.snap_to_cursor_with_keyframe"
    bl_label = "Snap to Cursor"
    bl_description = "Snap selected object or bone to 3D cursor and insert keyframe at current frame"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        frame = context.scene.frame_current
        cursor_loc = context.scene.cursor.location.copy()
        cursor_rot = context.scene.cursor.rotation_quaternion.copy()
        
        if obj.mode == 'POSE':
            bone = context.active_pose_bone
            if bone is None:
                self.report({'WARNING'}, "No active bone selected")
                return {'CANCELLED'}
            
            # Compute bone matrix in object local space
            parent_matrix_inv = obj.matrix_world.inverted()
            new_matrix = Matrix.Translation(cursor_loc) @ cursor_rot.to_matrix().to_4x4()
            bone.matrix = parent_matrix_inv @ new_matrix
            
            # Insert keyframes at current frame
            bone.keyframe_insert(data_path="location", frame=frame)
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        
        else:
            # Object Mode
            obj.location = cursor_loc
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = cursor_rot
            
            # Insert keyframes at current frame
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        
        return {'FINISHED'}


# =============================================================================
# PLAYBLAST OPERATOR
# =============================================================================

class VIEW3D_OT_playblast(bpy.types.Operator):
    bl_idname = "view3d.playblast"
    bl_label = "Playblast"
    bl_description = "Create a fast viewport playblast"

    def execute(self, context):
        scene = context.scene
        render = scene.render
        playblast_props = scene.playblast_props

        # ---------------------------------------------
        # OUTPUT PATH
        # ---------------------------------------------
        output_dir = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Blender_Playblasts"
        )
        os.makedirs(output_dir, exist_ok=True)
        
        # Use consistent filename with extension to prevent frame numbers
        render.filepath = os.path.join(output_dir, "playblast.mp4")

        # ---------------------------------------------
        # FRAME RANGE
        # ---------------------------------------------
        original_frame_start = scene.frame_start
        original_frame_end = scene.frame_end
        
        if playblast_props.use_custom_range:
            scene.frame_start = playblast_props.frame_start
            scene.frame_end = playblast_props.frame_end

        # ---------------------------------------------
        # RENDER ENGINE (SAFE FOR ALL VERSIONS)
        # ---------------------------------------------
        engine_ids = {
            e.identifier
            for e in bpy.types.RenderSettings
            .bl_rna.properties['engine']
            .enum_items
        }

        if 'BLENDER_EEVEE_NEXT' in engine_ids:
            scene.render.engine = 'BLENDER_EEVEE_NEXT'
        elif 'BLENDER_EEVEE' in engine_ids:
            scene.render.engine = 'BLENDER_EEVEE'
        else:
            scene.render.engine = 'CYCLES'

        # ---------------------------------------------
        # SETTINGS
        # ---------------------------------------------
        render.resolution_percentage = 75
        render.fps = scene.render.fps
        render.use_overwrite = True
        render.use_file_extension = True

        render.image_settings.file_format = 'FFMPEG'
        render.ffmpeg.format = 'MPEG4'
        render.ffmpeg.codec = 'H264'
        render.ffmpeg.constant_rate_factor = 'MEDIUM'
        render.ffmpeg.ffmpeg_preset = 'GOOD'
        render.ffmpeg.audio_codec = 'AAC'
        
        # --------------------------------------------------
        # SPEED OPTIMIZATIONS
        # --------------------------------------------------
        scene.render.use_simplify = True
        scene.render.simplify_subdivision = 0

        if hasattr(scene, "eevee"):
            eevee = scene.eevee
            for attr in ("use_motion_blur", "use_bloom", "use_ssr"):
                if hasattr(eevee, attr):
                    setattr(eevee, attr, False)

        # ---------------------------------------------
        # PLAYBLAST
        # ---------------------------------------------
        bpy.ops.render.opengl(animation=True)

        # Restore original frame range
        scene.frame_start = original_frame_start
        scene.frame_end = original_frame_end

        # ---------------------------------------------
        # AUTO-PLAY VIDEO
        # ---------------------------------------------
        final_output_path = render.filepath + ".mp4"
        
        if playblast_props.auto_play:
            # Use Blender's built-in view animation
            bpy.ops.render.play_rendered_anim()

        self.report({'INFO'}, f"Playblast saved to: {final_output_path}")
        return {'FINISHED'}


# =============================================================================
# PROPERTY GROUP
# =============================================================================

class PlayblastProperties(bpy.types.PropertyGroup):
    auto_play: bpy.props.BoolProperty(
        name="Auto Play",
        description="Automatically play the video after rendering",
        default=True
    )
    
    use_custom_range: bpy.props.BoolProperty(
        name="Use Custom Range",
        description="Render a custom frame range instead of scene range",
        default=False
    )
    
    frame_start: bpy.props.IntProperty(
        name="Start Frame",
        description="First frame to render",
        default=1,
        min=0
    )
    
    frame_end: bpy.props.IntProperty(
        name="End Frame",
        description="Last frame to render",
        default=250,
        min=0
    )


# =============================================================================
# PANELS (ALL IN "ANIM" TAB)
# =============================================================================

class VIEW3D_PT_cursor_tools_panel(bpy.types.Panel):
    bl_label = "Cursor Tools"
    bl_idname = "VIEW3D_PT_cursor_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Anim"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("view3d.cursor_to_selected_with_rotation")
        layout.operator("view3d.snap_to_cursor_with_keyframe")


class VIEW3D_PT_playblast_panel(bpy.types.Panel):
    bl_label = "Playblast"
    bl_idname = "VIEW3D_PT_playblast_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Anim'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        playblast_props = scene.playblast_props

        # Checkboxes in one row
        row = layout.row(align=True)
        row.prop(playblast_props, "auto_play")
        row.prop(playblast_props, "use_custom_range")
        
        # Frame range options
        if playblast_props.use_custom_range:
            col = layout.column(align=True)
            col.prop(playblast_props, "frame_start")
            col.prop(playblast_props, "frame_end")
        else:
            layout.label(text=f"Range: {scene.frame_start} - {scene.frame_end}")
        
        layout.separator()
        
        # Playblast button
        layout.operator(
            VIEW3D_OT_playblast.bl_idname,
            icon='RENDER_ANIMATION',
            text="Create Playblast"
        )


# =============================================================================
# REGISTRATION
# =============================================================================

classes = (
    PlayblastProperties,
    OBJECT_OT_cursor_to_selected_with_rotation,
    OBJECT_OT_snap_to_cursor_with_keyframe,
    VIEW3D_OT_playblast,
    VIEW3D_PT_cursor_tools_panel,
    VIEW3D_PT_playblast_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.playblast_props = bpy.props.PointerProperty(type=PlayblastProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.playblast_props


if __name__ == "__main__":
    register()
