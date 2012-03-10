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
A very basic Gcode reader for Python3.

This file contains some simple tools to parse a Gcode file in Python3.
The purpose of this parser is to extract Gcode for use in Blender, as well as
to work with merging Gcodes (for multi-extruderhead printing).

This parser file is based upon the 'blender-gcode-reader' Blender addon code base by:

Original author: Simon Kirkby ('zignig'): https://github.com/zignig/blender-gcode-reader
Modifications: Alessandro Ranellucci ('alexjr'): https://github.com/alexrj/blender-gcode-reader
Modifications: Winter Guerra ('xtremd') : https://github.com/xtremd/blender-gcode-reader/

My modifications: Douwe van der Veen ('appultaart')

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
import copy


# ----- function definitions -----

#
# The 'gcode_...' functions are based on the Reprap Gcode-wiki
#
def gcode_move(cmd):
    """Return the action on a 'move'. 
    
    For our current purpose, there is no need to do anything with the 'move' data,
    so we can just return the 'cmd' object without modifications. In the future,
    there might be additional functionality added.

    cmd   : the current command. 
    """
    return cmd


def gcode_set_units_to_inch(cmd):
    """Change the 'units' parameter to 'inch' """
    
    cmd.parameters["units"] = "inch"
    return cmd
    

def gcode_set_units_to_mm(cmd):
    """Set the machine state 'units' parameter to 'mm'. 
    """
    cmd.parameters["units"] = "mm"
    return cmd


def gcode_dwell(cmd):
    """Wait for a specified amount of time but do nothing.
    Example: G4 P200
    In this case sit still doing nothing for 200 milliseconds. 
    During delays the state of the machine (for example the temperatures 
    of its extruders) will still be preserved and controlled. """
    return cmd


def gcode_move_to_origin(cmd):
    """return the home coordinates 
    """
    homePosition = (0.0,0.0,0.0)                                                # x, y, z values

    # if there are X, Y, or Z values, only change those values to zero where
    # a parameter is given for. From the Reprap wiki: 'G28 X0 Y72.3'
    # will zero the X and Y axes, but not Z. The actual coordinate values are ignored.          
    if "X" in cmd.parameters or "Y" in cmd.parameters or "Z" in cmd.parameters: # if one or more: True 
        if "X" in cmd.parameters:
            cmd.parameters["X"] = homePosition[0]
        if "Y" in cmd.parameters:
            cmd.parameters["Y"] = homePosition[1]
        if "Z" in cmd.parameters:
            cmd.parameters["Z"] = homePosition[2]
        return cmd

    else:
        # if there are no arguments, i.e. the 'G28' command only
        # change the position to the home coordinates
        cmd.parameters["X"] = homePosition[0]
        cmd.parameters["Y"] = homePosition[1]
        cmd.parameters["Z"] = homePosition[2]
        return cmd


def gcode_set_to_abs_positioning(cmd):
    """Set the 'absolutePos' parameter to 'True' """
    cmd.parameters["absolutePos"] = True
    return cmd

def gcode_set_to_rel_positioning(cmd):
    """Set the 'absolutePos' parameter to 'False' """
    cmd.parameters["absolutePos"] = False
    return cmd


def gcode_set_position(cmd):
    """
    Set the absolute zero point by resetting current position to the values specified.

    Example: G92 X10 E90
    This would set the machine's X coordinate to 10, and the extrude 
    coordinate to 90. No physical motion will occur.     
    
    Since the X, Y, Z, E, and F values are set as parameters when this command 
    is executed, no change needs to be done. (However, there *has been* a coordinate
    change so one might run into weird use cases if G92 is used frequently.)
    """
    return cmd
    

def gcode_extruder_on(cmd):
    """Depreciated function. See reprap Gcode wiki. 
    
    For compatibility, an E value is returned. For example, 'old' Makerbot
    .gcode works with switching the extruder on with this command.
    This can be simulated in a 5D-printing environment by filling the E-value
    with some arbitrary value (hardcoded as 0.999 here)"""
    
    cmd.parameters["E"] = 0.999
    # Hmmm, this ugly hack with the 'E-value' does not seem to do the trick,
    # because the check is for a dE value when constructing the curve. 
    # TODO: write a function (with 'yield' statement?) that add increased
    # E-values when only X, Y positions are given
    return cmd


