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
The output of that are standardized 'Gcode' instances. This script will
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
sys.path.append("/home/douwe/.blender/2.62/scripts/addons/blender_gcode_reader")

# reload the GcodeParser module. This is done to ensure that any
# modifications applied to these files are processed (i.e., force reloading)
try:
    del sys.modules['Gcode_parser']
    import Gcode_parser
except KeyError:
    # the module is not loaded yet, we can ignore the KeyError and import directly
    import Gcode_parser

import bpy


# ----- class definitions -----
class gcodeCurve:
    """Store a group of Gcodes with identical Z-value. 
    
    Gcodes are scanned for their Z-value, and Gcodes with the 
    same Z-value are placed in the same 'gcodeCurve' instance.
    
    These Gcodes are then processed to generate splines.
    (In Blender, a 'Beziercurve' object can have multiple 'splines'. Each spline
    stores a series of points that are connected by a line).

    Variables:
        gcodeCurve._registry    :   list to keep track of the layers' names used
        gcodeCurve.name         :   the name of the instance. The 'Z-value' is a good one to use
        gcodeCurve.commands     :   a list of all the Gcode instances with 
                                    the same Z-value
        gcodeCurve.splines      :   a list of lists. Each list stores a spline,
                                    that are those points that are connected by
                                    a line. 
    """

    # Keep a registry of the current layers that we have made, so we don't 
    # overwrite layers by accident.
    # NOTE that because of the 'G92' code (reset position) command, strange
    #       bezier curves could be generated.
    _registry = list()

    def __init__(self, name):
        """Initialization of a 'gcodeCurve' instance. The <name> argument normally is the Z-value.
        """
        self._registry.append(name)                                             # bookkeeping
        self.name = name                                                        # default: Z-value
        self.standardGcode = list()                                                  # all 'Gcode' instances with the same Z value
        self.splines = list()                                                   # list of lists with spline points
        

    def __repr__(self):
        """return a representation of the 'gcodeCurve' instance"""
        return "<gcodeCurve '{0}': {1} standardGcode, {2} splines>".format(self.name, len(self.standardGcode), len(self.splines))


    def add_gcode(self, cmd):
        """Add a Gcode to the list of Gcodes of an existing spline"""
        self.standardGcode.append(cmd)


    def create_splines_data(self):
        """Create splines data from standardGcode commands.
        
        (Recall that all commands in a gcodeCurve have identical 'Z' values)
        """
        
        # create a list of points for the first spline.
        lastSplinePoint = self.standardGcode[0]                                 
        self.splines.append([lastSplinePoint])
        
        for indexNr in range(1, len(self.standardGcode)):
            currSplinePoint = self.standardGcode[indexNr]
            print("CURR SPLINE POINT: ", str(currSplinePoint))
            print("LAST SPLINE POINT: ", str(lastSplinePoint))
            
            delta = (currSplinePoint.X - lastSplinePoint.X, 
                     currSplinePoint.Y - lastSplinePoint.Y,
                     currSplinePoint.Z - lastSplinePoint.Z,
                     currSplinePoint.E - lastSplinePoint.E,
                     currSplinePoint.F - lastSplinePoint.F)
            
            if delta[0] != 0.0 or delta[1] != 0.0:                              # X and/or Y coordinates differ --> movement
                if delta[3] > 0.0:                                              # E-value changed: plastic is extruded
                    self.splines[-1].append(currSplinePoint)                    # take the last spline we're working on, and append to it
                    lastSplinePoint = currSplinePoint
                elif delta[3] <= 0.0:                                           # E-value is not changed, or plastic is retracted
                    self.splines.append([currSplinePoint])                      # add a new spline, with this point as first point
                    lastSplinePoint = currSplinePoint
            else:
                # no movement in X and Y directions. We don't care what happens for now
                # might become useful later, when dE- or dF-value information is used
                pass

        # For drawing stuff, we are only interested in splines with 2 or more standardGcode.
        # Hence, remove all the splines with length of 1, i.e. that contain only one command        
        tempSplines = list()
        for indexNr in range(len(self.splines)):

            if len(self.splines[indexNr]) >= 2:
                tempSplines.append(self.splines[indexNr])

        self.splines = tempSplines[:]


    def count_splines(self):
        """Returns the amount of splines in this gcodeCurve instance"""
        return len(self.splines)

    
    def count_spline_length(self, indexNr):
        """Returns the length of the spline with given indexNR"""
        return len(self.splines[indexNr])        


    def create_bezier_curve(self):
        """generate a Blender bezier curve from the splines data of a gcodeCurve instance.
        
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
        blCurveName = "curve_Z{0}".format(self.name)
    
        blCurve = bpy.data.curves.new(blCurveName, 'CURVE')                         # Add new curve data
        blCurve.dimensions = '2D'                                                   # no need to control the Z value, otherwise use '3D'
        
        # In Blender, a curve can have multiple splines. We will fill the curve
        # with multiple splines, all added to one BezierCurve.
        # We use the 'BEZIER' type, and will set the handle type to 'VECTOR'. This 
        # gives sharp corners, but also allows to later incorporate 'arc' functions
        # if required. Also, we can manually correct our model after import.
    
        for indexNr in range(len(self.splines)):
            blSpline = blCurve.splines.new('BEZIER')                                # add a new spline to the curve.
    
            # For each spline, first create the amount of points that are needed.
            gcodePts = self.count_spline_length(indexNr)
            blSpline.bezier_points.add(gcodePts-1)                                  # Note: when a spline is created, it has one bezier_point already
            
            # Loop over the created bezier_points of the spline and fill with data
            # Also, chenge the handle type to 'VECTOR' for every point.
            bezPts = blSpline.bezier_points
            for pt in range(gcodePts):
                bezPts[pt].co = (self.splines[indexNr][pt].X, self.splines[indexNr][pt].Y, self.splines[indexNr][pt].Z) # X, Y, Z
                bezPts[pt].handle_left_type = 'VECTOR'
                bezPts[pt].handle_right_type = 'VECTOR'
    
        return blCurve


                


class gcodeCurvesData:
    """Stores information on the curves that are generated from Gcode commands.
    """
    
    def __init__(self, extruder):
        """Create a new 'gcodeCurvesData' instance.
        
        The 'extruder' input is an 'Extruder' instance, which is generally
        stored inside a 'Machine' instance. E.g., myMachine.extruders[0] will
        give the first extruder data of myMachine.
        """
        self.extruderName = extruder.name
        self.standardGcode = extruder.standardGcode
        self.gcodeCurves = dict()
        self.bevel_object = None


    def add_gcode_to_gcodeCurves(self):
        """Sort gcode instances in gcodeCurve objects, based on their Z-value.
        
        Each Gcode instance is checked for their 'Z' value, and added to a
        gcodeCurve object that belongs to that 'Z' value
        
        Every key in the self.standardGcode dict is a 'Z'-value. 
        Its value is a 'gcodeCurve' object in which the standardGcode are 
        stored (in gcodeCurve.standardGcode).
        """
        
        for cmd in self.standardGcode:
            print(">>CMD", cmd)
            # process only the standardGcode that contain useful position information
            if cmd.command not in ("comment", "skeinforge", "unknown"):
                zValue = cmd.Z
    
                if zValue in gcodeCurve._registry:                              # Check if there is a gcodeCurve object with the 'Z' value:
                    self.gcodeCurves[zValue].add_gcode(cmd)                    
                else:                                                           # No gcodeCurve object with this Z value
                    self.gcodeCurves[zValue] = gcodeCurve(name=zValue)          # create gcodeCurve instance and add to stack
                    self.gcodeCurves[zValue].add_gcode(cmd)                     # ... and add the point
        
        # The first few standardGcode are generally initialization standardGcode, such as 
        # G21 (units to mm) or G90 (set absolute positioning). There is not yet a
        # Z-value added (this normally happens with a G28 'move to origin' command),
        # and the Z-value might be 'None'. If this is the case, we remove these as 
        # these are not of any use. I know it's a hack, but it works....    
        try: 
            self.gcodeCurves.pop(None)
            gcodeCurve._registry.remove(None)
        except KeyError:
            pass                                                                    # no None key, so we just continue

        print("OK: All Gcodes are sorted in gcodeCurve objects")

    
    def create_bevel_object(self, dimensions=(0.3, 0.3, 0.3)):
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
    
        self.bevel_object = bevelCurve
    
        
    def draw_blender_bezier_curves(self, use_bevel = False):
        """Draw all the Gcode-based splines data onto the viewing port.
    
        [Remember: the data is stored in a dictionary object that stores gcodeCurve
        objects; each gcodeCurve object stores the Gcode data (as Gcode instances)
        for one or more splines. In effect, every dict. key is a layer in which 
        standardGcode with identical 'Z' are stored.
    
        This function walks through the 'gcodeCurve' instances from the lowest to highest Z-value. 
        For each layer, the splines data in each 'gcodeCurve' will be converted 
        to Bezier splines. These splines are bundled in Blender Beziercurve objects.
        
        args[0] : a dict that stores ('Z': 'gcodeCurve instance') pairs
        args[1] : if provided, used as the bevel_object. Otherwise ignored.
        """
    
        myLayers = self.gcodeCurves                                                          # must always be supplied  
    
        # Get the layer names in sorted order. 
        # Since the layer name is Z-value, they will be ordered from bottom to top.
        Z_layerNames = sorted(gcodeCurve._registry)
        print("The layers have the names:", Z_layerNames)
        
        # Walk through all the layers, one by one
        for lr in Z_layerNames:
            cu = self.gcodeCurves[lr].create_bezier_curve()
            print("CU created:", cu)
    
            # Check if we need to add a bevel object to the curve.
            if use_bevel == True:
                cu.bevel_object = self.bevel_object                             # The second passed argument is used as bevel_object
            else:
                pass
            
            ob = bpy.data.objects.new("Ob" + cu.name, cu)
            ob.location = (0,0,0)                                                   #coordinate of origin
            ob.show_name = False
        
            # By linking the object to the active scene, the data becomes visible
            bpy.context.scene.objects.link(ob)



    def animate_blender_bezier_curves(Z_layerNames):
        """Animate the constructed Blender Beziercurves: one curve per keyframe.
        
        Z_layerNames  :   The names of the layers to be animated
                        This is normally the Z-value of the curve.
        """
    
        scn = bpy.context.scene                                                     # get the current scene
        scn.frame_end = len(Z_layerNames)                                             # one frame per curve
        scn.frame_set(0)                                                            # move to frame 0
    
        # At frame zero, hide all the curves
        for zValue in Z_layerNames:
            # The beziercurve objects that were created are named 'Obcurve_Z###', 
            # where the # stands for the Z-value number in which that curve is located.
            # For every of the curves: select and hide them
            currObj = bpy.data.objects["Obcurve_Z{0}".format(zValue)]
            currObj.hide = True                                                     # hide selected object
            currObj.hide_render = True                                              # .. also when rendering
            currObj.keyframe_insert("hide")
            currObj.keyframe_insert("hide_render")
    
        # Let the curves appear one frame at a time
        for indexNr in range(len(Z_layerNames)):
            scn.frame_set(indexNr)
            
            currObj = bpy.data.objects["Obcurve_Z{0}".format(Z_layerNames[indexNr])]
            
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

    inFile = '/home/douwe/compile/github/blender-gcode-reader/testFiles/sneeuwpop_T0.gcode' #"_partial2.gcode'
#    inFile = '/media/data_disk/fablab_utrecht/source/blender-gcode-reader/example files/example_framevertex.gcode'
    
    # load the Gcode data into an 'Extruder' instance that resides inside a 'Machine'
    myMachine = Gcode_parser.Machine()                                          # create a machine (stores standardGcode)
    myMachine.add_extruder(inFile)                                              # add extruder 1
    extruderToDraw = myMachine.extruders[-1]

    # Get the extruder we'd like to draw, and transfer that data to a gcodeCurvesData object
    myGcodeCurvesData = gcodeCurvesData(extruderToDraw)
    
    # Sort the Gcode commands by Z-value, and create 'gcodeCurve' instance for every Z value
    myGcodeCurvesData.add_gcode_to_gcodeCurves()

    # Obtain a sorted list of all the names of the layers, i.e., all Z values.
    Z_layerNames = sorted(gcodeCurve._registry)
#    print("Layer names are:", Z_layerNames)

    for Zval in Z_layerNames:
        myGcodeCurvesData.gcodeCurves[Zval].create_splines_data()

    # There might well be layers with commands but without splines. We will
    # remove these, as they will clutter the code (NB such spline-less layers
    # are normally the result of a repositioning command like G92)
    noSplineInLayer = list()
    for layer in Z_layerNames:
        if myGcodeCurvesData.gcodeCurves[layer].count_splines() == 0:                           # no splines are present
            noSplineInLayer.append(myGcodeCurvesData.gcodeCurves.pop(layer))                    # pop the layer with 0 splines
            gcodeCurve._registry.remove(layer)
            #gcodeCurve._registry.remove(layer)                                  # remove Z-value from registry
    print("These layers were removed as they contain no splines:", noSplineInLayer)

    # Hack to reselect the Z_layerNames: layers with 0 curves are removed, so we need to update
    Z_layerNames = sorted(gcodeCurve._registry)

    # let's start drawing in Blender!
    # First, make a bevel object in case we'd like to use one
    myGcodeCurvesData.create_bevel_object()

    # Draw the curves to our scene
    myGcodeCurvesData.draw_blender_bezier_curves()                                          # no bevel object
#    draw_blender_bezier_curves(mygcodeCurve, bev)                                    # with bevel object    

    # animate the curves
#    animate_blender_bezier_curves(Z_layerNames)
    
    
if __name__ == "__main__":
    main()
