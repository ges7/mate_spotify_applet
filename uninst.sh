#!/bin/bash
# to run as root


MANIFEST='org.mate.panel.MateSpotifyApplet.mate-panel-applet'
MANIFEST_DEST='/usr/share/mate-panel/applets/'

DBUS_FILE='org.mate.panel.applet.MateSpotifyAppletFactory.service'
DBUS_DEST='/usr/share/dbus-1/services/'

# mate manifest
rm $MANIFEST_DEST$MANIFEST

# dbus service file
rm $DBUS_DEST$DBUS_FILE

# icons
rm /usr/share/icons/hicolor/scalable/apps/mate-spotify-applet-icon.svg

rm /usr/share/icons/hicolor/48x48/apps/mate-spotify-applet-icon.png

rm /usr/share/icons/hicolor/32x32/apps/mate-spotify-applet-icon.png

