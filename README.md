Blender GCode Reader Add-on 
===========================
Reads 3D printing gcode files (such as for Ultimaker, RepRap, Makerbot) into blender 2.6 for visualization


Instructions:
-------------
1. Get latest version of Blender here: http://www.blender.org/download/get-blender/
   (This script works for Blender 2.63.4 (rev. 46312) 

2. Create a folder in your local blender addon scripts folder.
   Example: /home/appultaart/.blender/2.63/scripts/addons/3d_print

3. Copy at minimum the three files to this folder:
   "__init__.py", "Blender_import_gcode.py", and "Gcode_parser.py"
   
3. Open Blender

4. Navigate to:
	File Menu
	User Preferences (CTL-ALT-U)
	Select The Add-Ons Tab
    Select the Import-Export category
    Select the "Import Gcode for 3D printers" Add-on
	CLick the "Enable Add-on" checkbox to the right of the Add-on slot 
	(Click "Save As Default" if you want the Add-on to always be available)

4. The Add-On is accessible from two locations:
    - File --> Import --> Import 2D printer Gcode
    or
    - In the Tools panel (in 3D View, press 'T' to toggle panel).
    
    Select a file and watch the console for progress. The import process is slow, CPU intensive,  and may take a long time.
    Any errors are printed to the console; check here.

5. Bask in the glory of your awesome small plastic thing.



History:
--------
* Modified by Alessandro Ranellucci (2011-10-14)
  to make it compatible with Blender 2.59
  and with modern 5D GCODE

* Modified by Winter Guerra (XtremD) on February 16th, 2012
  to make the script compatable with stock Makerbot GCode files
  and grab all nozzle extrusion information from Skeinforge's machine output
  WARNING: This script no longer works with stock 5D GCode! (Can somebody please integrate the two versions together?)
  A big shout-out goes to my friend Jon Spyreas for helping me block-out the maths needed in the "addArc" subroutine
  Thanks a million dude!
  Github branch link: https://github.com/xtremd/blender-gcode-reader

* Modified by Douwe van der Veen (appultaart), 2012
  A major overhaul of the original script: the processing of Gcode, and the Blender-
  specific code have been separated into two files. In addition, a panel interface
  for within Blender has been added to make possible to change various settings 
  (such as, whether to use a bevel object, etc). 
  
  Because of the file split, this project is treated as a multi-file addon now:
    - __init__.py: required for 'multi-file' addon. Contains the Blender GUI and
                   menu entry code. All interactions with Blender are placed in here.
    - Gcode_parser.py: this file contains all information to parse a Gcode file. 
    - Blender_import_gcode.py: this file contains all tools needed to process 
                               imported Gcode in Blender, convert this code to 
                               Blender BezierCurves, add a bevel opject, etc.
                               
  All modifications are tested with Gcode generated for an Ultimaker 3D printer,
  yet the file split and code organization should make all machine-independent 
  (this is not yet tested).
  
  Developed at ProtoSpace / FabLab Utrecht: thanks for hospitality! 
  Thanks to Jelle Boomstra for help and advice with software and hardware.
  
  Github branch link: https://github.com/appultaart/blender-gcode-reader


Original developer:
-------------------
Simon Kirkby
tigger@interthingy.com
