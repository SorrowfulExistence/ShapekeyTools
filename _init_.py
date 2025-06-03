bl_info = {
    "name": "Shapekey Tools",
    "author": "SorrowfulExistence",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Mesh Data > Shape Keys",
    "description": "various tools for working with shape keys",
    "category": "Mesh",
}
#don't worry about library warning on your environment, it works based on Blender so it can't be easily tested on solely an IDE
import bpy
from mathutils import Vector

class MESH_OT_select_shapekey_vertices(bpy.types.Operator):
    """Select all vertices affected by the active shape key"""
    bl_idname = "mesh.select_shapekey_vertices"
    bl_label = "Select Affected Vertices"
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        description="Minimum distance a vertex must move to be selected",
        default=0.0001,
        min=0.0,
        soft_max=0.1,
        precision=5
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and 
                obj.data.shape_keys and 
                obj.active_shape_key_index > 0)  #basis is index 0
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        #get the active shape key
        shape_keys = mesh.shape_keys
        active_key = obj.active_shape_key
        basis = shape_keys.reference_key
        
        #make sure we're in object mode to access mesh data
        mode = obj.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #deselect all vertices first
        for v in mesh.vertices:
            v.select = False
        
        #compare each vertex position between basis and active shapekey
        affected_count = 0
        for i, vert in enumerate(mesh.vertices):
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            
            #check if vertex has moved beyond threshold
            if (shape_co - basis_co).length > self.threshold:
                vert.select = True
                affected_count += 1
        
        #update the mesh
        mesh.update()
        
        #switch to edit mode and vertex selection mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        
        self.report({'INFO'}, f"Selected {affected_count} affected vertices")
        return {'FINISHED'}


class MESH_OT_select_shapekey_faces(bpy.types.Operator):
    """Select all faces affected by the active shape key"""
    bl_idname = "mesh.select_shapekey_faces"
    bl_label = "Select Affected Faces"
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        description="Minimum distance a vertex must move to affect its faces",
        default=0.0001,
        min=0.0,
        soft_max=0.1,
        precision=5
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and 
                obj.data.shape_keys and 
                obj.active_shape_key_index > 0)
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        #get the active shape key
        shape_keys = mesh.shape_keys
        active_key = obj.active_shape_key
        basis = shape_keys.reference_key
        
        #make sure we're in object mode
        mode = obj.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #first find all affected vertices
        affected_verts = set()
        for i, vert in enumerate(mesh.vertices):
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            
            if (shape_co - basis_co).length > self.threshold:
                affected_verts.add(i)
        
        #deselect all faces first
        for f in mesh.polygons:
            f.select = False
        
        #select faces that contain any affected vertices
        affected_count = 0
        for face in mesh.polygons:
            for vert_idx in face.vertices:
                if vert_idx in affected_verts:
                    face.select = True
                    affected_count += 1
                    break  #no need to check other verts in this face
        
        #update the mesh
        mesh.update()
        
        #switch to edit mode and face selection mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        
        self.report({'INFO'}, f"Selected {affected_count} affected faces")
        return {'FINISHED'}


class MESH_OT_blend_shapekey_from_vgroup(bpy.types.Operator):
    """Blend shape key influence based on vertex group weights"""
    bl_idname = "mesh.blend_shapekey_from_vgroup"
    bl_label = "Blend from Vertex Group"
    bl_options = {'REGISTER', 'UNDO'}
    
    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex group to use for blending"
    ) # type: ignore
    
    invert: bpy.props.BoolProperty(
        name="Invert",
        description="Invert the vertex group influence",
        default=False
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and 
                obj.data.shape_keys and 
                obj.active_shape_key_index > 0 and
                len(obj.vertex_groups) > 0)
    
    def invoke(self, context, event):
        #get the vertex group from window manager property
        if hasattr(context.window_manager, 'shapekey_tools_vgroup'):
            self.vertex_group = context.window_manager.shapekey_tools_vgroup
        if hasattr(context.window_manager, 'shapekey_tools_vgroup_invert'):
            self.invert = context.window_manager.shapekey_tools_vgroup_invert
        return self.execute(context)
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        #get vertex group
        vgroup = obj.vertex_groups.get(self.vertex_group)
        if not vgroup:
            self.report({'ERROR'}, f"Vertex group '{self.vertex_group}' not found")
            return {'CANCELLED'}
        
        #get shape keys
        shape_keys = mesh.shape_keys
        active_key = obj.active_shape_key
        basis = shape_keys.reference_key
        
        #store current mode and switch to object mode
        mode = obj.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #blend each vertex based on vertex group weight
        for i, vert in enumerate(mesh.vertices):
            #get weight for this vertex
            weight = 0.0
            for g in vert.groups:
                if g.group == vgroup.index:
                    weight = g.weight
                    break
            
            #invert if needed
            if self.invert:
                weight = 1.0 - weight
            
            #blend between basis and shape key position
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            
            #interpolate position based on weight
            active_key.data[i].co = basis_co.lerp(shape_co, weight)
        
        #update mesh
        mesh.update()
        
        #restore mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        
        self.report({'INFO'}, f"Blended shape key '{active_key.name}' using vertex group '{vgroup.name}'")
        return {'FINISHED'}


