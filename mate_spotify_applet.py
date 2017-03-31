#!/usr/bin/python2.7
# -*- coding:utf-8 -*-
 
# ensure we are using Gtk 2, not Gtk3
# this will print a warning but everything should work

# PyGObject (PyGI). GObject Introspection
# https://git.gnome.org//browse/pygobject

import gi
gi.require_version("Gtk", "2.0")
gi.require_version('MatePanelApplet', '4.0')
 
from gi.repository import Gtk, Gdk
from gi.repository import GdkPixbuf
from gi.repository import MatePanelApplet

import subprocess
import time
import sys
import os
import requests
from gi.repository import GLib

# LOGGING
import logging
import logging.handlers

LOG_FILENAME = '/home/gabriel/dev/dbus_spotify/applet.log'

# Set up a specific logger with our desired output level
_log = logging.getLogger('Mate_Spotify_Applet_Logger')
_log.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=40000000, backupCount=5)

#handler = logging.handlers.SysLogHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to handler
handler.setFormatter(formatter)

_log.addHandler(handler)

# THREADING STUFF
import threading
 
class FuncThread(threading.Thread):
    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self)
 
    def run(self):
        self._target(*self._args)

def update_image(metas, win):
    '''
    Update tooltip window image.
    Requires a request to the web, and the requests library is blocking.
    Calling this function through the FuncThread Class seems to be the easiest
    way to asynchronously fetch the image and update the widget
    '''
    _log.debug('inside update_image thread')

    artUrl = metas['mpris:artUrl'].format().encode('utf-8')

    # PixbufLoader loads asynchronously, unlike GtkImage
    img_data = requests.get(artUrl)
    if not img_data:
        return
    pl = GdkPixbuf.PixbufLoader()
    pl.write(img_data.content)

    _log.debug('setting new image')
    win.img.set_from_pixbuf(pl.get_pixbuf())
    pl.close()

    # update url held by tooltip window
    win.artUrl = artUrl

# DBUS STUFF
import dbus

# we need this to be able to listen for signals (dbus event loop)
# see https://github.com/zyga/dbus-python/blob/master/examples/example-signal-recipient.py
import dbus.mainloop.glib as dbml
dbml.DBusGMainLoop(set_as_default=True)

# Spotify DBUS destination (well known name) and path
obj_dest="org.mpris.MediaPlayer2.spotify"
obj_path="/org/mpris/MediaPlayer2"

methods_path="org.mpris.MediaPlayer2.Player"
props_path = 'org.freedesktop.DBus.Properties'

#bus = dbus.SystemBus()
bus = dbus.SessionBus()

# call dbus methods, get dbus properties
player_iface = None
properties_iface = None

# GTK STUFF
from gi.repository import Pango
LABEL_SIZE = 150

# images
play_img = Gtk.Image()
pause_img = Gtk.Image()
next_img = Gtk.Image()
prev_img = Gtk.Image()
tt_img = Gtk.Image()

# gtk widgets
but_play_pause = Gtk.Button()
but_prev = Gtk.Button()
but_next = Gtk.Button()
song_label = Gtk.Label()
song_label.set_alignment(xalign=0, yalign=0.5) # left aligh
song_label.set_size_request(LABEL_SIZE, -1) # fixed size
song_label.set_ellipsize(Pango.EllipsizeMode.END)

