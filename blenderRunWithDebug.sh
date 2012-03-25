#!/bin/bash

# Runs a blender installation in /Applications via commandline with debug output

# By Winter Guerra (XtremD)
# Release under the Creative Commons CC_BY_SA license

SearchDirectory="/Applications"

#Can we find the blender install location by regexing /Applications ? Why not?
blenderInstallLocation=$(ls -p $SearchDirectory | grep -i 'blender.*2\.6.*/')

numberOfBlenders=$(echo "$blenderInstallLocation" | wc -l)
#echo "$numberOfBlenders"

#Check if there is more than 1 possible install location and throw a warning if so
if [ $numberOfBlenders \> 1 ]; then

#Argh! Panic!!
echo "Argh! More than one installation directories were found in $SearchDirectory!"
echo "$blenderInstallLocation"
echo "Aborting!"

exit 1
fi

echo "Opening blender executable at $SearchDirectory/$blenderInstallLocation"

#Show work
echo "$SearchDirectory/${blenderInstallLocation}blender.app/Contents/MacOS/./blender"

#Execute Blender
$SearchDirectory/${blenderInstallLocation}blender.app/Contents/MacOS/./blender
