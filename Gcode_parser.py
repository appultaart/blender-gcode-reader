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

This file contains some very simple tools to parse a Gcode file in Python3.
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


# ----- function definitions -----


# ----- class definitions -----
class Reprap_Gcode:
    """Store information of Reprap-specific Gcode commands.
    
    Such Gcode commands may be interpreted before they are stored (for example,
    the 'home axis' command might be invoked that tells the machine to move the
    head to the home position, but without specifying what exactly that home
    position is). Therefore, the Machine class instances have functions that 
    will modify such gcode-commands.
    """

    def gcode_move(cmd):
        """Return the action on a 'move'. 
        """
        return cmd
        
    def gcode_set_units_to_inch(cmd):
        """Change the 'units' parameter to 'inch' """
        cmd.parameters["units"] = "inch"
        return cmd
        
    def gcode_set_units_to_mm(cmd):
        """Set the extruder state 'units' parameter to 'mm'. 
        """
        cmd.parameters["units"] = "mm"
        return cmd
    
    def gcode_dwell(cmd):
        """Wait for a specified amount of time but do nothing.
        Example: G4 P200
        In this case sit still doing nothing for 200 milliseconds. 
        During delays the state of the extruder will still be preserved 
        and controlled. """
        return cmd
    
    def gcode_select_tool(cmd):
        """Select the tool. In the case of RepRap Gcode, tools are extruders.
        """
        if cmd.command == "T0":
            cmd.T = 0
        if cmd.command == "T1":
            cmd.T = 1
        return cmd
    
    def gcode_move_to_origin(cmd):
        """return the home coordinates 
        """
        homePosition = (0.0,0.0,0.0)                                                # x, y, z values
    
        # if there are X, Y, or Z values, only change those values to zero where
        # a parameter is given for. From the Reprap wiki: 'G28 X0 Y72.3'
        # will zero the X and Y axes, but not Z. The actual coordinate values are ignored.          
        if cmd.X is not None or cmd.Y is not None or cmd.Z is not None: # if one or more: True 
            if cmd.X is not None:
                cmd.X = homePosition[0]
            if cmd.Y is not None:
                cmd.Y = homePosition[1]
            if cmd.Z is not None:
                cmd.Z = homePosition[2]
            return cmd
        else:
            # if there are no arguments, i.e. the 'G28' command only
            # change the position to the home coordinates
            cmd.X = homePosition[0]
            cmd.Y = homePosition[1]
            cmd.Z = homePosition[2]
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
        This would set the extruder's X coordinate to 10, and the extrude 
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
        return cmd
        
    def gcode_extruder_off(cmd):
        """Depreciated function. See reprap Gcode wiki.
        
        For compatibility, an E value is returned. For example, 'old' Makerbot
        .gcode works with switching the extruder off with this command.
        This can be simulated in a 5D-printing environment by filling the E-value
        with some arbitrary value (hardcoded as 0.0 here)"""
        return cmd
    
    def gcode_set_extruder_temp_cont(cmd):
        """Set the extruder temperature to the Gcode instance"""
        cmd.parameters["extruderTemp"] = cmd.parameters["S"]                        # if M104 S260 --> get '260'
        return cmd

    def gcode_get_extruder_temp(cmd):
        """Return the extruder temperature. 
            Not relevant for now; Ignore.
        """
        return cmd
        
    def gcode_fan_on(cmd):
        """Set the Gcode parameter "fan" to True"""
        cmd.parameters["fan"] = True
        return cmd
    
    def gcode_fan_off(cmd):
        """Set the Gcode parameter "fan" to False"""
        cmd.parameters["fan"] = False
        return cmd
    
    def gcode_set_extruder_speed(cmd):
        """***Depreciated function, according to the Reprap Gcode Wiki***
        --> Sets speed of extruder motor. (Deprecated in current firmware, see M113)"""
        return cmd
    
    def gcode_set_extruder_temp_wait(cmd):
        """Set the extruder temperature of the Gcode instance"""
        cmd.parameters["extruderTemp"] = cmd.parameters["S"]
        return cmd
    
    def gcode_set_extruder_pwm(cmd):
        """Set the extrudePWM parameter of the Gcode instance"""
        cmd.parameters["extruderPWM"] = cmd.parameters["S"]
        return cmd
    
    def gcode_set_E_absolute(cmd):
        """Use absolute distances for extrusion, no relative E-values."""
        return cmd
    
    def gcode_disable_motors(cmd):
        """Disable steppers until next move.
        (alternatively, use S to specify an inactivity timeout, after which 
        the steppers will be disabled. S0 to disable the timeout.)
        """
        return cmd

    def skeinforge_code(*args):
        pass

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
                    'M82'   : gcode_set_E_absolute,
                    'M84'   : gcode_disable_motors,
                    'M101'  : gcode_extruder_on,
                    'M103'  : gcode_extruder_off,
                    'M104'  : gcode_set_extruder_temp_cont,
                    'M105'  : gcode_get_extruder_temp,
                    'M106'  : gcode_fan_on,
                    'M107'  : gcode_fan_off,
                    'M108'  : gcode_set_extruder_speed,
                    'M109'  : gcode_set_extruder_temp_wait,
                    'M113'  : gcode_set_extruder_pwm,
    
                    # Tnnn 	Select tool nnn. In RepRap, tools are extruders
                    'T0'    : gcode_select_tool,
                    'T1'    : gcode_select_tool
    
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


