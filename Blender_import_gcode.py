#! /usr/bin/env python3 

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
Blender Gcode-reader and visualization.

This script takes a Gcode file, and parses the file to the very crude and basic 'gcode-parser'.
The output of that are standardized 'gcodeCommand' instances. This script will
process these commands into Beziercurves for use inside Blender.

Both the 'Gcode_parser.py' file and this file are based upon the 'blender-gcode-reader' 
addon code base by:

Original author: Simon Kirkby ('zignig'): https://github.com/zignig/blender-gcode-reader
Modifications: Alessandro Ranellucci ('alexjr'): https://github.com/alexrj/blender-gcode-reader
Modifications: Winter Guerra ('xtremd') : https://github.com/xtremd/blender-gcode-reader

Current modifications: Douwe van der Veen ('appultaart'): https://github.com/appultaart/blender-gcode-reader

Primary reason for this rewrite of the already written code add-on:
    1. I couldn't fine a Gcode parser written in Python/Python3
    2. Our present need to merge two G-code files (generated from different .stl files);
    3. Code must be working with our Ultimaker machines, and use 5D-coordinates (x,y,z,e,f)
       in a more structured order (Object-based)
    4. Code must accept Slic3r-generated gcode, not only Skeinforge... (Ideally: be Gcode-agnostic)
    5. (Ideally, this code should serve as a library for later work, but that's for later, if it happens at all....)
    6. Separate the Gcode parser from the Blender code parts--> so we can use both
       independently, or put output to different programs.

TODO:   -put back the nice blender-code that registers it as an add-on and is user-friendly;
        -skeinforge and Makerbot stock gcode cannot be confirmed to work well for now, 
            needs to be tested (test file!?)
        - as the dE values are used (deltaE: difference between E points between
            two Gcode commands), the ugly hack with the M101/M103 codes must
            be worked out. Best is to implement a 'yield' function that returns
            incremental E-values if no E-values are given?
"""

# ----- imports -----
import sys
# add the path where 'gcode-parser.py' is
# TODO make this hack a bit more like it should (i.e., check Blender guidelines)

sys.path.append("/media/data_disk/fablab_utrecht/source/blender-gcode-reader/douwe")
# reload the GcodeParser_Python module. This is done to ensure that any
# modifications applied to these files are processed (i.e., force reloading)
try:
    del sys.modules['Gcode_parser']
    import Gcode_parser as Gcode
except KeyError:
    # the module is not loaded yet, we can ignore the KeyError and import directly
    import Gcode_parser as Gcode


import bpy


# ----- class definitions -----
class gcodeLayer:
    """Store gcodeCommands with the same Z-value. 
    
    gcodeCommands are scanned for their Z-value, and gcodeCommands with the 
    same Z-value are places in tyhe same 'gcodeLayer' member.
    
    These gcodeCommands are then processed to generate splines.
    (In Blender, a 'Beziercurve' object can have multiple 'splines'. Each spline
    stores a series of points that are connected by a line).

    Variables:
        gcodeLayer._registry    :   list to keep track of the layers' names used
        gcodeLayer.name         :   the name of the instance. The 'Z-value' is a good one to use
        gcodeLayer.commands     :   a list of all the gcodeCommand instances with 
                                    the same Z-value
        gcodeLayer.splines      :   a list of lists. Each list stores a spline,
                                    that are those points that are connected by
                                    a line. 
    """

    # Keep a registry of the current layers that we have made, so we don't 
    # overwrite layers by accident.
    # NOTE that because of the 'G92' code (reset position) command, strange
    #       bezier curves could be generated.
    _registry = list()
    
    def __init__(self, name):
        """Initialization of a 'gcodeLayer' instance. The <name> argument normally is the Z-value.
        """
        self._registry.append(name)                                             # bookkeeping
        self.name = name                                                        # default: Z-value
        self.commands = list()                                                  # all 'gcodeCommand' instances with the same Z value
        self.splines = list()                                                   # list of lists with spline points

    def __repr__(self):
        """return a representation of the 'layer' instance"""
        return "<layer '{0}': {1} commands, {2} splines>".format(self.name, len(self.commands), len(self.splines))

    def count_splines(self):
        """Returns the amount of splines in this gcodeLayer instance"""
        return len(self.splines)
    
    def count_spline_length(self, indexNr):
        """Returns the length of the spline with given indexNR"""
        return len(self.splines[indexNr])
        
    def add_command(self, point):
        """Add a gcodeCommand to the list of gcodeCommands of an existing spline"""
        self.commands.append(point)

    def create_splines(self):
        """Create splines from Gcode commands with identical Z value.
        """
        lastSplinePoint = self.commands[0]                                      # first point
        self.splines.append([lastSplinePoint])                                  # create list containing first point of the first spline
        
        for indexNr in range(1, len(self.commands)):                            # process the other gcode points in this layer
            currSplinePoint = self.commands[indexNr]
            
            delta = (currSplinePoint.parameters["X"] - lastSplinePoint.parameters["X"], 
                     currSplinePoint.parameters["Y"] - lastSplinePoint.parameters["Y"],
                     currSplinePoint.parameters["Z"] - lastSplinePoint.parameters["Z"],
                     currSplinePoint.parameters["E"] - lastSplinePoint.parameters["E"],
                     currSplinePoint.parameters["F"] - lastSplinePoint.parameters["F"])
            
            if delta[0] != 0.0 or delta[1] != 0:                                # X and/or Y coordinates differ --> movement
                if delta[3] > 0.0:                                              # E-value changed: plastic is extruded
                    self.splines[-1].append(currSplinePoint)                    # take the last spline we're working on, and append to it
                    lastSplinePoint = currSplinePoint
                elif delta[3] <= 0.0:                                           # E-value is not changed, or plastic is retracted
                    self.splines.append([currSplinePoint])                      # add to the list of splines, a new spline
                    lastSplinePoint = currSplinePoint

            else:
                # no movement in X and Y directions. We don't care what happens for now
                # might become useful later, when dE- or dF-value information is used
                pass


        # For drawing stuff, we are only interested in splines with 2 or more commands.
        # Hence, remove all the splines with length of 1, i.e. that contain only one command        
        tempSplines = list()
        for indexNr in range(len(self.splines)):

            if len(self.splines[indexNr]) >= 2:
                tempSplines.append(self.splines[indexNr])

        self.splines = tempSplines[:]
                
 


# ----- functions -----
def sort_commands_to_layers(listOfGcodeCommands):
    """Place gcode commands into a gcodeLayer object, based on their Z-value.
    
    listOfGcodeCommands:    list.
                            This list stores processed Gcode code, one command at 
                            a time. Each item in the list is a 'gcodeCommand' instance.
    
    return: dict (containing gcodeLayer instances)
    """
    
    layersData = dict()                                                         # store the gcodeLayer instances in here
    
    for cmd in listOfGcodeCommands:
        # process only the commands that contain useful position information
        if cmd.command not in ("comment", "skeinforge", "unknown"):
            zValue = cmd.parameters["Z"]

            if zValue in gcodeLayer._registry:                                  # Check if there is a gcodeLayer object with the 'Z' value:
                layersData[zValue].add_command(cmd)
                
            else:                                                               # No gcodeLayer object with this Z value
                layersData[zValue] = gcodeLayer(name=zValue)                    # create gcodeLayer instance and add to stack
                layersData[zValue].add_command(cmd)                             # ... and add the point
    
    # The first few commands are generally initialization commands, such as 
    # G21 (units to mm) or G90 (set absolute positioning). There is not yet a
    # Z-value added (this normally happens with a G28 'move to origin' command),
    # and the Z-value is 'None'. If this is the case, we remove these as 
    # these are not of any use. I know it's a hack, but it works....    
    try: 
        layersData.pop(None)
        gcodeLayer._registry.remove(None)
    except KeyError:
        pass                                                                    # no None key, so we just continue
    
    # Return the dictionary. 
    # Every key in the dict is a 'Z'-value. Its value is a 'gcodeLayer' object
    # in which the commands are stored (in gcodeLayer.commands)
    
    print("Done with sorting the gcodeCommands to gcodeLayers")
    return layersData                                                           # Done




def make_bevel_object(dimensions=(0.3, 0.3, 0.3)):
    """Create the bevel object that is used for printing.
        (TODO: make bevel object relate to the E- and F-coordinates)
        """        

    # check if there is a bevel_object already:
    if 'bevel_profile' in bpy.data.objects:                                     # the bevel profile exists
        bevelCurve = bpy.data.objects.get('bevel_profile')

    else:                                                                       # no bevel object yet
        bpy.ops.curve.primitive_bezier_circle_add()                             # add bezier circle
        # after creation, the object is automatically selected, so we can grab it
        bevelCurve = bpy.context.selected_objects[0]
        bevelCurve.dimensions = dimensions
        bevelCurve.name = "bevel_profile"
        # set to low view and render resolution, so rendering does not take much time/memory
        bevelCurve.data.resolution_u = 2
        bevelCurve.data.render_resolution_u = 2

    return bevelCurve




def create_blenderBezier(gcodeLayer):
    """generate a Blender bezier curve from the splines data of a gcodeLayer instance.
    
    Note: in the 'blender-gcode-addon' code by xtremd, a manual correction of the
    bezier curve was implemented. This was removed for several reasons:
    (1) it is not necessary if a Bezier curve is used in Blender: his code used
        a poly line, and in Blender a poly line does not have handles.
    (2) use of handles makes it easier to modify in the Blender viewport, to 
        correct the model if needed.
    (2) The drawing renders much faster in Blender with fewer objects created. 
        That is, if every line segment is a separate object, screen rendering
        time increases significantly. 
    """
    
    # Each Bezier curve will be named after its Z-value. 
    # Example: 'bezierCurve_Z0.23'  tells that it's the curve with Z-value = 0.23
    blCurveName = "curve_Z{0}".format(gcodeLayer.name)

    blCurve = bpy.data.curves.new(blCurveName, 'CURVE')                         # Add new curve data
    blCurve.dimensions = '2D'                                                   # no need to control the Z value, otherwise use '3D'
    
    # In Blender, a curve can have multiple splines. We will fill the curve
    # with multiple splines, all added to one BezierCurve.
    # We use the 'BEZIER' type, and will set the handle type to 'VECTOR'. This 
    # gives sharp corners, but also allows to later incorporate 'arc' functions
    # if required. Also, we can manually correct our model after import.

    for indexNr in range(len(gcodeLayer.splines)):
        blSpline = blCurve.splines.new('BEZIER')                                # add a new spline to the curve.

        # For each spline, first create the amount of points that are needed.
        gcodePts = gcodeLayer.count_spline_length(indexNr)
        blSpline.bezier_points.add(gcodePts-1)                                  # Note: when a spline is created, it has one bezier_point already
        
        # Loop over the created bezier_points of the spline and fill with data
        # Also, chenge the handle type to 'VECTOR' for every point.
        bezPts = blSpline.bezier_points
        for pt in range(gcodePts):
            bezPts[pt].co = (gcodeLayer.splines[indexNr][pt].parameters["X"], gcodeLayer.splines[indexNr][pt].parameters["Y"], gcodeLayer.splines[indexNr][pt].parameters["Z"]) # X, Y, Z
            bezPts[pt].handle_left_type = 'VECTOR'
            bezPts[pt].handle_right_type = 'VECTOR'

    return blCurve



def draw_blenderBeziers(*args):
    """Draw all the Gcode-based splines data onto the viewing port.

    [Remember: the data is stored in a dictionary object that stores gcodeLayer
    objects; each gcodeLayer object stores the Gcode data (as gcodeCommand instances)
    for one or more splines. In effect, every dict. key is a layer in which 
    commands with identical 'Z' are stored.

    This function walks through the 'gcodeLayer' instances from the lowest to highest Z-value. 
    For each layer, the splines data in each 'gcodeLayer' will be converted 
    to Bezier splines. These splines are bundled in Blender Beziercurve objects.
    
    args[0] : a dict that stores ('Z': 'gcodeLayer instance') pairs
    args[1] : if provided, used as the bevel_object. Otherwise ignored.
    """

    myLayers = args[0]                                                          # must always be supplied  

    # Get the layer names in sorted order. 
    # Since the layer name is Z-value, they will be ordered from bottom to top.
    layerNames = sorted(gcodeLayer._registry)
    print("The layers have the names:", layerNames)
    
    # Walk through all the layers, one by one
    for lr in layerNames:
        
        cu = create_blenderBezier(myLayers[lr])
#        print("CU created:", cu)

        # Check if we need to add a bevel object to the curve.
        try:
            cu.bevel_object = args[1]                                           # The second passed argument is used as bevel_object
        except IndexError:
            pass
        
        ob = bpy.data.objects.new("Ob" + cu.name, cu)
        ob.location = (0,0,0)                                                   #coordinate of origin
        ob.show_name = False
    
        # By linking the object to the active scene, the data becomes visible
        bpy.context.scene.objects.link(ob)


###
def animate_blenderBeziers(layerNames):
    """Animate the constructed Blender Beziercurves: one curve per keyframe.
    
    layerNames  :   The names of the layers to be animated
                    This is normally the Z-value of the curve.
    """

    scn = bpy.context.scene                                                     # get the current scene
    scn.frame_end = len(layerNames)                                             # one frame per curve
    scn.frame_set(0)                                                            # move to frame 0

    # At frame zero, hide all the curves
    for zValue in layerNames:
        # The beziercurve objects that were created are named 'Obcurve_Z###', 
        # where the # stands for the Z-value number in which that curve is located.
        # For every of the curves: select and hide them
        currObj = bpy.data.objects["Obcurve_Z{0}".format(zValue)]
        currObj.hide = True                                                     # hide selected object
        currObj.hide_render = True                                              # .. also when rendering
        currObj.keyframe_insert("hide")
        currObj.keyframe_insert("hide_render")

    # Let the curves appear one frame at a time
    for indexNr in range(len(layerNames)):
        scn.frame_set(indexNr)
        
        currObj = bpy.data.objects["Obcurve_Z{0}".format(layerNames[indexNr])]
        
        currObj.hide = False
        currObj.hide_render = False
        currObj.keyframe_insert("hide")
        currObj.keyframe_insert("hide_render")



# ----- the body of the program -----
def main():
    """Main code of the Blender part. 
    
    This code will only execute if the script is executed directly. Otherwise,
    this code is ignored (e.g., to facilitate import as a module)
    """

    inFile = '/media/data_disk/fablab_utrecht/source/blender-gcode-reader/douwe/sneeuwpop.gcode' #"_partial2.gcode'
#    inFile = '/media/data_disk/fablab_utrecht/source/blender-gcode-reader/example files/example_framevertex.gcode'

    myMachine = Gcode.machine()                                                 # create a machine (stores commands)
    myMachine.read_gcode(inFile)                                                # read gcode
    myMachine.standardize_5D_commands()                                         # turn the gcode line into a gcode command
    myMachine.synchronize_commands()                                            # add previous state data to the commands
    myGcodeCommands = myMachine.export_commands()                               # export to a list of commands in sequential order

    # The gcodeData object is a dictionary that stores gcodeLayer objects.
    # Each gcodeLayer object has the name of the 'Z' value, and in this 
    # object all the commands with that 'Z' value are stored.
    myGcodeLayers = sort_commands_to_layers(myGcodeCommands)                    # input is list, returns dict
    layerNames = sorted(gcodeLayer._registry)
    print("Layer names are:", layerNames)

    # For every layer (i.e., every gcodeLayer object), walk through the 
    # commands and convert to splines. For Blender, every layer (= Z-value) 
    # stores one BezierCurve object. This curve can have multiple splines.
    for layer in myGcodeLayers.values():
        layer.create_splines()
        print(layer)

    # There might well be layers with commands but without splines. We will
    # remove these, as they will clutter the code (NB such spline-less layers
    # are normally the result of a repositioning command like G92)
    noSplineInLayer = list()
    for layer in layerNames:
        if myGcodeLayers[layer].count_splines() == 0:                           # no splines are present
            noSplineInLayer.append(myGcodeLayers.pop(layer))                    # pop the layer with 0 splines
            gcodeLayer._registry.remove(layer)                                  # remove Z-value from registry
    print("These layers were removed as they contain no splines:", noSplineInLayer)

    # Hack to reselect the layernames: layers with 0 curves are removed, so we need to update
    layerNames = sorted(gcodeLayer._registry)

    # let's start drawing in Blender!
    # First, make a bevel object in case we'd like to use one
    bev = make_bevel_object()                                                   # make a bevel object
    
    # Draw the curves to our scene
    draw_blenderBeziers(myGcodeLayers)                                          # no bevel object
#    draw_blenderBeziers(myGcodeLayers, bev)                                    # with bevel object    

    # animate the curves
    animate_blenderBeziers(layerNames)
    
    
if __name__ == "__main__":
    main()
