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
#	firstHead = request.forms.firstHead
	secondFile = request.files.secondGcodeFile
#	secondHead = request.forms.secondHead

#	print("Input 1:", firstFile.file, type(firstFile), type(firstFile.file))
#	print("*************")

	with open(BOTTLE_TMP_FOLDER + "/" + firstFile.filename, mode="wt") as outFile1:
		for line in firstFile.file:
			outFile1.write(line.decode("utf-8"))

	with open(BOTTLE_TMP_FOLDER + "/" + secondFile.filename, mode="wt") as outFile2:
		for line in secondFile.file:
			outFile2.write(line.decode("utf-8"))



			
#	print("Input 2:", firstHead)
#	print("Input 3:", secondFile.filename)
#	print("Input 4:", secondHead)



	#if firstHead == "Douwe":
		#return "<p>Hello, Douwe!</p>"
	#else:
		#return """<p>Is there someone else <a href="merge_gcodes.html">here</a> ?</p>"""
	
	
	


#@app.route("/login", method="GET") 
#def login_form():
    #return """<form method="POST">
                #<input name="name"     type="text" />
              #</form>"""

#def check_login(name):
    #if name == "douwe":
        #return True
    #else:
        #return False


#@app.route('/login', method="POST") # or @route('/login', method='POST')
#def login_submit():
    #name     = request.forms.get("name")
    #if check_login(name):
        #return "<p>Your login was correct</p>"
    #else:
        #return "<p>Login failed</p>"
        



debug(True) # this stops caching of the templates
run(app, reloader=True) # NB reloader=True geeft twee instances van Bottle, zie de handleiding!