class Gcode:
    """Store Gcode command information in a defined structural form.
    
    Members of this class store a processed Gcode command (processed by an 'extruder'
    instance). When a line of Gcode is processed, its parameters are split for 
    easy and reproducible access. Note that a structured order of the command
    parameters is not expected (i.e., commands 'G1 X3 Y0.2 Z9' == 'G1 Z9 Y0.2 X3').
    
    Example:    line 14 of a Gcode file is 'G1 X23 E23 (this is a comment)'. 
                With this command processed, the results are stored in an 
                'Gcode' instance, say 'myGcode':
                    myGcode.name = '14'
                    myGcode.command = 'G1'
                    myGcode.parameters = {"comment":"this is a comment"}
                    myGcode.X = 23
                    myGcode E = 23

    Variables:
        Gcode.name       :   name of the object. The file line number is a good one to use
        Gcode.command    :   the command as a string
        Gcode.parameters :   paramete
        Gcode.X .Y .Z    :   x, y, and z coordinates
        Gcode.E .F       :   extrusion and feed rate parametersrs
        Gcode.T          :   extruder this command operates on        
    """
    
    def __init__(self, name):
        """Initialize a member of the 'Gcode' class"""
        self.name = name                                                        # command name: suggest to use the line number
        self.command = str()                                                    # the gcode command. Examples: 'G1,' 'M105', 'comment', 'skeinforge'
        self.parameters = dict()                                                # the parameters of the command. Example: {'S':260}
        self.X = None
        self.Y = None
        self.Z = None
        self.E = 0.0
        self.F = 0.0
        self.T = 0

    def __repr__(self):
        """return a representation with the values of this object instance"""
        return "<Gcode: name='{0.name}', command='{0.command}', ".format(self) + \
                "X={0.X}, Y={0.Y}, Z={0.Z}, E={0.E}, F={0.F}, T={0.T}, ".format(self) + \
                "parameters={0.parameters}>".format(self)
    
    def __str__(self):
        """return a sting representation of all the parameters of this command"""

        constructedGcode = ""                 # store the result in here
        
        # if it's only a comment, return the comment and ignore other parameters
        if self.command == "comment":
            # this check is needed if one has to print a comment-command 
            # without a parameter 'comment', or with this parameter removed. 
            if "comment" in self.parameters.keys():
                constructedGcode += "(" + self.parameters["comment"].strip() + ")"
                return constructedGcode.strip()
            else:
                constructedGcode += "( *** " + self.name + ", without 'comment' parameter *** )"
                return constructedGcode.strip()
        
        # if command is T0, T1: only return T
        elif self.command.startswith("T"):
            if self.command == "T0":
                return "T0"
            elif self.command == "T1":
                return "T1"

        elif self.command.startswith("M"):
            constructedGcode += self.command + " "
            for parameter in ["S", "P"]:
                if parameter in self.parameters.keys():
                    constructedGcode += parameter + str(self.parameters[parameter]) + " "

        else:
            constructedGcode += self.command + " "
            constructedGcode += "X" + str(self.X) + " " if self.X is not None else ""
            constructedGcode += "Y" + str(self.Y) + " " if self.Y is not None else ""
            constructedGcode += "Z" + str(self.Z) + " " if self.Z is not None else ""
            constructedGcode += "E" + str(self.E) + " " if self.E is not None else ""
            constructedGcode += "F" + str(self.F) + " " if self.F is not None else ""