class TTWin(object):

    def __init__(self):
        self.win = Gtk.Window(Gtk.WindowType.POPUP)
        self.img = Gtk.Image()
        self.artUrl = None

        color = Gdk.Color(9000, 11000, 13000)
        self.win.modify_bg(Gtk.StateType.NORMAL, color)
        # labels
        self.sng_lb = Gtk.Label()
        self.alb_lb = Gtk.Label()
        self.art_lb = Gtk.Label()

        xpad, ypad = 10, 10 
        self.sng_lb.set_label('[Song Name]')
        self.sng_lb.set_padding(xpad=xpad, ypad=ypad)
        self.alb_lb.set_label('[Album Name]')
        self.alb_lb.set_padding(xpad=xpad, ypad=ypad)
        self.art_lb.set_label('[Artists Names]')
        self.art_lb.set_padding(xpad=xpad, ypad=ypad)
        self.sng_lb.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(65255,65255,65255))
        self.alb_lb.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(65255,65255,65255))
        self.art_lb.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(65255,65255,65255))

        # boxes and packing
        hbox = Gtk.HBox(homogeneous=False, spacing=0)
        vbox = Gtk.VBox(homogeneous=False, spacing=0)

        vbox.pack_start(self.sng_lb, False, False, 0)
        vbox.pack_start(self.alb_lb, False, False, 0)
        vbox.pack_start(self.art_lb, False, False, 0)

        hbox.pack_start(self.img, False, False, 0)
        hbox.pack_start(vbox, False, False, 0)

        # set the window not (user_) resizable,
        # to allow gtk to resize it when the labels shrink.
        # it WON'T do it if the window is user resizable.
        self.win.set_resizable(False)
        self.win.add(hbox)

        # Have to .show() everything here, or it won't work.
        # The hbox, vbox, and all the elements
        hbox.show()
        vbox.show()
        self.img.show()
        self.sng_lb.show()
        self.alb_lb.show()
        self.art_lb.show()

    def set_image(self, image):
        self.img = image

    def set_song(self, song):
        self.sng_lb.set_label(song)

    def set_album(self, album):
        self.alb_lb.set_label(album)

    def set_artists(self, artists):
        self.art_lb.set_label(artists)


#TTWin
tt_win = TTWin()

def play_pause(widget, event, props_iface):
    props_iface.PlayPause()
    return

def next_func(widget, event, props_iface):
    props_iface.Next()
    return

def prev_func(widget, event, props_iface):
    props_iface.Previous()
    return

def properties_handler(wk_name, data, array, sender=None):
    '''
    dbus calls this handler with
    wk_name : well_know_name of dbus object
    data : dict with infos and Metadatas (result of Properties Get Metadatas)
    array : some array (?)
    '''

    _log.debug("properties_handler")

    metas = data['Metadata']
    status = data['PlaybackStatus'].format().encode('utf-8')
    trackNum = metas['xesam:trackNumber'].real
    length = metas['mpris:length'].real

    album = metas['xesam:album'].format().encode('utf-8')
    artists = [x.format().encode('utf-8') for x in metas['xesam:artist']]
    artists = ', '.join(artists)
    title = metas['xesam:title'].format().encode('utf-8')

    # update play_button image
    new_img = pause_img if status == 'Playing' else play_img
    but_play_pause.set_image(new_img)
    #but_play_pause.show()
    #new_img.show()

    # update song name. -1 keeps height automatic
    song_label.set_label(title)
    song_label.show()

    # update tt stuff
    tt_win.sng_lb.set_label(title)
    tt_win.alb_lb.set_label(album)
    tt_win.art_lb.set_label(artists)

    # fixme: we already do this in the thread, refactor to send it
    # as argument
    artUrl = metas['mpris:artUrl'].format().encode('utf-8')

    if tt_win.artUrl != artUrl:
        image_thread = FuncThread(update_image, metas, tt_win)
        image_thread.start()

    # if we join, we'll actually wait for the thread to finish
    # to return from this dbus handler. We don't want that..
    #image_thread.join()


def query_tooltip_custom_cb(widget, x, y, keyboard_tip, tooltip):

    window = widget.get_tooltip_window()
    
    #_log.debug("tooltip callback called")
    #sys.stdout.flush()
   
    return True


def applet_fill(applet):

    # you can use this path with gio/gsettings
    settings_path = applet.get_preferences_path()

    # Mate launched the applet with a cwd of '/',
    # so we have to do this in order to find where our resources are
    ourpath = os.path.dirname(os.path.realpath(__file__))

    # load images
    play_img.set_from_file(ourpath+"/res/play.png")
    pause_img.set_from_file(ourpath+"/res/pause.png")
    next_img.set_from_file(ourpath+"/res/next.png")
    prev_img.set_from_file(ourpath+"/res/prev.png")

    tt_img.set_from_pixbuf(play_img.get_pixbuf())

    hbox = Gtk.HBox(homogeneous=False, spacing=0)

    # play_pause
    #but_play_pause.connect("button_release_event", play_pause,
    #        applet, player_iface)
    but_play_pause.set_image(play_img)
    but_play_pause.set_sensitive(False)
    hbox.add(but_play_pause)
    play_img.show()
    but_play_pause.show()

    #prev
    #but_prev.connect("button_release_event", prev_func,
    #        applet, player_iface)
    but_prev.set_image(prev_img)
    but_prev.set_sensitive(False)
    hbox.add(but_prev)
    prev_img.show()
    but_prev.show()

    #next
    #but_next.connect("button_release_event", next_func,
    #        applet, player_iface)
    but_next.set_image(next_img)
    but_next.set_sensitive(False)
    hbox.add(but_next)
    next_img.show()
    but_next.show()

    # label, tooltip connection
    song_label.set_label('No Spotify')
    hbox.add(song_label)
    song_label.show()

    # fill applet, and show
    applet.add(hbox)
    applet.show_all()

