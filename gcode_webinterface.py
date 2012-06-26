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
Web interface to the Gcode parser.

The primary purpose of this web interface is to create a platform-independent,
easy to use, communication with an end user who has the aim to merge two
Gcode files into a single (dual-extrusion) file.

Author: Douwe van der Veen ('appultaart') : https://github.com/appultaart/blender-gcode-reader/
"""


# ----- import -----
from bottle import TEMPLATE_PATH, Bottle, Route, route, run, debug, template, request, validate, static_file, error, default_app, get, post
import Gcode_parser


# ----- constants and variables -----
BOTTLE_TEMPLATE_FOLDER = "./webInterface/templates"
BOTTLE_STATIC_FOLDER = "./webInterface/static"
BOTTLE_TMP_FOLDER = "./webInterface/tmp"
BOTTLE_HTML_FOLDER = "./webInterface"


# add template path folder to Bottle's search path to make life easier.
TEMPLATE_PATH.append(BOTTLE_TEMPLATE_FOLDER)


# ----- initiate a Bottle instance -----
app = Bottle()


# ----- routes -----
# show the main page
@app.route("/", method="GET")
@app.route("/index.html", method="GET")
def show_IndexPage():
    return static_file("index.html", root = BOTTLE_HTML_FOLDER)


# static files such as images are requested through this route
@app.route("/static/<filepath:path>")
def server_static(filepath):
	return static_file(filepath, root = BOTTLE_STATIC_FOLDER)


# the Gcode merge process is processed here
@app.route("/merge_gcodes.html", method = "GET")
def form_GET_mergeGcodes():
	return static_file("merge_gcodes.html", root = BOTTLE_HTML_FOLDER)

@app.route("/merge_gcodes.html", method = "POST")
def form_POST_mergeGcodes():
	firstFile = request.files.data
	firstHead = request.forms.firstHead
	secondFile = request.files.secondGcodeFile
	secondHead = request.forms.secondHead

	checkForCorrectEntries = ""
	continueProcessing = True
	if firstFile is "":
		checkForCorrectEntries += "<p>Please select a first .gcode file to merge</p><br>"
		continueProcessing = False
	if secondFile == "":
		checkForCorrectEntries += "<p>Please select your second .gcode file to merge</p><br>"
		continueProcessing = False
	if firstHead == "":
		checkForCorrectEntries += "<p>Please add a number where the first .gcode file starts its header</p><br>"
		continueProcessing = False
	if secondHead == "":
		checkForCorrectEntries += "<p>Please add a number where the second .gcode file starts its header</p><br>"
		continueProcessing = False
			
	if continueProcessing is False:
		return checkForCorrectEntries
	
	else:
		# CREATE an Ultimaker Machine
		Ultimaker = Gcode_parser.Machine()
		print("Activated an Ultimaker virtual machine")
		
		# Add the first extruder, process the 'firstFile', and convert to standardGcode
		Ultimaker.extruders.append(Gcode_parser.Extruder(name = firstFile.filename))
		currentExtruder = Ultimaker.extruders[-1]	
		# process 'firstFile'
		for line in firstFile.file:
			line = line.decode("utf-8")
			line = line.strip()
			currentExtruder.rawGcode.append(line)	
		print("Ultimaker Gcode #1 has been added successfully")
		# convert raw Gcode to standard Gcode
		currentExtruder.convert_rawGcode_to_standardGcode()
		print("Current extruder {0}, converted successfully".format(currentExtruder.name))


		# Add the second extruder, process the 'secondFile', and convert to standardGcode
		Ultimaker.extruders.append(Gcode_parser.Extruder(name = secondFile.filename))
		currentExtruder = Ultimaker.extruders[-1]	
		# process 'secondFile'
		for line in secondFile.file:
			line = line.decode("utf-8")
			line = line.strip()
			currentExtruder.rawGcode.append(line)	
		print("Ultimaker Gcode #1 has been added successfully")		
		# convert raw Gcode to standard Gcode
		currentExtruder.convert_rawGcode_to_standardGcode()
		print("Current extruder {0}, converted successfully".format(currentExtruder.name))
	

	    ## correct for the gcode centering
	    #Ultimaker.extruders[1].add_offset(offsetX = 10, offsetY = 10)
	    #Ultimaker.extruders[1].add_offset(offsetX = 0, offsetY = 22)

	##    Ultimaker.extruders[-1].debug_extruder()
	##    for i in Ultimaker.extruders[0].commands:
	##        print(repr(i))


		Ultimaker.merge_extruders(int(firstHead), int(secondHead))
		Ultimaker.extruders[-1].debug_extruder()

		Ultimaker.extruders[-1].export_standardGcode(outFile = BOTTLE_TMP_FOLDER + "/merge_result.gcode")
    
		return "<p>Merging was successfull, and is saved in file '{0}'</p>".format(BOTTLE_TMP_FOLDER + "/merge_result.gcode")





debug(True) # this stops caching of the templates
run(app, reloader=True) # NB reloader=True geeft twee instances van Bottle, zie de handleiding!