#            constructedGcode += "T" + str(self.T) + " " if self.T is not None else ""

        # add a comment to the end of the line, if there is any
        if "comment" in self.parameters.keys():
            constructedGcode += "(" + str(self.parameters["comment"]) + ")"
        
        # remove any trailing whitespace, and return the string
        return constructedGcode.strip()


    def update_state(self, other):
        """Update the current ('self') Gcode parameters with those of another ('other') instance.
        
        This function takes all the 'parameters' arguments of 'self', and 
        updates these with those parameters values in 'other'. Main purpose
        is to transfer the last known machine state to the current command.
        
        NOTE: the 'other' instance must exist, and will be implicitly updated
              with this code! The differences between the 'self' and 'other'
              instance are the lack of 'comment', 'unknown', and 'skeinforge'
              fields, and a different other.name than self.name. 

        return  :   an updated Gcode instance
        
        """
        print("Self", repr(self))
        print("Other", repr(other))
        
        other.command = self.command        # store the last used command
        
        # remove any of the items that we don't want to pass onto other commands
        for item in ("comment", "unknown", "skeinforge"):
            if item in other.parameters.keys():
                del other.parameters[item] 

        if self.X is None:
            self.X = other.X
        else:
            other.X = self.X

        if self.Y is None:
            self.Y = other.Y
        else:
            other.Y = self.Y

        if self.Z is None:
            self.Z = other.Z
        else:
            other.Z = self.Z

        if self.E is None:
            self.E = other.E
        else:
            other.E = self.E

        if self.F is None:
            self.F = other.F
        else:
            other.F = self.F

        if self.T is None:
            self.T = other.T

        for key in other.parameters.keys():                                     # pass the other's settings to the command...
            self.parameters.setdefault(key, other.parameters[key])              # (ignore if the key is in parameters; otherwise, add the other key/value pair)
        for key in other.parameters.keys():                                     # .... and update other values with those of the latest command
            other.parameters[key] = self.parameters[key]