class MESH_OT_blend_to_basis_by_distance(bpy.types.Operator):
    """Clean up shape keys by resetting vertices with minimal movement to basis. Can be used iteratively - each use recalculates and cleans the specified percentage of remaining moving vertices"""
    bl_idname = "mesh.blend_to_basis_by_distance"
    bl_label = "Clean Up Small Movements"
    bl_options = {'REGISTER', 'UNDO'}
    
    percentage: bpy.props.FloatProperty(
        name="Percentage",
        description="Percentage of least-moved vertices to reset to basis",
        default=10.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE'
    ) # type: ignore
    
    threshold_mode: bpy.props.EnumProperty(
        name="Mode",
        description="How to determine which vertices to clean up",
        items=[
            ('PERCENTAGE', "Percentage", "Clean up bottom X% of vertices by movement"),
            ('THRESHOLD', "Threshold", "Clean up all vertices that move less than threshold"),
        ],
        default='PERCENTAGE'
    ) # type: ignore
    
    distance_threshold: bpy.props.FloatProperty(
        name="Distance Threshold",
        description="Maximum distance for cleanup (when using Threshold mode)",
        default=0.001,
        min=0.0,
        soft_max=0.1,
        precision=5
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and 
                obj.data.shape_keys and 
                obj.active_shape_key_index > 0)
    
    def invoke(self, context, event):
        #get settings from window manager properties
        wm = context.window_manager
        if hasattr(wm, 'shapekey_tools_cleanup_mode'):
            self.threshold_mode = wm.shapekey_tools_cleanup_mode
        if hasattr(wm, 'shapekey_tools_cleanup_percentage'):
            self.percentage = wm.shapekey_tools_cleanup_percentage
        if hasattr(wm, 'shapekey_tools_cleanup_threshold'):
            self.distance_threshold = wm.shapekey_tools_cleanup_threshold
        return self.execute(context)
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        #get shape keys
        shape_keys = mesh.shape_keys
        active_key = obj.active_shape_key
        basis = shape_keys.reference_key
        
        #store mode and switch to object
        mode = obj.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #calculate distances for all vertices and create sorted list
        vertex_distances = []
        
        for i in range(len(mesh.vertices)):
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            dist = (shape_co - basis_co).length
            #only include vertices that actually move (not already at basis)
            if dist > 0.0:
                vertex_distances.append((i, dist))
        
        #check if there's anything to clean
        if not vertex_distances:
            self.report({'INFO'}, "No vertices to clean - all are at basis")
            return {'FINISHED'}
        
        #sort by distance (ascending - least movement first)
        vertex_distances.sort(key=lambda x: x[1])
        
        #determine which vertices to reset
        vertices_to_reset = []
        
        if self.threshold_mode == 'PERCENTAGE':
            #calculate how many vertices to reset based on percentage of moving vertices
            num_to_reset = int(len(vertex_distances) * (self.percentage / 100.0))
            vertices_to_reset = [v[0] for v in vertex_distances[:num_to_reset]]
        else:  #THRESHOLD mode
            #reset all vertices that move less than threshold
            vertices_to_reset = [v[0] for v in vertex_distances if v[1] <= self.distance_threshold]
        
        #reset selected vertices to basis
        reset_count = 0
        for vert_idx in vertices_to_reset:
            basis_co = basis.data[vert_idx].co
            active_key.data[vert_idx].co = basis_co.copy()
            reset_count += 1
        
        #update mesh
        mesh.update()
        
        #restore mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        
        #calculate remaining moving vertices for feedback
        remaining_moving = len(vertex_distances) - reset_count
        
        if self.threshold_mode == 'PERCENTAGE':
            self.report({'INFO'}, f"Reset {reset_count} vertices ({self.percentage}% of {len(vertex_distances)} moving) - {remaining_moving} still moving")
        else:
            self.report({'INFO'}, f"Reset {reset_count} vertices moving less than {self.distance_threshold} - {remaining_moving} still moving")
        return {'FINISHED'}


