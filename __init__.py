###############
# __init__.py #
###############

"""
# gcode parser for blender 2.5 
# Simon Kirkby
# 201102051305
# tigger@interthingy.com 

# modified by David Anderson to handle Skeinforge comments
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

"""

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

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty


bl_info = {
    'name': 'DOUWE Import GCode',
    'author': 'Douwe tests this',       #'Simon Kirkby',
    'version': (0,0,7),
    'blender': (2, 6, 2),
    'api': 45822,
    'location': 'File > Import-Export > Gcode',
    'description': 'Import and visualize gcode files generated for 3D printers (.gcode)',
    'category': 'Import-Export'}

__version__ = '.'.join([str(s) for s in bl_info['version']])


# ---------------------------------------------
class IMPORT_OT_gcode(bpy.types.Operator, ImportHelper):
    """Class to open the File Selector to select a .gcode file
    """
    bl_idname= "import_scene.import_gcode"
    bl_description = 'Use the File Selector to import a .gcode file'
    bl_label = "Import GcodeZ"
    filename_ext = ".gcode"
    filter_glob = StringProperty(default="*.gcode", options={'HIDDEN'})    
    filepath= StringProperty(name="File Path", description="Filepath used for importing the .gcode file", maxlen=1024, default="")
    
    def execute(self, context): 
## ADD FUNCTIONAL STUFF HERE
        # Initiate a virtual 3D printing machine
        myMachine = parseGcode.Machine()
        print("OK: initiated Machine:", myMachine)

        # Import the .gcode file and add as an extruder
        myMachine.add_extruder(self.filepath)
        print("OK: add extruder to current machine.")

        # select the extruder we'd like to draw
        extruderToDraw = myMachine.extruders[-1]

        # Get the extruder we'd like to draw, and transfer that data to a gcodeCurvesData object
        myGcodeCurvesData = blenderGcode.gcodeCurvesData(extruderToDraw)

        # Sort the Gcode commands by Z-value, and create 'gcodeCurve' instance for every Z value
        myGcodeCurvesData.add_gcode_to_gcodeCurves()

        # Obtain a sorted list of all the names of the layers, i.e., all Z values.
        Z_layerNames = sorted(blenderGcode.gcodeCurve._registry)

        # Create splines data
        for Zval in Z_layerNames:
            myGcodeCurvesData.gcodeCurves[Zval].create_splines_data()

        # There might well be layers with commands but without splines. We will
        # remove these, as they will clutter the code (NB such spline-less layers
        # are normally the result of a repositioning command like G92)
        noSplineInLayer = list()
        for layer in Z_layerNames:
            if myGcodeCurvesData.gcodeCurves[layer].count_splines() == 0:                           # no splines are present
                noSplineInLayer.append(myGcodeCurvesData.gcodeCurves.pop(layer))                    # pop the layer with 0 splines
                blenderGcode.gcodeCurve._registry.remove(layer)
        print("These layers were removed as they contain no splines:", noSplineInLayer)
    
        # Hack to reselect the Z_layerNames: layers with 0 curves are removed, so we need to update
        Z_layerNames = sorted(blenderGcode.gcodeCurve._registry)
    
        # let's start drawing in Blender!
        # First, make a bevel object in case we'd like to use one
        myGcodeCurvesData.create_bevel_object()

        myGcodeCurvesData.draw_blender_bezier_curves(use_bevel = bpy.context.scene.use_bevel)
 
 ## END FUNCTIONAL STUFF
        return {'FINISHED'}


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class OBJECT_OT_CloseGcodePanelButton(bpy.types.Operator):
    """Class for a button that can close the .gcode import panel
    """
    bl_idname = "import_scene.close_panel"
    bl_label = "Close this Gcode panel"
    
    def execute(self, context):
        print("Now in the ClosePanelButton execute function...")
        bpy.types.INFO_MT_file_import.remove(menu_func)
        bpy.utils.unregister_module(__name__)
        return {'FINISHED'}


class GcodeToolPropertiesPanel(bpy.types.Panel):
    """Class that creates a .gcode import panel inside the Tool Properties panel.
    """
    bl_label = "Panel: Import .gcode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"

    def draw(self, context):
        self.layout.operator("import_scene.import_gcode", text='Import a .gcode file')
        self.layout.prop(context.scene, "use_bevel") 
        self.layout.operator("import_scene.close_panel", text = 'Close this panel')
# ----------------------------        

bpy.types.Scene.use_bevel = BoolProperty(name = "Use Bevel", 
                                         description = "Whether or not to use a bevel object",
                                         default = False)



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