class Extruder:
    """Extruder objects store information and can process a .gcode file. 
    
    Each member of the 'extruder' class stores information of a .gcode file,
    and has some methods to process this information. 
    
    Variables:
        name            :   the name for the extruder, like 'Ultimaker' or 'Extruder 2'
        rawGcode        :   the Gcode commands are stored in a list, line by line
        commands        :   the processed Gcode commands are stored in a list.
        
        One may assume that the index position of the 'rawGcode' and 'commands' 
        lists point to the same command. Thus, 'myExtruder.rawGcode[4]' gives
        the Gcode command in the 5th line of the imported .gcode file, and 
        'myExtruder.commands[4]' stores the processed command. 
    """

    def __init__(self, name='Extruder'):
        """Initialize a new member of the 'extruder' class"""
        self.name = name
        self.rawGcode = []                                                      # list to store raw Gcode
        self.standardGcode = []                                                 # extract the recognized gcode commands

    def __repr__(self):
        """returns a representation of a 'extruder' object"""
        return """<Extruder object
        * name: {0.name}
        * rawGcode: {1} lines
        * commands: {2} lines>
        """.format(self, len(self.rawGcode), len(self.standardGcode))


    def import_rawGcode(self, filename):
        """Import a '*.gcode' file into the 'extruder' instance.
        
        This method reads a *.gcode file into memory, and stores each line
        in the self.rawGcode list. From here, it can be used for later processing.
        
        filename    :   a file that contains the .gcode commands
        """
        with open(filename, mode='rt') as gcodeFile:
            for line in gcodeFile:
                line = line.strip()                                             # remove trailing whitespace, including '\n'
                self.rawGcode.append(line)
        print("OK: Import of .gcode for '{0}' has finished".format(self.name))


    def convert_rawGcode_to_standardGcode(self):
        """Transform each line of a .gcode file to a standardized (5D) command.

        This function takes a list of lines of raw gcode imput (e.g., from 
        the 'import_rawGcode' method). Each line is then processed sequentually by 
        doing the following:
        
        1. Create a new 'Gcode' instance;
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
        
        After processing, each Gcode instance is checked against their 
        Reprap Gcode, since the command might modify a parameter. 
        Example: 'G28' tells to set X,Y,Z to (0,0,0).          
        """

        lineNr = 0                                                              # keep track of the current line number
        for line in self.rawGcode:
            lineNr += 1
            
            # 1. create a new 'Gcode' instance
            currCommand = Gcode(name=lineNr)

            # 2. check if the line contains Skeinforge-code. 
            if line.startswith('(<'):                                           # Assumes that first character is always and only '(<'
                line = line[1:-1]                                               # remove brackets '()'
                currCommand.command = "skeinforge"
                currCommand.parameters["skeinforge"] = line
                self.standardGcode.append(currCommand)                               # add to the list of commands
                continue
            
            # 3. Ignore everything to the right of ';'
            if ';' in line:
                currCommand.parameters["comment"] = line.split(";", 1)[1].strip()       # all to the right of ";" is a comment
                line = line.split(";", 1)[0].strip()                                    # remainder is useable command

            # 3. Ignore comments marked by '(..)'
            if '(' in  line:
                currCommand.parameters["comment"] = line.split("(", 1)[1].strip(";)")   # All to the right of '(' is a comment
                line = line.split("(")[0].strip()

            # 3. There is the chance that the whole line is a comment.
            #    In that case, grab the raw gcode, and insert this line as a comment
            if len(line) == 0:
                currCommand.command = "comment"
                currCommand.parameters["comment"] = self.rawGcode[lineNr-1].strip(";()")
                self.standardGcode.append(currCommand)                               # add to the list of commands
                continue

            # 4. Store the 'command' parameter (the first code in the line)
            commands = line.strip().split(" ")
            if commands[0] in Reprap_Gcode.reprapGcodes.keys():                              # this line starts with a valid code
                currCommand.command = commands[0].strip()                       # add command name; remove any double white space as some Gcode has two whitespaces
                for item in commands[1:]:
                    if item[0] == "X":
                        currCommand.X = float(item[1:].strip())
                    elif item[0] == "Y":
                        currCommand.Y = float(item[1:].strip())
                    elif item[0] == "Z":
                        currCommand.Z = float(item[1:].strip())
                    elif item[0] == "E":
                        currCommand.E = float(item[1:].strip())
                    elif item[0] == "F":
                        currCommand.F = float(item[1:].strip())
                    elif item[0] == "T":
                        currCommand.T = int(item[1:].strip())
                    else:
                    # for every of the parameters, make the first character the
                    # key, and add the remaining characters (excl. whitespace)
                        currCommand.parameters[item[0]] = float(item[1:].strip())
            else:
                # the command is not in the list of Gcodes, treat as comment
                print(">> Line {0}: unrecognized Gcode in '{1}'".format(lineNr, line.strip()))
                currCommand.command = "unknown"
                currCommand.parameters["comment"] = commands

            self.standardGcode.append(currCommand)                                   # Add the created Gcode instance to the list of commands
        
        # Send each of the created commands to its function, to check if there
        # is any extra operation or action that must be done to the command.
        for cmd in self.standardGcode:
            if cmd.command in Reprap_Gcode.reprapGcodes.keys():                
                cmd = Reprap_Gcode.reprapGcodes[cmd.command](cmd)

        # Up to here, we have read all the raw Gcode commands, and transformed
        # these to standardized 'Gcode' instances. 
        # As a final step, we have to process all the commands and add the
        # last-known parameters (which are stored in extruder memory) to each
        # of these commands.
        # Example: line 1 = G1 X2 Y2 Z2 E10 F10
        #          line 2 = G1 Y4
        #           --> the X, Z, E, and F positions are not modified in line #2, 
        #               and can be transferred from line #1. 
        lastState = self.create_lastState("lastState")

        for cmd in self.standardGcode:
            cmd.update_state(lastState)
        print("OK: Gcode commands for '{0}' have been expanded with previous values".format(self.name))


    def export_standardGcde(self, outFile = '/home/douwe/Desktop/output.gcode'):
        """
        Reconstruct raw Gcode commands from processed, standardized Gcode commands.
        
        This method will return all the 'Gcode' instances as strings.
        It should return functional equivalents of the original raw Gcode command.

        return  :   file (that contains reconstructed gcode commands)
        """
        
        with open(outFile, mode = 'w') as gcodeOutFile:
            for indexNr in range(0, len(self.standardGcode)):                
                gcodeOutFile.write(self.standardGcode[indexNr].name + " " + str(self.standardGcode[indexNr]) + "\n")


    def add_offset(self, offsetX = 1000, offsetY = 1000):
        """Add offset values to extruder's X and Y coordinates
        """
        
        for command in self.standardGcode:
            if command.X is not None:
                command.X += offsetX
            if command.Y is not None:
                command.Y += offsetY

        print("OK: offset ({0}, {1}) added to extruder '{2}'".format(offsetX, offsetY, self.name))
        

    def create_lastState(self, name="lastState_T0"):
        """Create an empty 'last state' Gcode instance
        
        This function returns a Gcode with empty parameters
        """
        lastState = Gcode(name)
        lastState.X = 0.0
        lastState.Y = 0.0
        lastState.Z = 0.0
        lastState.E = 0.0
        lastState.F = 0.0
        lastState.T = 0
        lastState.parameters = {'units':None,                                       # working unit: mm, inch
                                'extruderTemp':None,                                # extruder temperature
                                'extruderPWM':None,                                 # extruder temp. set by PWM
                                'absolutePos':None,                                 # is positioning absolute (True), relative (False)
                                'fan':False}                                        # is the fan on (True) or off (False)
        return lastState


    def debug_extruder(self, outFileName = "/home/douwe/Desktop/debug_extruder.txt"):
        """Aid with debugging extruder data: save all data to a text file.
        
        Note that the 'merge_extruders' code only returns 'standardGcode' 
        commands and not 'rawGcode' commands, hence a test for the presence
        of 'len(rawGcode) > 0'
        """
        
        with open(outFileName, mode = "wt") as outFile:
            for indexNr in range(len(self.standardGcode)):
                if len(self.rawGcode) > 0:
                    outFile.write("r -- {0} --\t".format(indexNr + 1) + str(self.rawGcode[indexNr]) + "\n")
                outFile.write("s -- {0} --\t".format(indexNr + 1) + str(self.standardGcode[indexNr]) + "\n\n")