class MESH_PT_shapekey_tools_panel(bpy.types.Panel):
    """Panel for shape key tools"""
    bl_label = "Shape Key Tools"
    bl_idname = "MESH_PT_shapekey_tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.data.shape_keys
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        #only show tools if we have an active non-basis shape key
        if obj.active_shape_key_index > 0:
            col = layout.column(align=True)
            
            #selection tools
            col.label(text="Selection:")
            col.operator("mesh.select_shapekey_vertices", icon='VERTEXSEL')
            col.operator("mesh.select_shapekey_faces", icon='FACESEL')
            
            col.separator()
            
            #blending tools
            col.label(text="Blending:")
            
            #vertex group blend
            if len(obj.vertex_groups) > 0:
                #add vertex group selector in the ui
                col.prop_search(
                    context.window_manager, "shapekey_tools_vgroup",
                    obj, "vertex_groups",
                    text="Vertex Group"
                )
                col.prop(context.window_manager, "shapekey_tools_vgroup_invert", text="Invert")
                row = col.row(align=True)
                row.operator("mesh.blend_shapekey_from_vgroup", icon='GROUP_VERTEX')
            else:
                col.label(text="No vertex groups", icon='INFO')
            
            col.separator()
            
            #cleanup tool (formerly distance-based blend)
            col.label(text="Cleanup:")
            col.prop(context.window_manager, "shapekey_tools_cleanup_mode", text="")
            
            if context.window_manager.shapekey_tools_cleanup_mode == 'PERCENTAGE':
                col.prop(context.window_manager, "shapekey_tools_cleanup_percentage")
            else:
                col.prop(context.window_manager, "shapekey_tools_cleanup_threshold")
            
            col.operator("mesh.blend_to_basis_by_distance", icon='BRUSH_DATA')
            
        else:
            layout.label(text="Select a shape key (not Basis)")


#property for vertex group selection in ui
def register_props():
    bpy.types.WindowManager.shapekey_tools_vgroup = bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex group for shape key blending"
    ) # type: ignore
    bpy.types.WindowManager.shapekey_tools_vgroup_invert = bpy.props.BoolProperty(
        name="Invert",
        description="Invert the vertex group influence",
        default=False
    ) # type: ignore
    bpy.types.WindowManager.shapekey_tools_cleanup_mode = bpy.props.EnumProperty(
        name="Mode",
        description="How to determine which vertices to clean up",
        items=[
            ('PERCENTAGE', "Percentage", "Clean up bottom X% of vertices by movement"),
            ('THRESHOLD', "Threshold", "Clean up all vertices that move less than threshold"),
        ],
        default='PERCENTAGE'
    ) # type: ignore
    bpy.types.WindowManager.shapekey_tools_cleanup_percentage = bpy.props.FloatProperty(
        name="Percentage",
        description="Percentage of least-moved vertices to reset to basis",
        default=10.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE'
    ) # type: ignore
    bpy.types.WindowManager.shapekey_tools_cleanup_threshold = bpy.props.FloatProperty(
        name="Distance Threshold",
        description="Maximum distance for cleanup",
        default=0.001,
        min=0.0,
        soft_max=0.1,
        precision=5
    ) # type: ignore


def unregister_props():
    del bpy.types.WindowManager.shapekey_tools_vgroup
    del bpy.types.WindowManager.shapekey_tools_vgroup_invert
    del bpy.types.WindowManager.shapekey_tools_cleanup_mode
    del bpy.types.WindowManager.shapekey_tools_cleanup_percentage
    del bpy.types.WindowManager.shapekey_tools_cleanup_threshold


classes = (
    MESH_OT_select_shapekey_vertices,
    MESH_OT_select_shapekey_faces,
    MESH_OT_blend_shapekey_from_vgroup,
    MESH_OT_blend_to_basis_by_distance,
    MESH_PT_shapekey_tools_panel,
)


def register():
    register_props()
    
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    unregister_props()


if __name__ == "__main__":
    register()