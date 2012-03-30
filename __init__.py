###############
# __init__.py #
###############

# To support reload properly, try to access a package var, 
# if it's there, reload everything
if "bpy" in locals():
    import imp
    imp.reload(blenderGcode)
    imp.reload(parseGcode)
    print("Reloaded Blender_import_gcode, Gcode_parser")
else:
    from . import Blender_import_gcode as blenderGcode
    from . import Gcode_parser as parseGcode
    print("Imported Blender_import_gcode, Gcode_parser")

import bpy 

from bpy.props import StringProperty


bl_info = {
    'name': 'Import GCode',
    'author': 'Simon Kirkby',
    'version': (0,0,7),
    'blender': (2, 6, 2),
    'api': 45241,
    'location': 'File > Import-Export > Gcode',
    'description': 'Import and visualize gcode files generated for 3D printers (.gcode)',
    "wiki_url": "",
    "tracker_url": "",
    'category': 'Import-Export'}

__version__ = '.'.join([str(s) for s in bl_info['version']])

# gcode parser for blender 2.5 
# Simon Kirkby
# 201102051305
# tigger@interthingy.com 

#modified by David Anderson to handle Skeinforge comments
# Thanks Simon!!!

# modified by Alessandro Ranellucci (2011-10-14)
# to make it compatible with Blender 2.59
# and with modern 5D GCODE

# Modified by Winter Guerra (XtremD) on February 16th, 2012
# to make the script compatable with stock Makerbot GCode files
# and grab all nozzle extrusion information from Skeinforge's machine output
# WARNING: This script no longer works with stock 5D GCode! (Can somebody please integrate the two versions together?)
# A big shout-out goes to my friend Jon Spyreas for helping me block-out the maths needed in the "addArc" subroutine
# Thanks a million dude!
# Github branch link: https://github.com/xtremd/blender-gcode-reader

# modified by Douwe van der Veen (appultaart) in March, 2012
# to make the script compatible with Ultimaker Gcode files generated
# from Slic3r. Also, overhaul of the script to separate the Gcode reader
# part from the Blender drawing part: converted to multi-files addon.
# Thanks to Jelle Boomstra for suggestions, advice, help.


class IMPORT_OT_gcode(bpy.types.Operator):
    '''Imports gcode used by 3D printers such as Reprap, Makerbot, Ultimaker'''
    bl_idname = "import_scene.gcode"
    bl_description = 'Gcode reader, reads tool moves and animates layers build'
    bl_label = "Import gcode" +' v.'+ __version__
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"

    filepath = StringProperty(name="File Path", 
                            description="Filepath used for importing the GCode file", 
                            maxlen= 1024, 
                            default= "")

    ##### DRAW #####
    def draw(self, context):
        layout0 = self.layout
         
    def execute(self, context):
#        global toggle, theMergeLimit, theCodec, theCircleRes

        # do the things needed to build a file
        myMachine = parseGcode.Machine()
        print("OK: initiated Machine:", myMachine)

        myMachine.add_extruder(self.filepath)
        print("OK: add extruder to current machine.")

        myGcodes = myMachine.extruders[-1].standardGcode
        print("OK: Gcode commands are fetched from the current extruder.")


    # The gcodeData object is a dictionary that stores gcodeCurveData objects.
    # Each gcodeCurveData object has the name of the 'Z' value, and in this 
    # object all the commands with that 'Z' value are stored.
        mygcodeCurveDatas = blenderGcode.sort_commands_to_layers(myGcodes)                    # input is list, returns dict
        layerNames = sorted(blenderGcode.gcodeCurveData._registry)
        print("Layer names are:", layerNames)

    # For every layer (i.e., every gcodeCurveData object), walk through the 
    # commands and convert to splines. For Blender, every layer (= Z-value) 
    # stores one BezierCurve object. This curve can have multiple splines.
        for layer in mygcodeCurveDatas.values():
            layer.create_splines()
            print(layer)

    # There might well be layers with commands but without splines. We will
    # remove these, as they will clutter the code (NB such spline-less layers
    # are normally the result of a repositioning command like G92)
        noSplineInLayer = list()
        for layer in layerNames:
            if mygcodeCurveDatas[layer].count_splines() == 0:                           # no splines are present
                noSplineInLayer.append(mygcodeCurveDatas.pop(layer))                    # pop the layer with 0 splines
                blenderGcode.gcodeCurveData._registry.remove(layer)                                  # remove Z-value from registry
        print("These layers were removed as they contain no splines:", noSplineInLayer)

        # Hack to reselect the layernames: layers with 0 curves are removed, so we need to update
        layerNames = sorted(blenderGcode.gcodeCurveData._registry)
    
        # let's start drawing in Blender!
        # First, make a bevel object in case we'd like to use one
        bev = blenderGcode.make_bevel_object()                                                   # make a bevel object
        
        # Draw the curves to our scene
        blenderGcode.draw_blenderBeziers(mygcodeCurveDatas)                                          # no bevel object
    #    draw_blenderBeziers(mygcodeCurveDatas, bev)                                    # with bevel object    
    
        # animate the curves
        blenderGcode.animate_blenderBeziers(layerNames)
    
#### 

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}




def menu_func(self, context):
    self.layout.operator(IMPORT_OT_gcode.bl_idname, text="3D printer GCode (.gcode)", icon='PLUGIN')

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func)
 
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func)

if __name__ == "__main__":
    register()
