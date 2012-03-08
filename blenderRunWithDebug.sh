#!/bin/bash

# Runs a blender installation in /Applications via commandline with debug output

# By Winter Guerra (XtremD)
# Release under the Creative Commons CC_BY_SA license
# March 1st, 2012

blenderInstallLocation=/Applications/Blender_2.62_x64/blender.app/Contents/MacOS

echo Opening blender at $blendersInstallLocation

#Show work
echo $blenderInstallLocation/./blender

#Execute Blender
$blenderInstallLocation/./blender