def name_owner_changed_handler(one, two, three, sender, dest, interface, 
        member, path, message):
    '''
    For NameOwnerChanged, one is the past name, three is the new name.
    If one = spotify and three = '' (empty string), it means spotify has quit.
    (it changed it's owner name to nothingness).
    '''
    _log.debug('NameOwnerChanged Handler Called !')
    _log.debug("ONE : %s", one)
    _log.debug("TWO : %s", two)
    _log.debug("THREE : %s", three)

    if not (one == 'org.mpris.MediaPlayer2.spotify' and three == ''):
        return

    _log.debug('Spotify has quit, starting reset process..')
    # then, we unwire UI, remove the disconnect callback,
    # reconnect the catchall callback. That's it.
    unwire_interface()
    remove_name_owner_changed_handler()
    plant_catchall()

def unwire_interface():
    _log.debug('unwire_interface')

    #remove all callbacks from buttons

    #set all ui unsensitive
    but_play_pause.set_visible(False)
    but_play_pause.set_sensitive(False)
    but_prev.set_visible(False)
    but_prev.set_sensitive(False)
    but_next.set_visible(False)
    but_next.set_sensitive(False)

    #disconnect tooltip window
    #set text as no spotify
    song_label.set_label('No Spotify')

    #remove Gtk signal handlers
    but_play_pause.disconnect_by_func(play_pause)
    but_prev.disconnect_by_func(prev_func)
    but_next.disconnect_by_func(next_func)

    # remove tooltip window connection
    song_label.set_tooltip_window(None)
    song_label.disconnect_by_func(query_tooltip_custom_cb)
    song_label.props.has_tooltip = False
    # remove signal receivers
    #properties_iface.connect_to_signal("PropertiesChanged", properties_handler, sender_keyword='sender')
    # I don't know how to disconnect the handler, so setting them to none
    # hopefully makes it so the objects are GCed and have to be recreated at 
    # next wire_interface call
    properties_iface = None
    player_iface = None


def plant_name_owner_changed_handler():
    bus.add_signal_receiver(name_owner_changed_handler,
            path = "/org/freedesktop/DBus",
            sender_keyword = "sender",
            destination_keyword = "dest",
            interface_keyword = "interface",
            member_keyword = "member",
            path_keyword = "path",
            message_keyword = "message",
            signal_name = "NameOwnerChanged")
    _log.debug('name_owner_changed handler has been planted')

def remove_name_owner_changed_handler():
    bus.remove_signal_receiver(name_owner_changed_handler,
            path="/org/freedesktop/DBus")