def gcode_extruder_off(cmd):
    """Depreciated function. See reprap Gcode wiki.
    
    For compatibility, an E value is returned. For example, 'old' Makerbot
    .gcode works with switching the extruder off with this command.
    This can be simulated in a 5D-printing environment by filling the E-value
    with some arbitrary value (hardcoded as 0.0 here)"""
    
    cmd.parameters["E"] = 0.0
    # See comment in 'gcode_extruder_on' function: this is an ugly hack
    return cmd


def gcode_set_extruder_temp_cont(cmd):
    """Set the extruder temperature to the gcodeCommand instance"""
    cmd.parameters["extruderTemp"] = cmd.parameters["S"]                        # if M104 S260 --> get '260'
    return cmd


def gcode_get_extruder_temp(cmd):
    """Return the extruder temperature to the machine. 
        Not relevant for now; Ignore.
    """
    return cmd


def gcode_fan_on(cmd):
    """Set the gcodeCommand parameter "fan" to True"""
    cmd.parameters["fan"] = True
    return cmd


def gcode_fan_off(cmd):
    """Set the gcodeCommand parameter "fan" to False"""
    cmd.parameters["fan"] = False
    return cmd


def gcode_set_extruder_speed(cmd):
    """***Depreciated function, according to the Reprap Gcode Wiki***
    --> Sets speed of extruder motor. (Deprecated in current firmware, see M113)"""
    return cmd

def gcode_set_extruder_temp_wait(cmd):
    """Set the extruder temperature of the gcodeCommand instance"""
    cmd.parameters["extruderTemp"] = cmd.parameters["S"]
    return cmd


def gcode_set_extruder_pwm(cmd):
    """Set the extrudePWM parameter of the gcodeCommand instance"""
    cmd.parameters["extruderPWM"] = cmd.parameters["S"]
    return cmd


    
def skeinforge_code(*args):
    pass


def get_position_difference(firstObj, secondObj):
    """Returns the difference of two Gcodes (assuming 'G1' code)
    
    firstObj and secondObje should be two instances of a 'headPosition' object"""
    return "G1 " + (firstObj - secondObj)




# ----- class definitions -----
class gcodeCommand:
    """Store Gcode command information in an ordered fashion.
    
    Members of this class store a processed Gcode command (processed by a 'machine'
    instance). When a line of Gcode is processed, its parameters are split for 
    easy and reproducible access. Note that a structured order of the command
    parameters is not expected (i.e., commands 'G1 X3 Y0.2 Z9' == 'G1 Z9 Y0.2 X3').
    
    Example:    line 14 of a Gcode file is 'G1 X23 Y-34 Z0.2 F1100 E23'. 
                With this command processed, the results are stored in an 
                'gcodeCommand' instance, say 'myGcodeCommand':
                    myGcodeCommand.name = '14'
                    myGcodeCommand.command = 'G1'
                    myGcodeCommand.parameters = {"X":23.0, "Y"-34.0:, "Z":0.2, "E":23.0, "F":1100.0}
    
    Variables:
        gcodeCommand.name       :   name of the object. The file line number is a good one to use
        gcodeCommand.command    :   the command as a string
        gcodeCommand.parameters :   the parameters, stored in a dictionary
    """
    
    def __init__(self, name):
        """Initialize a member of the 'gcodeCommand' class"""
        self.name = name                                                        # command name: suggest to use the line number
        self.command = str()                                                    # the gcode command. Examples: 'G1,' 'M105', 'comment', 'skeinforge'
        self.parameters = dict()                                                # the parameters of the command. Example: {'X':23, 'Y':7, 'E':56}', {'S':260}


    def __repr__(self):
        """return a representation with the values of this object instance"""
        return "gcodeCommand(name={0.name}', command={0.command}, parameters={0.parameters})".format(self)
    
    
    def __eq__(self, other):
        """Implements the '==' operator. 
        Return True if two instances have identical values (except 'name' variable), 
        otherwise return False.
        """
        return self.command == other.command and self.parameters == other.parameters
     

    def get_coordinates(self):
        """Return the X, Y, Z, and E and F values in a 5-tuple"""

        try:                                                                    # if all of the keys are in the dict, return tuple
            return (self.parameters["X"], self.parameters["Y"], self.parameters["Z"], self.parameters["E"], self.parameters["F"])
        except KeyError:                                                        # one or more of the keys are not in the dict!
            print("ERROR: this gcodeCommand does not have X, Y, Z, E, and/or F fields.")
            return



