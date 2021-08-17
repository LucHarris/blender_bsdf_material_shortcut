bl_info = {
    "name": "BSDF Shortcut",
    "author": "Luc Harris",
    "version": (0, 0, 1),
    "blender": (2, 93, 0),
    "location": "Propertial > Material > BSDF Setup Shortcut",
    "description": "Loads textures from a directory into a default BSDF material setup.\nAssumes a texture pack is organised into a directory and uses file name postfix convention from textures.com\nMaterial Settings such as blend mode and shadow remain defaulted",
    "doc_url": "",
    "category": "Material",
}

import bpy,os,enum

#### enum ####

# indices for non-image nodes 
class Nodes(enum.IntEnum):    
    # after images
    BSDF    = 0
    MIX     = 1
    BUMP    = 2
    NORM    = 3
    OUTPUT  = 4
    # before images
    COORD   = 5
    MAP     = 6

# indices for image set
class ImageSetID(enum.IntEnum):
    LOOKUP       = 0
    PATH         = 1
    COLOR        = 2
    DEST_INPUT   = 3
    DEST_NODE    = 4


#### functions ####

# looks for existing node or creates new one 
def BsdfNode(nodes, type = "", existingName = "", useExisting = False, x = 0, y = 0):
    node = ( (useExisting and nodes.get(existingName))     or nodes.new(type) )
    node.location = (x,y)
    return node

# sets image data with node properties
def SetImageData(dir):
    # data for images
    imageSet = [
            # 0             # 1      # 2             # 3            # 4
        ['_albedo.',        '',  'sRGB',         'Color1',       Nodes.MIX ],
        ['_ao.',            '',  'Non-Color',    'Color2',       Nodes.MIX ],
        ['_metallic.',      '',  'Non-Color',    'Metallic',     Nodes.BSDF],
        ['_specular.',      '',  'Non-Color',    'Specular',     Nodes.BSDF],
        ['_roughness.',     '',  'Non-Color',    'Roughness',    Nodes.BSDF],
        ['_translucency.',  '',  'sRGB',         'Transmission', Nodes.BSDF],
        ['_emissive.',      '',  'sRGB',         'Emission',     Nodes.BSDF],
        ['_height.',        '',  'Non-Color',    'Height',       Nodes.BUMP],
        ['_normal.',        '',  'Non-Color',    'Color',        Nodes.NORM],
        ['_alpha.',         '',  'Non-Color',    'Alpha',        Nodes.BSDF],
        #### Add more textures here ####
    ]
    
    #
    
    # creates a list of relevant file paths
    if os.path.isdir(dir):                   # validation
        for i in os.listdir(dir):            #  everything in folder folder
            file = dir+i                     #
            if os.path.isfile(file):            # if is file
                for j in imageSet:              # 
                    if j[ImageSetID.LOOKUP] in i:
                        j[ImageSetID.PATH] = i
    
    return imageSet

# adds additional nodes for bsdf material  
def SetBSDFNodes(nodeTree, nodes): 
    # create additional nodes or uses existing nodes
    bsdfNodes = [
        BsdfNode(   nodes,  "ShaderNodeBsdfPrincipled",           'Principled BSDF',     True,   0,    400  ),
        BsdfNode(   nodes,  "ShaderNodeMixRGB",                   "",                    False,  -200, 300  ),
        BsdfNode(   nodes,  "ShaderNodeBump",                     "",                    False,  -180, -180 ),
        BsdfNode(   nodes,  "ShaderNodeNormalMap",                "",                    False,  -280, -400 ),
        BsdfNode(   nodes,  "ShaderNodeOutputMaterial",           "Material Output",     True,    300, 300  ),
        BsdfNode(   nodes,  "ShaderNodeTexCoord",                 "",                    False,  -1000,1    ),
        BsdfNode(   nodes,  "ShaderNodeMapping",                  "",                    False,  -800, 1    ),
    ]

    # set custom properties
    bsdfNodes[Nodes.MIX].blend_type = 'MULTIPLY'
    bsdfNodes[Nodes.MIX].inputs['Fac'].default_value = 1.0
    bsdfNodes[Nodes.MIX].inputs['Color2'].default_value = (1,1,1,1)

    # set links
    nodeTree.links.new(bsdfNodes[Nodes.MIX].outputs['Color'],       bsdfNodes[Nodes.BSDF].inputs['Base Color'] )
    nodeTree.links.new(bsdfNodes[Nodes.NORM].outputs['Normal'],     bsdfNodes[Nodes.BUMP].inputs['Normal'] )
    nodeTree.links.new(bsdfNodes[Nodes.BUMP].outputs['Normal'],     bsdfNodes[Nodes.BSDF].inputs['Normal'] )
    nodeTree.links.new(bsdfNodes[Nodes.COORD].outputs['UV'],        bsdfNodes[Nodes.MAP].inputs['Vector'] )
    nodeTree.links.new(bsdfNodes[Nodes.BSDF].outputs['BSDF'],       bsdfNodes[Nodes.OUTPUT].inputs['Surface'] ) 

    return bsdfNodes