def wire_interface():
    '''
    connects the UI to the callbacks and events.
    connect the handlers to the DBus callbacks.
    called when DBUS gets on.
    '''
    _log.debug('wire_interface')
    proxy = bus.get_object(obj_dest, obj_path)
    player_iface = dbus.Interface(proxy,
            dbus_interface=methods_path)
    properties_iface = dbus.Interface(proxy,
            dbus_interface=props_path)
    #bus.call_on_disconnection(disconnect)

    # NameLost seems to not be sent on all systems...
    # signal time=1490139156.297933 sender=org.freedesktop.DBus -> destination=:1.106 serial=5 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus;
    # member=NameLost
    # string "org.mpris.MediaPlayer2.spotify"
    # Plant handler !
    plant_name_owner_changed_handler()

    # initial song, album, artist for the tooltip window
    metas = properties_iface.Get(methods_path, 'Metadata')
    song = metas['xesam:title'].format().encode('utf-8')
    album = metas['xesam:album'].format().encode('utf-8')
    artists = [x.format().encode('utf-8') for x in metas['xesam:artist']]
    artists = ', '.join(artists)

    # initial status and thus image
    status = properties_iface.Get(methods_path, 'PlaybackStatus')
    initial_img = pause_img if status == 'Playing' else play_img

    # activate buttons, connect them to their callbacks
    but_play_pause.set_visible(True)
    but_play_pause.set_sensitive(True)
    # set image after setting sensitive, otherwise 
    # the image will appear as if it was insensisive on next interface update,
    # and until the button is hovered. We don't want that
    but_play_pause.set_image(initial_img)
    but_play_pause.connect("button_release_event", play_pause,
            player_iface)
    but_prev.set_visible(True)
    but_prev.set_sensitive(True)
    but_prev.connect("button_release_event", prev_func,
            player_iface)
    but_next.set_visible(True)
    but_next.set_sensitive(True)
    but_next.connect("button_release_event", next_func,
            player_iface)

    # tooltip window
    tt_win.set_song(song)
    tt_win.set_album(album)
    tt_win.set_artists(artists)

    # song_label, tooltip window connection
    song_label.set_label(song)
    song_label.set_tooltip_window(tt_win.win)
    song_label.connect('query-tooltip', query_tooltip_custom_cb)
    song_label.props.has_tooltip = True

    # launch image updating thread
    image_thread = FuncThread(update_image, metas, tt_win)
    image_thread.start()

    # Install handler to catch the PropertiesChanged signal sent by spotify everytime some property changes
    properties_iface.connect_to_signal("PropertiesChanged", properties_handler, sender_keyword='sender')


def catchall_handler(one, two, three, sender, dest, inter, member):

    _log.debug('CATCHALL CALLED')
    _log.debug(one)
    _log.debug(two)
    _log.debug(three)
    _log.debug(sender)
    _log.debug(dest)
    _log.debug(inter)
    _log.debug(member)

    # we caught what we wanted, remove the handler
    remove_catchall()

    _log.debug('going to wire interface ...')
    wire_interface()

def plant_catchall():

    bus.add_signal_receiver(catchall_handler,
            path = "/org/mpris/MediaPlayer2",
            sender_keyword = "sender",
            destination_keyword = "dest",
            interface_keyword = "inter",
            member_keyword = "member")
            #dbus_interface = "org.freedesktop.DBus.Properties",
            #signal_name = "PropertiesChanged")
    _log.debug('catchall signal has been planted')

def remove_catchall():
    bus.remove_signal_receiver(catchall_handler,
            path="/org/mpris/MediaPlayer2")
    _log.debug('catchall signal handler has been removed ...')

#ipython gives a warning GObject.MainLoop is deprecated, 
#to use GLib.MainLoop instead
#loop = GObject.MainLoop()
loop = GLib.MainLoop()

def on_destroy(applet):
    _log.debug('on_destroy called')
    _log.debug('on_destroy : removing catchall handler')
    remove_catchall()
    _log.debug('on_destroy : quitting GLib loop')
    loop.quit()

def applet_factory(applet, iid, data):
    if iid != "MateSpotifyApplet":
       return False

    # fill the widgets, without connecting anything
    applet_fill(applet)

    applet.connect("destroy", on_destroy)
    # check for DBus
    # if we can't get the proxy to the object, it most likely doesn't exist, i.e.
    # spotify is not launched or "dbus" is messed up, i.e spotify was launched
    # from something like "guake" that seems to act like a dbus jail.
    # so we set a catchall, to catch when spotify comes on in DBus
    try:
        proxy = bus.get_object(obj_dest, obj_path)
        wire_interface()
    except Exception as e:
        _log.debug("Could not get proxy object to Spotify, planting handler to listen when it comes on on DBus")
        # _log.critical(e)
        remove_catchall()
        plant_catchall()

        # the bug at removal/readding of widget my be caused by the 
        # quit the loop just in case (paranoia)
        loop.quit()
        loop.run()
        return True

    return True

MatePanelApplet.Applet.factory_main("MateSpotifyAppletFactory", True,
        MatePanelApplet.Applet.__gtype__,
        applet_factory, None)