class Machine:
    """'Machine' instances hold information about a machine.
    
    A Machine aims to mimick the real physiological state of an actual
    3D printer, that is able to process Gcode commands in a certain way.
    
    A Machine can hold one or more 'extruder' heads, and each 'extruder' heads
    in turn stores individual Gcode commands. 
    """
    
    def __init__(self, name = "Ultimaker"):
        """Initialization of the Machine instance"""
        self.name = name
        self.extruders = list()
    
    
    def __repr__(self):
        """Representation of a Machine instance"""
        return "<Machine instance '{0}', with {1} extruders".format(self.name, len(self.extruders))


    def add_extruder(self, gcodeFile):
        """Attach an extruder head to the current machine.
        
        Add extruder information to the current machine. The extruder is 
        filled with gcode data that is saved in the 'gcodeFile' file. 
        If the file exists, an attempt is made to: 
            (1) load the file;
            (2) transform the raw gcode to standardized Gcode instances 
        """

        extruderName = "extruder_" + str(len(self.extruders) + 1)
        self.extruders.append(Extruder(name = extruderName))
        
        # (1) load the gcode data from file
        try:
            self.extruders[-1].import_rawGcode(gcodeFile)        
        except IOError:
            print("ERROR: the file '{0}' is not found. Is this a valid .gcode file?".format(gcodeFile))

        #(2) parse the raw gcode commands, and turn them into 'Gcode' instances 
        self.extruders[-1].convert_rawGcode_to_standardGcode()


    def merge_extruders(self, line1, line2):
        """Merge the gcode commands of two extruder heads.
        
        Gcode commands are added in two steps. 
        
        The first step aims to capture all the 'initialization' commands for
        both files. That is, the repositioning of the location ('G92', 'G28'), 
        information on the units ('G21') etc. This 'initialization' process 
        must be given as a line number. For example, if the initialization commands
        are from lines 1 to 13 of a .gcode file, enter the last line (13) here.
        
        The second step assumes that these are the actual commands where the 
        printing takes place, and that for these, Z-values go up (i.e., from 0 
        to more positive values).    
    
        Variables:
        line1, line2          :   the last line of the 'initialization' phase for each file
        
        return      :   a new 'extruder' instance
                        ... that stores the Gcode instances of both extruders
        """
        print("TODO: entering the 'merge_extruders' function")
        # assume that it's the first and second extruders that will be merged
        extruder1 = self.extruders[0]
        extruder2 = self.extruders[1]
 
        # add a new extruder in which the merged commands will be stored
        self.extruders.append(Extruder(name = "merged"))
        newExtruder = self.extruders[-1]
        countX = 1              # bookkeeping for convenient line numbering

        # Step 1. Add initialization state commands for both extruders
        #       1a. add a T0 command 
        newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
        countX += 1
        newExtruder.standardGcode[-1].command = "T0"
        newExtruder.standardGcode[-1].parameters["comment"] = "** extruder 1 Initialization start **"
        newExtruder.standardGcode[-1].T = 0
        
        #       1b. add the other initialization commands for extruder 1
        for index in range(0, line1):
            newExtruder.standardGcode.append(extruder1.standardGcode[index])
            newExtruder.standardGcode[-1].name = "a_" + str(extruder1.standardGcode[index].name)
            newExtruder.standardGcode[-1].T = 0        # we are extruder 1, now
        
        #       1c. add a closing comment for extruder 1
        newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
        countX += 1
        newExtruder.standardGcode[-1].command = "comment"
        newExtruder.standardGcode[-1].parameters["comment"] = "** extruder 1 Initialization end **"
        newExtruder.standardGcode[-1].T = 0
        
        #       1c. add a T1 command for extruder 2
        newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
        countX += 1
        newExtruder.standardGcode[-1].command = "T1"
        newExtruder.standardGcode[-1].parameters["comment"] = "** extruder 2 Initialization start **"
        newExtruder.standardGcode[-1].T = 1

        #       1d. add the other initialization commands for extruder 2
        for index in range(0, line2):
            newExtruder.standardGcode.append(extruder2.standardGcode[index])
            newExtruder.standardGcode[-1].name = "b_" + str(extruder2.standardGcode[index].name)
            newExtruder.standardGcode[-1].T = 1        # we are extruder 2, now

        #       1e. add the closing comment for extruder 2
        newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
        countX += 1
        newExtruder.standardGcode[-1].command = "comment"
        newExtruder.standardGcode[-1].parameters["comment"] = "** extruder 2 Initialization end **"
        newExtruder.standardGcode[-1].T = 1
    

        # Step 2: merge the remainder of the code
        #   first, find the Z values of extruder1 and extruder2 
        Zvalues = set()
        for indexNr in range(line1 - 1, len(extruder1.standardGcode)):
            Zvalues.add(extruder1.standardGcode[indexNr].Z)
        for indexNr in range(line2 - 1, len(extruder2.standardGcode)):
            Zvalues.add(extruder2.standardGcode[indexNr].Z)
        Zvalues.discard(None)                                                   # Remove any 'None' type, if present
        Zvalues = sorted(list(Zvalues))                                         # ... and sort the Z-values in a list
        print("Z-values: ", Zvalues)

        lastStateExtruder1 = extruder1.standardGcode[line1]
        lastStateExtruder2 = extruder2.standardGcode[line2]

        print("laststate 1", lastStateExtruder1, "line1:", line1)
        
        for Zval in Zvalues:
            # assumption: the gcode commands are from lowest to highest Z-value
            if extruder1.standardGcode[line1].Z == Zval:
                print(">> Now processing Zval:", Zval)
                
                # add a T0 command, then the other commands until no more Zval
                newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
                countX += 1
                newExtruder.standardGcode[-1].command = "T0"
                newExtruder.standardGcode[-1].parameters["comment"] = "** switch to T0 **"
                
                while extruder1.standardGcode[line1].Z == Zval:
