#!/bin/bash

# Runs a blender installation in /Applications via commandline with debug output

# By Winter Guerra (XtremD)
# Release under the Creative Commons CC_BY_SA license
# March 1st, 2012

SearchDirectory="/Applications"

#Can we find the blender install location by regexing /Applications ? Why not?
blenderInstallLocation=$(ls -p $SearchDirectory | grep -i 'blender.*2\.6.*/')

#Check if there is more than 1 possible install location and throw a warning if so
if [ $(wc -l $blenderInstallLocation) > "1" ]; then
echo "Arg! More than one install location found in $SearchDirectory !"
exit 1
fi

#TODO: Ask the user to choose which is the installation folder and save it in a config file.

echo "Opening blender executable at $SearchDirectory/$blenderInstallLocation"

#Show work
echo "$SearchDirectory/${blenderInstallLocation}blender.app/Contents/MacOS/./blender"

#Execute Blender
$SearchDirectory/${blenderInstallLocation}blender.app/Contents/MacOS/./blender
