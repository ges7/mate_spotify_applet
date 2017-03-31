#!/bin/bash
# to run as root

# check if we are in the right directory to do anything
if [ ! -f ./mate_spotify_applet.py ]; then
    echo "mate_spotify_applet.py not found in this folder !"
    echo "Launch the install from the root folder : sudo ./install.sh"
    exit
fi

MANIFEST='./files/org.mate.panel.MateSpotifyApplet.mate-panel-applet'
MANIFEST_DEST='/usr/share/mate-panel/applets/'

DBUS_FILE='./files/org.mate.panel.applet.MateSpotifyAppletFactory.service'
DBUS_DEST='/usr/share/dbus-1/services/'

LOC=$(readlink -f ./mate_spotify_applet.py)

# escape the string to be able to feed it in sed
LOC=$(sed -e 's/[\/&]/\\&/g' <<< $LOC)
#echo "loc escaped is :" $LOC

sed -i "s/^Location=.*$/Location=$LOC/g" $MANIFEST
sed -i "s/^Exec=.*$/Exec=$LOC/g" $DBUS_FILE

# mate 'manifest'
cp $MANIFEST $MANIFEST_DEST

# dbus service file (generic for applets in Mate)
cp $DBUS_FILE $DBUS_DEST

# icon
cp ./files/mate-spotify-applet-icon.svg /usr/share/icons/hicolor/scalable/apps/mate-spotify-applet-icon.svg

cp ./files/mate-spotify-applet-icon-48x48.png /usr/share/icons/hicolor/48x48/apps/mate-spotify-applet-icon.png

cp ./files/mate-spotify-applet-icon-32x32.png /usr/share/icons/hicolor/32x32/apps/mate-spotify-applet-icon.png

update-icon-caches /usr/share/icons/*