class machine:
    """Objects of the 'machine' class.
    
    Each member of the 'machine' class stores information of a .gcode file,
    and has some methods to process this information. 
    
    Variables:
        machineName     :   the name for the machine, like 'Ultimaker' or 'Extruder 2'
        rawGcode        :   the Gcode commands are stored in a list, line by line
        commands        :   the processed Gcode commands are stored in a list.
        
        One may assume that the index position of the 'rawGcode' and 'commands' 
        lists point to the same command. Thus, 'myMachine.rawGcode[4]' gives
        the Gcode command in the 5th line of the imported .gcode file, and 
        'myMachine.commands[4]' stores the processed command. 
    """

    def __init__(self, machineName='Ultimaker'):
        """Initialize a new member of the 'machine' class"""
        self.machineName = machineName
        self.rawGcode = []                                                      # list to store raw Gcode
        self.commands = []                                                      # extract the recognized gcode commands


    def __repr__(self):
        """returns a representation of a 'machine' object"""
        return """<Machine object
        * machineName: {0.machineName}
        * rawGcode: {1} lines
        * commands: {2} lines>
        """.format(self, len(self.rawGcode), len(self.commands))


    def read_gcode(self, filename):
        """Import a '*.gcode' file into the 'machine' instance.
        
        This method reads a *.gcode file into memory, and stores each line
        in the rawGcode list. From here, it can be used for later processing.
        
        filename    :   a file that contains the .gcode commands

        return      :   list (each item is a line of the file)
        """
        with open(filename, mode='rt') as gcodeFile:
            for line in gcodeFile:
                line = line.strip()                                             # remove trailing whitespace, including '\n'
                self.rawGcode.append(line)

    
    def standardize_3D_commands(self):
        """Transform each line of a .gcode file to a standardized (3D) command.

        TODO. Place code here to process 3D Gcode commands,
        that is, those files that use the M101 and M103 commands to switch the
        extruder on or off, and that do not use E and/or F information.
        """
        pass


    def standardize_5D_commands(self):
        """Transform each line of a .gcode file to a standardized (5D) command.

        This function takes a list of lines of raw gcode imput (e.g., from 
        the 'read_gcode' method). Each line is then processed sequentually by 
        doing the following:
        
        1. Create a new 'gcodeCommand' member;
        2. If there are Skeinforge commands (marked '(<...>)', then do not treat
            as a comment but mark as a Skeinforge command. 
        3. Check for comments in the line. If there are, move those to 
            the 'comment' field
        4. Store the first parameter in the 'command' field.
        5. Store the other variables in the 'parameters' dictionary. 
        6. Add any missing parameters that will be transferred from the last 
            known setting. Example, if command is 'G1 E5 F10', and second command
            is 'G1 X0 Y10', the E and F values must be transferred to here, as 
            they were unchanged.
        
        Note that this function assumes that the input file contains 5D code,
        that is, code that uses the E and F values. When no E/F values are used
        to control the start/stop of extrusion, use the 'create_3D_commands' method.
        """

        lineNr = 0                                                              # keep track of the current line number
        for line in self.rawGcode:
            lineNr += 1
            
            # 1. create a new 'gcodeCommand' instance
            currCommand = gcodeCommand(name=lineNr)            
            
            # 2. check if the line contains Skeinforge-code. 
            if line.startswith('(<'):                                           # Assumes that first character is always and only '(<'
                line = line[1:-1]                                               # remove brackets '()'
                currCommand.command = "skeinforge"
                currCommand.parameters["skeinforge"] = line
                self.commands.append(currCommand)                               # add to the list of commands
                continue
            
            # 3. Ignore comments marked by ';'
            if ';' in line:
                currCommand.parameters["comment"] = line.split(";", 1)[1]       # all to the right of ";" is a comment
                line = line.split(";", 1)[0]                                    # remainder is useable command

            # 3. Ignore comments marked by '(..)'
            if '(' in  line:
                currCommand.parameters["comment"] = line.split("(", 1)[1].strip(";)")   # All to the right of '(' is a comment
                line = line.split("(")[0].strip()

            # 3. There is the chance that the whole line is a comment.
            #    In that case, grab the raw gcode, and insert this line as a comment
            if len(line) == 0:
                currCommand.command = "comment"
                currCommand.parameters["comment"] = self.rawGcode[lineNr-1].strip(";()")
                self.commands.append(currCommand)                               # add to the list of commands
                continue

            # 4. Store the 'command' parameter (the first code in the line)
            commands = line.split(" ")
            if commands[0] in reprapGcodes.keys():                              # this line starts with a valid code
                currCommand.command = commands[0].strip()                       # add command name; remove any double white space as some Gcode has two whitespaces
                for item in commands[1:]:
                    # for every of the parameters, make the first character the
                    # key, and add the remaining characters (excl. whitespace)
                    currCommand.parameters[item[0]] = float(item[1:].strip())
                            
            else:
                # the command is not in the list of Gcodes, treat as comment
                print(">> Line {0}: unrecognized Gcode in '{1}'".format(lineNr, line))
                currCommand.command = "unknown"
                currCommand.parameters["comment"] = commands

            self.commands.append(currCommand)                                   # Add the created gcodeCommand instance to the list of commands

    def synchronize_commands(self):
        """Add the last-known parameters (stored in machine memory) to each command.
        
            Example: line 1 = G1 X2 Y2 Z2 E10 F10
                    line 2 = G1 Y4
                    --> the X, Z, E, and F positions are not modified in line #2, 
                        and can be transferred from line #1. 
            
            Before adding the last known parameter values, first each gcodeCommand
            instance is checked against their Reprap Gcode, since the command
            might modify a parameter. Example: 'G28' tells to set X,Y,Z to (0,0,0).  
        """
        
        lastMachineState = {'X':None, 'Y':None, 'Z':None,                       # The initial machine state
                            'E':0.0, 'F':0.0,                                   # coordinates
                                                                                # Note: E=0 and F=0, since it is implicitly assumed in
                                                                                #       the Gcode file that those are zero when the 
                                                                                #       machine is powered up.
                            'units':None,                                       # working unit: mm, inch
                            'extruderTemp':None,                                # extruder temperature
                            'extruderPWM':None,                                 # extruder temp. set by PWM
                            'absolutePos':None,                                 # is positioning absolute (True), relative (False)
                            'fan':False}                                        # is the fan on (True) or off (False)

        for cmd in self.commands:
            if cmd.command in reprapGcodes.keys():
                
                # First, send the command to its function and check if there 
                # is an operation that must be done to the command.
                cmd = reprapGcodes[cmd.command](cmd)

                # Fill in the blanks
                for key in lastMachineState.keys():                             # pass the lastMachineState's settings to the command...
                    cmd.parameters.setdefault(key, lastMachineState[key])       # (ignore if the key is in parameters; otherwise, add the lastMachineState key/value pair)

                for key in lastMachineState.keys():                             # .... and update lastMachineState values with those of the latest command
                    lastMachineState[key] = cmd.parameters[key]

            else:                                                               # if cmd not in Gcode commands, do not modify it
                pass
        print("Standardization of Gcode commands has finished.")


    def export_commands(self):
        """Export the standardized Gcode commands.
        
        This method will place all the 'gcodeCommand' instances (for example, 
        as generated by synchronize_commands) into a list, for futher processing.
        
        return  :   list  (a list of gcodeCommand instances)
        """

        exportList = list()
        
        for command in self.commands:
                exportList.append(command)
        print("A list of synchronized Gcode commands has been exported successfully")
        return exportList