def LoadImageTexturesToNodes(nodeTree,nodes,dir,imageSet, bsdfNodes):
    
    # variables for setting image texture nodes
    x = -600
    y = 500
    inc = -250
    
    # loads textures and applies to an image texture node
    for i in imageSet:
        if len(i[ImageSetID.PATH]):        # validate file is present
            
            node = nodes.new('ShaderNodeTexImage')
            node.location = (x,y)
            node.image = bpy.data.images.load(dir + i[ImageSetID.PATH])
            node.image.colorspace_settings.name = i[ImageSetID.COLOR]
            # liks texture mapping output to image texture input
            nodeTree.links.new( bsdfNodes[Nodes.MAP].outputs['Vector']   , node.inputs['Vector'])
            # links image texture output to destination input
            nodeTree.links.new(node.outputs['Color'],     bsdfNodes[   i[ImageSetID.DEST_NODE]    ].inputs[i[ImageSetID.DEST_INPUT]],)
            # offset position of next iteration
            y += inc;

#### Blender Properties ####

class BsdfShortcutData(bpy.types.PropertyGroup):
    height: bpy.props.FloatProperty(
        name="Some Floating Point", 
        description='Default height strength', 
        default=0.1 )
        
    directory: bpy.props.StringProperty(
        name="Texture Directory",
        description="Directory for textures to be loaded from", 
        default = 'D:\\Textures\\PBR\Barbed Wire\\',
        subtype='DIR_PATH',
        )
    
##### Operator ####

class NODE_OT_bsdf_shortcut(bpy.types.Operator):
    """Adds a new BSDF material with with textures from directory"""
    bl_idname = "node.bsdf_shortcut"
    bl_label = "Add Textured Material From Directory"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # gets directory in panel
        texDir = bpy.context.scene.bsdf_shortcut_data.directory
        
        # creates a new material slot and material 
        mat = bpy.data.materials.new("Material") # or bpy.data.materials.get(mat_name)
        bpy.context.active_object.data.materials.append(mat)
        mat.use_nodes = True
        
        # shortcusts
        nodeTree = mat.node_tree
        nodes = nodeTree.nodes
        
        imageSet = SetImageData(texDir)
        
        bsdfNodes = SetBSDFNodes(nodeTree,nodes)

        LoadImageTexturesToNodes(nodeTree,nodes,texDir,imageSet, bsdfNodes)
       
        return {'FINISHED'}

#### Panel ####

class NODE_PT_bsdf_shortcut(bpy.types.Panel):
    bl_idname = "NODE_PT_bsdf_shortcut"
    bl_label = "BSDF Setup Shortcut"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    #bl_category = "Material Properties"
    
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        row = layout.row()
        row.prop(scene.bsdf_shortcut_data,'directory')
        row = layout.row()
        row.operator("node.bsdf_shortcut")

#### Register ####
 
classes = {
    BsdfShortcutData,
    NODE_OT_bsdf_shortcut,
    NODE_PT_bsdf_shortcut
    } 
    
def register():
    
    for c in classes:
        bpy.utils.register_class(c)
    
    # create property
    bpy.types.Scene.bsdf_shortcut_data = bpy.props.PointerProperty(type=BsdfShortcutData)

def unregister():
    # remove property
    del(bpy.types.Scene.Datablock_Test)
    
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
        
if __name__ == "__main__":
    register()