#                    print("line1", line1, extruder1.commands[line1])
                    newExtruder.standardGcode.append(extruder1.standardGcode[line1])
                    newExtruder.standardGcode[-1].T = 0
                    newExtruder.standardGcode[-1].name = "a_" + str(newExtruder.standardGcode[-1].name)
                    if line1 == len(extruder1.standardGcode) - 1:
                        break
                    else:
                        line1 += 1
            
            if extruder2.standardGcode[line2].Z == Zval:
                print(">> Now processing Zval for extr.2", Zval)

                # add a T1 command, then the other commands until no more Zval
                newExtruder.standardGcode.append(Gcode(name="x_" + str(countX)))
                countX += 1
                newExtruder.standardGcode[-1].command = "T1"
                newExtruder.standardGcode[-1].parameters["comment"] = "** switch to T1 **"
                
                while extruder2.standardGcode[line2].Z == Zval:
                    newExtruder.standardGcode.append(extruder2.standardGcode[line2])
                    newExtruder.standardGcode[-1].T = 1
                    newExtruder.standardGcode[-1].name = "b_" + str(newExtruder.standardGcode[-1].name)
                    if line2 == len(extruder2.standardGcode) - 1:
                        break
                    else:
                        line2 += 1

        print("OK: merge code processed successfully")


# ----- the body of the program -----
def main():
    """Main code of the Gcode reader. 
    
    This code will only execute if the script is executed directly. Otherwise,
    this code is ignored (e.g., to facilitate import as a module)
    """

    # create a extruder (stores commands)
    inFile1 = '/home/douwe/compile/github/blender-gcode-reader/testFiles/line_L.gcode'
    inFile2 = '/home/douwe/compile/github/blender-gcode-reader/testFiles/line_R.gcode'

    Ultimaker = Machine()
    Ultimaker.add_extruder(inFile1)        # add extruder 1
    Ultimaker.add_extruder(inFile2)        # add extruder 2
#    print(Ultimaker)

#    Ultimaker.extruders[-1].debug_extruder()
#    for i in Ultimaker.extruders[0].commands:
#        print(repr(i))

    Ultimaker.merge_extruders(11, 11)
    Ultimaker.extruders[-1].debug_extruder()

#    Ultimaker.extruders[-1].export_standardGcde()
    
#    Ultimaker.extruders[1].add_offset()
    
#    for i in Ultimaker.extruders[2].commands:
#        print(repr(i))



if __name__ == "__main__":
    main()