# ----- variables  -----
reprapGcodes =   {
                # Headings taken from 'reprap.org/wiki/G-code'
                # Letter --> Meaning
                #
                # Gnnn 	Standard GCode command, such as move to a point
                'G0'    : gcode_move,                                           # rapid move, but treated as G1
                'G1'    : gcode_move,
#                'G4'    : gcode_dwell,
#                'G04'   : gcode_dwell,
                'G20'   : gcode_set_units_to_inch,
                'G21'   : gcode_set_units_to_mm,
                'G28'   : gcode_move_to_origin,
                'G90'   : gcode_set_to_abs_positioning,
                'G91'   : gcode_set_to_rel_positioning,
                'G92'   : gcode_set_position,
                # Mnnn 	RepRap-defined command, such as turn on a cooling fan
                'M101'  : gcode_extruder_on,
                'M103'  : gcode_extruder_off,
                'M104'  : gcode_set_extruder_temp_cont,
                'M105'  : gcode_get_extruder_temp,
                'M106'  : gcode_fan_on,
                'M107'  : gcode_fan_off,
                'M108'  : gcode_set_extruder_speed,
                'M109'  : gcode_set_extruder_temp_wait,
                'M113'  : gcode_set_extruder_pwm
                # Tnnn 	Select tool nnn. In RepRap, tools are extruders

                # Snnn 	Command parameter, such as the voltage to send to a motor                
                # Pnnn 	Command parameter, such as a time in milliseconds
                # Xnnn 	An X coordinate, usually to move to
                # Ynnn 	A Y coordinate, usually to move to
                # Znnn 	A Z coordinate, usually to move to
                # Ennn 	Length of extrudate in mm. This is exactly like X, Y and Z, 
                #       but for the length of filament to extrude. It is common 
                #       for newer stepper based systems to interpret ... 
                #       Better: Skeinforge 40 and up interprets this as the 
                #       absolute length of input filament to consume, rather 
                #       than the length of the extruded output.
                # Fnnn 	Feedrate in mm per minute. (Speed of print head movement)
                }

