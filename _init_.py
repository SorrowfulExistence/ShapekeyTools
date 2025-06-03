bl_info = {
    "name": "Shapekey Tools",
    "author": "SorrowfulExistence",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "properties > mesh data > shape keys",
    "description": "various tools for working with shape keys",
    "category": "Mesh",
}

#if it gives a warning in your IDE, it's because the libraries are in Blender, it should be fine
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
        
        #restore previous mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        
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
        
        #restore previous mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        
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
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        #get vertex group
        vgroup = obj.vertex_groups.get(self.vertex_group)
        if not vgroup:
            self.report({'ERROR'}, "Vertex group not found")
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
    """Blend vertices back to basis based on how far they've moved"""
    bl_idname = "mesh.blend_to_basis_by_distance"
    bl_label = "Blend to Basis by Distance"
    bl_options = {'REGISTER', 'UNDO'}
    
    percentage: bpy.props.FloatProperty(
        name="Percentage",
        description="How much to blend back to basis (0=no change, 100=full basis)",
        default=50.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE'
    ) # type: ignore
    
    distance_mode: bpy.props.EnumProperty(
        name="Distance Mode",
        description="How to calculate blend amount based on distance",
        items=[
            ('LINEAR', "Linear", "Vertices that moved more blend more"),
            ('INVERSE', "Inverse", "Vertices that moved less blend more"),
        ],
        default='LINEAR'
    ) # type: ignore
    
    normalize_distance: bpy.props.BoolProperty(
        name="Normalize Distance",
        description="Normalize distances so the furthest vertex gets full blend",
        default=True
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
        
        #get shape keys
        shape_keys = mesh.shape_keys
        active_key = obj.active_shape_key
        basis = shape_keys.reference_key
        
        #store mode and switch to object
        mode = obj.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #calculate distances for all vertices
        distances = []
        max_dist = 0.0
        
        for i in range(len(mesh.vertices)):
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            dist = (shape_co - basis_co).length
            distances.append(dist)
            max_dist = max(max_dist, dist)
        
        #avoid division by zero
        if max_dist == 0:
            self.report({'WARNING'}, "No vertices have moved from basis")
            return {'CANCELLED'}
        
        #blend each vertex
        factor = self.percentage / 100.0
        
        for i, vert in enumerate(mesh.vertices):
            dist = distances[i]
            
            #calculate blend weight based on distance
            if self.normalize_distance and max_dist > 0:
                normalized_dist = dist / max_dist
            else:
                normalized_dist = dist
            
            if self.distance_mode == 'LINEAR':
                blend_weight = normalized_dist * factor
            else:  #INVERSE
                blend_weight = (1.0 - normalized_dist) * factor
            
            #blend position
            basis_co = basis.data[i].co
            shape_co = active_key.data[i].co
            active_key.data[i].co = shape_co.lerp(basis_co, blend_weight)
        
        #update mesh
        mesh.update()
        
        #restore mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        
        self.report({'INFO'}, f"Blended vertices to basis by {self.percentage}%")
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
                row = col.row(align=True)
                op = row.operator("mesh.blend_shapekey_from_vgroup", icon='GROUP_VERTEX')
                
                #add vertex group selector in the ui
                col.prop_search(
                    context.window_manager, "shapekey_tools_vgroup",
                    obj, "vertex_groups",
                    text="Vertex Group"
                )
            else:
                col.label(text="No vertex groups", icon='INFO')
            
            col.separator()
            
            #distance-based blend
            col.operator("mesh.blend_to_basis_by_distance", icon='ARROW_LEFTRIGHT')
            
        else:
            layout.label(text="Select a shape key (not Basis)")


#property for vertex group selection in ui
def register_props():
    bpy.types.WindowManager.shapekey_tools_vgroup = bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex group for shape key blending"
    )


def unregister_props():
    del bpy.types.WindowManager.shapekey_tools_vgroup


#update vertex group blend operator when ui property changes
def vgroup_update(self, context):
    return None


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
    
    #make vertex group operator use the ui property
    def draw_func(self, context):
        if hasattr(context.window_manager, 'shapekey_tools_vgroup'):
            self.vertex_group = context.window_manager.shapekey_tools_vgroup
    
    MESH_OT_blend_shapekey_from_vgroup.draw = draw_func


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    unregister_props()


if __name__ == "__main__":
    register()