skeinforgeCodes = {

                # I am for now not working with skeinforge codes, but it's left here
                # and will not hurt. Skeinforge codes can be easily implemented
                # here, just as with the Reprap codes...
                '</surroundingLoop>' : skeinforge_code,
                '<surroundingLoop>' : skeinforge_code,
                '<boundaryPoint>' : skeinforge_code,
                '<loop>' : skeinforge_code,
                '</loop>' : skeinforge_code,
                '<layer>' : skeinforge_code,
                '</layer>' : skeinforge_code,
                '<layer>' : skeinforge_code,
                '<layerThickness>' : skeinforge_code,
                '</layerThickness>' : skeinforge_code,
                '<perimeter>' : skeinforge_code,
                '</perimeter>' : skeinforge_code, 
                '<bridgelayer>' : skeinforge_code,
                '</bridgelayer>' : skeinforge_code,
                '</extrusion>' : skeinforge_code,
                '<perimeterWidth>' : skeinforge_code,
                '</perimeterWidth>' : skeinforge_code
                }


# ----- the body of the program -----
def main():
    """Main code of the Gcode reader. 
    
    This code will only execute if the script is executed directly. Otherwise,
    this code is ignored (e.g., to facilitate import as a module)
    """
 
    # create a machine (stores commands)
    inFile = '/media/data_disk/fablab_utrecht/source/blender-gcode-reader/douwe/sneeuwpop_partial2.gcode'
#    inFile = '/media/data_disk/fablab_utrecht/source/blender-gcode-reader/example files/example_framevertex.gcode'
    myMachine = machine()
    myList = list()
 
    myMachine.read_gcode(inFile)                                                # read gcode
    myMachine.standardize_5D_commands()                                         # turn each gcode line into a standardized gcodeCommand
    myMachine.synchronize_commands()                                            # add previous state data to the commands
    myList = myMachine.export_commands()                                        # export to list
    
    # Print something on the screen so we know that something has happened
    for cmd in myList:
        if cmd.command not in ("unknown", "comment", "skeinforge"):
            print(">Command {0}: X={1}, Y={2}, Z={3}, E={4}, F={5}".format(cmd.name, cmd.parameters["X"], cmd.parameters["Y"], cmd.parameters["Z"], cmd.parameters["E"], cmd.parameters["F"]))


if __name__ == "__main__":
    main()

