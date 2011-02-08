#    Author : Clement Houtmann
#    Copyright (C) 2011 Clement Houtmann
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import sys
import binascii
import string
import pickle
import os
import subprocess
import Image
import random
import cStringIO

import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import gobject

GTKCOLOR = ['#000000', '#0000FF', '#00FF00', '#FF0000']
COLOR = [(242, 241, 240), (0, 0, 255), (0, 255, 0), (255, 0, 0)]

PKG_SIZE = 1024
CHR_SIZE = 512

###############
# CONVERSIONS #
###############

# conversion from hex string to binary string
# ex: 'a2' -> '1010010'
def hst2bst(hStr):
    resu = ''
    for ch in hStr:
        n = string.atoi(ch, base=16)
        bStr= ''
        while n > 0:
            bStr = str(n % 2) + bStr
            n = n >> 1
        while len(bStr)<4:
            bStr = '0' + bStr
        resu = resu + bStr
    return resu

# convert a binary string '010110111...' intro an 8x8 4-colored matrix
def bst2spr(mystr):
    # 8x8 matrix
    return [[string.atoi(mystr[8*i + j]) + 2 * string.atoi(mystr[64 + 8*i + j])
        for j in range(8)] for i in range(8)]

def hst2spr(hSt):
    return bst2spr(hst2bst(hSt))

# convert an 8x8 4-colored matrix intro a binary string '010110111...'
# inverse of bst2spr
def spr2bst(mysprite):
    result = ['0']*128
    for i in range(8):
        for j in range(8):
            if mysprite[i][j] == 0:
                result[8*i+j], result[64+ 8*i + j] = '0','0'
            elif mysprite[i][j] == 1:
                result[8*i+j], result[64+ 8*i + j] = '1','0'
            elif mysprite[i][j] == 2:
                result[8*i+j], result[64+ 8*i + j] = '0','1'
            else:
                result[8*i+j], result[64+ 8*i + j] = '1','1'
    return ''.join(result)

# conversion from binary string to hex string
# ex: '1010010' -> 'a2'
def bst2hst(bstr):
    if len(bstr) < 4: return ''
    else:    
        enc = [repr(i) for i in range(10)] + ['a','b','c','d','e','f']
        return enc[string.atoi(bstr[:4], base=2)] + bst2hst(bstr[4:])

# conversion from hex string to 8x8 sprite
def spr2hst(spr):
    return bst2hst(spr2bst(spr))

# conversion from 8x8 sprite to hex string
def bin2spr(buffer):
    return hst2spr(binascii.b2a_hex(buffer))

def spr2bin(spr):
    return binascii.a2b_hex(spr2hst(spr))

def spr2image(spr, scale=1):
    im = Image.new('RGB',(8,8))
    pix = im.load()
    for x,line in enumerate(spr):
        for y,pixel in enumerate(line):
    #for a in range(scale):
    #    for b in range(scale):
            pix[y,x] = COLOR[pixel]
    im2 = im.resize((scale*8,scale*8), Image.NEAREST)
    return im2
 

def image_to_pixbuf (image):
    file = cStringIO.StringIO ()
    image.save (file, 'png')
    contents = file.getvalue()
    file.close ()
    loader = gtk.gdk.PixbufLoader ('png')
    loader.write (contents, len (contents))
    pixbuf = loader.get_pixbuf ()
    loader.close ()
    return pixbuf

def spr2pixbuf(spr, scale=1):
    return image_to_pixbuf(spr2image(spr, scale)) 

######################
# Class for files    #
######################

class Nesrom:
    sprList = []
    puzzles = {}

    def import_rom(self, filename):
        #self.filename = filename
        self.puzzles = {}
        self.sprList = []
        with open(filename, 'r') as f:
            buffer=f.read(16)
            while buffer != '':
                self.sprList.append(buffer)
                buffer=f.read(16)

    def get_offset(self):
        if self.sprList == []:
            return 0
        else:
            return (PKG_SIZE *
                string.atoi(binascii.b2a_hex(self.sprList[0][4]), base=16))+1

######################
# GTK contants       #
######################

MAIN_WINDOW = 'window1'
PUZZLE_LIST = 'treeview1'
PUZZLE_AREA = 'layout1'
#SPRITE_LIST = 'treeview2'
SPRITE_AREA = 'layout2'
GLADE_FILE = 'ned.glade'
STATUS_BAR = 'statusbar3'
TRASH = 'scrolledwindow2'
SAVEFILEENTRY = 'entry1'
SAVEREP = 'filechooserbutton1'
EDITBUTTON = 'toolbutton8'

FILE_CHOOSER = 'filechooserdialog1'
NEWFILE_CHOOSER = 'dialog1'

ROM = 'rom'
DUMP = 'dump'
PNG = 'png'

FSTROW = 0
LSTROW = 1
FSTCOL = 2
LSTCOL = 3

TARGET_TYPE_PLACEHOLDER = 80
TARGET_TYPE_TRASH = 81
from_image = [ ( "text/plain", 0, TARGET_TYPE_PLACEHOLDER ),
               ( "trash", 0, TARGET_TYPE_TRASH ) ]
to_image = [ ( "text/plain", 0, TARGET_TYPE_PLACEHOLDER ) ]
to_trash = [ ( "trash", 0, TARGET_TYPE_TRASH ) ]



###############
# GTK program #
###############

class GTKeditor:
    def __init__(self):
        self.mainwindow = gtk.glade.XML(GLADE_FILE, MAIN_WINDOW)
        self.filechooser = gtk.glade.XML(GLADE_FILE, FILE_CHOOSER)
        self.newfilechooser = gtk.glade.XML(GLADE_FILE, NEWFILE_CHOOSER)
        self.spritearea = self.mainwindow.get_widget(SPRITE_AREA)
        self.puzzlearea = self.mainwindow.get_widget(PUZZLE_AREA)
        self.puzzlelist_treeview = self.mainwindow.get_widget(PUZZLE_LIST)
        self.editbutton = self.mainwindow.get_widget(EDITBUTTON)
        self.statusbar = self.mainwindow.get_widget(STATUS_BAR)
        self.nesrom = None
        self.cache = {}
        self.currentZone = 0
        self.scale=6
        self.perline = 10
        self.length=10
        self.editbox = gtk.DrawingArea()

        self.editbox.connect("expose-event", self.updateEditBox)
        self.editbox.set_size_request(100,100)

        self.puzzlearea.put(self.editbox, 0, 0)

        # enable button events on editbox
        self.editbox.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_MOTION_MASK)
        self.editbox.connect('button-press-event', self.editSprite)
        self.editbox.connect('motion-notify-event', self.editSprite)

        # initialize events
        events = {
            # for menu:
            'delete': self.quit,
            'openDumpFile': self.openDumpFile,
            'saveDumpFile': self.saveDumpFile,
            'importRom': self.importRom,
            'exportRom': self.exportRom,
            'exportImage': self.exportImage ,
            'exportAllImages': self.notImplemented ,
            'importImage': self.notImplemented ,
            'importAllImages': self.notImplemented ,
            'about': self.notImplemented ,
            # for puzzle list buttons
            'newPuzzle': self.newPuzzle ,
            'deletePuzzle' : self.deletePuzzle ,
            # for puzzle area buttons
            'addFstRow' : self.addFstRow ,
            'addLstRow' : self.addLstRow ,
            'addFstCol' : self.addFstCol ,
            'addLstCol' : self.addLstCol ,
            'editModeChange' : self.editModeChange ,
            # for sprite area buttons
            'previousSpriteZone' : self.previousSpriteZone,
            'nextSpriteZone' : self.nextSpriteZone,
            # for file dialog:
            'closeOpenDialog' : self.closeOpenDialog ,
            'closeSaveDialog' : self.closeSaveDialog ,
            'openfile' : self.openfile,
            'savefile' : self.savefile,
            # for clicking on puzzle treeview:
            'displayPuzzle' : self.displayCurrentPuzzle,
            }
        self.mainwindow.signal_autoconnect(events)
        self.newfilechooser.signal_autoconnect(events)
        self.filechooser.signal_autoconnect(events)
        # avoid to destroy the FC when the WM deletes it
        fc = self.filechooser.get_widget(FILE_CHOOSER)
        fc.connect('delete-event', fc.hide_on_delete)
        nfc = self.newfilechooser.get_widget(NEWFILE_CHOOSER)
        nfc.connect('delete-event', nfc.hide_on_delete)
        # initialize trasharea as trash receiver
        trasharea = self.mainwindow.get_widget(TRASH)
        trasharea.connect('drag_data_received', self.getImage)
        trasharea.drag_dest_set(gtk.DEST_DEFAULT_ALL
                                    , to_trash , gtk.gdk.ACTION_COPY)

        self.mainwindow.get_widget(MAIN_WINDOW).show_all()
 
    #############
    # Callbacks #
    #############

    # not implemented callback
    def notImplemented(self, source=None, event=None):
        print 'feature not implemented yet'

    # Quit callback
    def quit(self, source=None, event=None):
        gtk.main_quit()
        print 'exiting'

    # previous spritezone callback
    def previousSpriteZone(self, source=None, event=None):
        # BOUUUUH UGLY
        try:
            self.currentZone = self.currentZone - (self.perline * self.length)
            self.displaySpritZone()
        except NameError:
            pass

    # next spritezone callback
    def nextSpriteZone(self, source=None, event=None):
        # BOUUUUH UGLY
        try:
            self.currentZone = self.currentZone + (self.perline * self.length)
            self.displaySpritZone()
        except NameError:
            pass

    # new first Row callback
    def addFstRow(self, source=None, event=None):
        self.extendCurrentPuzzle(FSTROW)

    # new last Row callback
    def addLstRow(self, source=None, event=None):
        self.extendCurrentPuzzle(LSTROW)

    # new first Col callback
    def addFstCol(self, source=None, event=None):
        self.extendCurrentPuzzle(FSTCOL)

    # new last Col callback
    def addLstCol(self, source=None, event=None):
        self.extendCurrentPuzzle(LSTCOL)

    # new Puzzle callback
    def newPuzzle(self, source=None, event=None):
        if self.nesrom == None:
            self.outputmsg('error: open dump or load Rom first')
        else:
            counter = 1
            newname = 'New Puzzle '+str(counter)
            while newname in self.nesrom.puzzles:
                counter = counter+1
                newname = 'New Puzzle '+str(counter)
            self.nesrom.puzzles[newname] = [[-1]]
            # puts puzzle list in treeview
            self.updatePuzzleList()

    # delete puzzle callback
    def deletePuzzle(self, source=None, event=None):
        if self.nesrom == None:
            self.outputmsg('error: open dump or load Rom first')
        else:
            puzzlename = self.getCurrentPuzzle()
            if puzzlename == None:
                self.outputmsg('error: can\'t delete puzzle if none is selected')
            else:
                # update nesrom
                del self.nesrom.puzzles[puzzlename]
                # update treeview
                self.updatePuzzleList()
                # update puzzlearea
                for child in self.puzzlearea.get_children():
                    self.puzzlearea.remove(child)
                self.puzzlearea.put(self.editbox, 0, 0)

    # Open Dump File callback
    def openDumpFile(self, source=None, event=None):
        self.filechooser.filetype = DUMP
        self.outputmsg('choose a dump file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

    # import ROM callback
    def importRom(self, source=None, event=None):
        self.filechooser.filetype = ROM
        self.outputmsg('choose a rom file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

    # Save Dump File callback
    def saveDumpFile(self, source=None, event=None):
        if self.nesrom == None:
            self.outputmsg('Nothing to save...')
        else:
            self.newfilechooser.filetype = DUMP
            self.outputmsg('choose a dump file')
            self.newfilechooser.get_widget(NEWFILE_CHOOSER).show()

    # export ROM callback
    def exportRom(self, source=None, event=None):
        if self.nesrom == None:
            self.outputmsg('Nothing to save...')
        else:
            self.newfilechooser.filetype = ROM
            self.outputmsg('choose a rom file')
            self.newfilechooser.get_widget(NEWFILE_CHOOSER).show()

    # export image callback
    def exportImage(self, source=None, event=None):
        puzzlename = self.getCurrentPuzzle()
        if self.nesrom == None or puzzlename == None:
            self.outputmsg('should select something first...')
        else:
            self.newfilechooser.filetype = PNG
            self.outputmsg('choose a png file')
            self.newfilechooser.get_widget(NEWFILE_CHOOSER).show()

# TODO : deprecated
    # Open File dialog callback
#    def openFileDialog(self, source=None, event=None, flag=None):
#        self.filechooser.filetype = flag
#        self.filechooser.get_widget(FILE_CHOOSER).show()

    # Close File dialog callback
    def closeOpenDialog(self, source=None, event=None):
        self.filechooser.get_widget(FILE_CHOOSER).hide()

    # Close Save dialog callback
    def closeSaveDialog(self, source=None, event=None):
        self.newfilechooser.get_widget(NEWFILE_CHOOSER).hide()

    # callback when the treeview is edited
    def treeview_edited(self, cellrenderedtext, path, newtext, liststore, column):
        oldtext = liststore[path][column]
        self.outputmsg ( '{0} -> {1}'.format(oldtext, newtext))
        if oldtext != newtext and newtext != '':
            self.nesrom.puzzles[newtext] = self.nesrom.puzzles[oldtext]
            del self.nesrom.puzzles[oldtext]
            liststore[path][column] = newtext
            self.displayCurrentPuzzle()
        self.updateCache()

    # Save file callback
    def savefile(self, source=None, event=None):
        self.closeSaveDialog()
        filetype = self.newfilechooser.filetype
        name = self.newfilechooser.get_widget(SAVEFILEENTRY).get_text()
        filerep = self.newfilechooser.get_widget(SAVEREP).get_filename()
        filename = filerep + '/' + name

        if name == '':
            self.outputmsg('Provide name please')

        elif os.path.exists(filename):
            self.outputmsg('File exists!')

        # save dump file
        elif filetype == DUMP:
            with open(filename, 'w') as f:
                pickle.dump(self.nesrom, f)

        # export rom
        elif filetype == ROM:
            with open(filename, 'w') as f:
                for line in self.nesrom.sprList:
                    f.write(line)

        elif filetype == PNG:
            puzzlename = self.getCurrentPuzzle()
            if self.nesrom == None or puzzlename == None:
                self.outputmsg('should select something first...')
            else:
                if filename[-4:] == '.png':
                    image = self.puzzle_to_image(self.nesrom.puzzles[puzzlename], scale=1)
                    image.save(filename)
                    self.outputmsg('image saved to '+filename)
                else:
                    self.outputmsg('error: filname must end with ".png"')
            


    # Open File callback -> when filechooser clicked 'ok'
    def openfile(self, source=None, event=None):
        self.closeOpenDialog()
        filetype = self.filechooser.filetype
        filename = self.filechooser.get_widget(FILE_CHOOSER).get_filename()

        # open dump file
        if filetype == DUMP:
            with open(filename, 'r') as f:
                self.nesrom = pickle.load(f)
            self.outputmsg(os.path.basename(filename) +
                            ' loaded: ' +
                            str(len(self.nesrom.puzzles)) +
                            'puzzles found')

        # open rom
        elif filetype == ROM:
            # construct new rom
            self.nesrom = Nesrom()
            self.nesrom.import_rom(filename)
            self.outputmsg(os.path.basename(filename) +
                            ' loaded: ' +
                            str(len(self.nesrom.sprList)) +
                            'sprites found')

        ######################################################
        # This last part of the function displays the nesrom #
        ######################################################

        # puts puzzle list in treeview
        self.updatePuzzleList()
        # clear puzzlelayout
        for child in self.puzzlearea.get_children():
            self.puzzlearea.remove(child)
        self.displaySpritZone()

    # callback when showing editbox
    def updateEditBox(self, area=None, event=None):
        puzzlename = self.getCurrentPuzzle()
        if puzzlename != None:
            currentpuzzle = self.nesrom.puzzles[puzzlename]
            width = len(currentpuzzle[0])
            height = len(currentpuzzle)
            self.editbox.set_size_request(width*8*self.scale, height*8*self.scale)
            style = self.editbox.get_style()
            self.gc = gtk.gdk.GC(self.editbox.window)
            pixbuf = image_to_pixbuf(self.puzzle_to_image(currentpuzzle, self.scale))
            self.editbox.window.draw_pixbuf(self.gc, pixbuf, 0, 0, 0, 0, -1, -1)
            self.editbox.window.draw_point(self.gc, 30, 30)


    # Callback to display current puzzle
    def displayCurrentPuzzle(self, treeview=None):
        puzzlename = self.getCurrentPuzzle()
        if puzzlename != None:
            currentpuzzle = self.nesrom.puzzles[puzzlename]
            self.outputmsg('displaying ' + puzzlename)
            for child in self.puzzlearea.get_children():
                self.puzzlearea.remove(child)
            self.puzzlearea.put(self.editbox, 0, 0)
            width = self.scale*8*len(currentpuzzle[0])
            height = self.scale*8*len(currentpuzzle)
            self.puzzlearea.set_size(width, height)
            for i,line in enumerate(currentpuzzle):
                for j, sprnum in enumerate(line):
                    if 0<sprnum<len(self.nesrom.sprList):
                        eventbox = self.displaySprite(self.puzzlearea,
                                            sprnum,
                                            self.scale,
                                            self.scale*8*j,
                                            self.scale*8*i,
                                            True, i, j, puzzlename, from_image)
                    else:
                        eventbox = self.displaySprite(self.puzzlearea,
                                            sprnum,
                                            self.scale,
                                            self.scale*8*j,
                                            self.scale*8*i,
                                            False, i, j, puzzlename, from_image)
            if self.editbutton.get_active():
                for child in self.puzzlearea.get_children():
                    child.hide()
                self.editbox.show()
            else:
                self.puzzlearea.show_all()
                self.editbox.hide()
            # TODO : bin2spr has already been called in displaySprite... redundant
            self.updateCache()

    # callback when editing sprite
    def editSprite(self, widget, event):
        print event.state
        # verify the edit mode on
        if self.editbutton.get_active():
            x,y = event.get_coords()
            puzzlename = self.getCurrentPuzzle()
            # verify if a puzzle is selected
            if puzzlename != None:
                currentpuzzle = self.nesrom.puzzles[puzzlename]
                width = len(currentpuzzle[0])
                height = len(currentpuzzle)
                if 0<x<width*8*self.scale and 0<y<height*8*self.scale:
                    # fast version
                    a, b =  (int(x/self.scale), int(y/self.scale))
                    i, j = a/8, b/8
                    u, v = a%8, b%8
                    sprnum = currentpuzzle[j][i]
                    colormap = self.editbox.get_colormap()
                    if (event.state & gtk.gdk.MOD1_MASK):
                        newval = 3
                    elif event.state & gtk.gdk.SHIFT_MASK:
                        newval = 2
                    elif event.state & gtk.gdk.CONTROL_MASK:
                        newval = 1
                    else:
                        newval = 0
                    mycolor = colormap.alloc_color(GTKCOLOR[newval], True, True)
                    mygc = self.editbox.window.new_gc(foreground = mycolor)
                    if 0<sprnum<len(self.nesrom.sprList):
                        # change image
                        for p,line in enumerate(currentpuzzle):
                            for q,sprnum2 in enumerate(line):
                                if sprnum == sprnum2:
                                    self.editbox.window.draw_rectangle(
                                        mygc,
                                        True,
                                        ((q*8)+u)*self.scale,
                                        ((p*8)+v)*self.scale,
                                        self.scale, self.scale)
                        # update cache
                        self.cache[sprnum][v][u] = newval

                    # slow version
#                    spr = bin2spr(self.nesrom.sprList[sprnum])
#                    spr[v][u] = 0
#                    self.nesrom.sprList[sprnum] = spr2bin(spr)
#                    self.updateEditBox()

    # callback when toggling the edit button
    def editModeChange(self, togglebutton):
        if self.editbutton.get_active():
            self.outputmsg('edit mode on')
            # turn to edit mode
            #self.updateEditBox()
            for child in self.puzzlearea.get_children():
                child.hide()
            self.editbox.show()
                #child.handler_unblock_by_func(self.editSprite)
        else:
            # go back to unedit mode
            self.flushCache()
            self.displaySpritZone()
            self.outputmsg('edit mode off')
            self.displayCurrentPuzzle()
            for child in self.puzzlearea.get_children():
                child.show_all()
            self.editbox.hide()


    # callback for sender in Drag&Drop
    def sendImage(self, widget, context, selection, targetType, eventTime):
        if targetType == TARGET_TYPE_TRASH: # moved to trash
            (puzzlename, posx, posy) = widget.data
            # update nesrom
            self.nesrom.puzzles[puzzlename][posx][posy] = -1
            # update widget
            for child in widget.get_children():
                widget.remove(child)
            self.putSprInWidget(widget, -1, 6)
            self.setDestWidget(widget, puzzlename, posx, posy)
            widget.show_all()
            selection.set(selection.target, 8, str(widget.data))
        else: # send to placeholder
            # send sprite info
            selection.set(selection.target, 8, str(widget.number))

    # callback for receiver in Drag&Drop
    def getImage(self, widget, context, x, y, selection, targetType,time):
        if targetType == TARGET_TYPE_PLACEHOLDER:
            (puzzlename, posx, posy) = widget.data
            newsprnum = string.atoi(selection.data)
            self.outputmsg('replacing sprite {1}, {2} in {0} by {3} -> {4}'.format(
                puzzlename,
                posx,
                posy,
                newsprnum,
                self.nesrom.puzzles[puzzlename]))
            # update nesrom
            self.nesrom.puzzles[puzzlename][posx][posy] = newsprnum
            # update widget
            for child in widget.get_children():
                widget.remove(child)
            pixbuf = self.putSprInWidget(widget, newsprnum, 6)
            self.setSourceWidget(widget, newsprnum, pixbuf, from_image)
            self.setDestWidget(widget, puzzlename, posx, posy)
            widget.show_all()
        else:
            self.outputmsg ( 'erasing ' + selection.data )
 
    ################################
    # Defining Drag & Drop widgets #
    ################################

    # Define a Widget as Source for Drag&Drop (usually an EventBox)
    def setSourceWidget(self, eventbox, sprnum, pixbuf, flags):
        eventbox.number = sprnum
        eventbox.pixbuf = pixbuf
        eventbox.connect('drag_data_get', self.sendImage)
        eventbox.drag_source_unset()
        if not self.editbutton.get_active():
            eventbox.drag_source_set(gtk.gdk.BUTTON1_MASK, flags, gtk.gdk.ACTION_COPY)
            eventbox.drag_source_set_icon_pixbuf(pixbuf)

    # Define a Widget as Destination for Drag&Drop (usually an EventBox)
    def setDestWidget(self, eventbox, puzzlename, posx, posy):
        eventbox.data = (puzzlename, posx, posy)
        eventbox.connect('drag_data_received', self.getImage)
        eventbox.drag_dest_unset()
        eventbox.drag_dest_set(gtk.DEST_DEFAULT_ALL
                                    , to_image , gtk.gdk.ACTION_COPY)


    ######################
    # Displaying methods #
    ######################

    def updateCache(self):
        puzzlename = self.getCurrentPuzzle()
        currentpuzzle = self.nesrom.puzzles[puzzlename]
        self.cache = {}
        for line in currentpuzzle:
            for sprnum in line:
                self.cache[sprnum] = bin2spr(self.nesrom.sprList[sprnum])

    def flushCache(self):
        puzzlename = self.getCurrentPuzzle()
        currentpuzzle = self.nesrom.puzzles[puzzlename]
        for sprnum in self.cache:
            self.nesrom.sprList[sprnum] = spr2bin(self.cache[sprnum])
        

    def extendCurrentPuzzle(self, flag):
        if self.nesrom == None:
            self.outputmsg('error: open dump or load Rom first')
        else:
            puzzlename = self.getCurrentPuzzle()
            if puzzlename == None:
                self.outputmsg('error: can\'t add row to puzzle if none is selected')
            else:
                currentpuzzle = self.nesrom.puzzles[puzzlename] 
                if flag == FSTROW:
                    self.nesrom.puzzles[puzzlename] = ([[-1]* len(currentpuzzle[0])] +
                                                        currentpuzzle)
                elif flag == LSTROW:
                    self.nesrom.puzzles[puzzlename] = (currentpuzzle +
                                                        [[-1]* len(currentpuzzle[0])])
                elif flag == FSTCOL:
                    for i,line in enumerate(currentpuzzle):
                        currentpuzzle[i] = [-1] + line
                else: # flag == LSTCOL:
                    for i,line in enumerate(currentpuzzle):
                        currentpuzzle[i] = line + [-1]
                self.displayCurrentPuzzle()



    # print SpritZone
    def displaySpritZone(self):
        # variables to be modified later...
        offset = self.nesrom.get_offset()
        # delete everything in it !
        for child in self.spritearea.get_children():
            self.spritearea.remove(child)
        # initialize size variables
        if (self.currentZone < offset or
                self.currentZone> len(self.nesrom.sprList)):
            self.currentZone = offset
        maxspr = min(self.currentZone+self.length*self.perline, len(self.nesrom.sprList))
        self.spritearea.set_size(self.perline*self.scale*8,
            (maxspr-self.currentZone)*8*self.scale/self.perline)
        # now let's draw !
        for sprnum in range(self.currentZone, maxspr):
            eventbox = gtk.EventBox()
            pixbuf = self.putSprInWidget(eventbox, sprnum, self.scale)
            eventbox.pixbuf = pixbuf
            self.setSourceWidget(eventbox, sprnum, pixbuf, to_image)
            index = sprnum - self.currentZone
            self.spritearea.put(eventbox,
                            8*self.scale*(index - self.perline*(index/self.perline)),
                            self.scale*8*(index/self.perline))
        self.spritearea.show_all()


    # update puzzlelist
    def updatePuzzleList(self):
        self.putListInTreeview(self.puzzlelist_treeview,
                                self.nesrom.puzzles.keys(),
                                'Puzzles')

    # write a list in a Treeview Widget
    def putListInTreeview(self, treeview, mylist, title,
                            datatype=gobject.TYPE_STRING):
        # set model of Puzzle list
        liststore = gtk.ListStore(datatype)
        # remove columns
        col0 = treeview.get_column(0)
        while col0 != None:
            treeview.remove_column(col0)
            col0 = treeview.get_column(0)
        # add column:
        C_DATA_COLUMN_NUMBER_IN_MODEL = 0
        cell0 = gtk.CellRendererText()
        cell0.set_property('editable', True)
        cell0.connect('edited', self.treeview_edited, liststore,0)
        col0 = gtk.TreeViewColumn(title, cell0,    
                            text=C_DATA_COLUMN_NUMBER_IN_MODEL)
        treeview.append_column(col0)
        treeview.set_model(liststore)
        treeview.set_reorderable(True)
        for x in mylist:
            liststore.append([x])

    # get current puzzle
    def getCurrentPuzzle(self):
        return self.getTreeviewSelected(self.puzzlelist_treeview)

    # get selected value in a Treeview Widget
    def getTreeviewSelected(self, treeview):
        treeselection = treeview.get_selection()
        #treeselection.set_mode(gtk.SELECTION_SINGLE)
        (model, iter) = treeselection.get_selected()
        if iter == None: return None
        else: return model.get_value(iter, 0)


    # general method for outputing a message in the statusbar
    def outputmsg(self, message):
        cid = self.statusbar.get_context_id('Messages')
        self.statusbar.push(cid, message)

    # Print a sprite in a Widget (usually an EventBox)
    def putSprInWidget(self, eventbox, sprnum, scale=1):
        gtkimage = gtk.Image()
        #pixbuf = image_to_pixbuf(self.puzzle_to_image([[sprnum]], scale))
        if 0<=sprnum<len(self.nesrom.sprList):
            pixbuf = spr2pixbuf(bin2spr(self.nesrom.sprList[sprnum]), scale)
        else:
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 8*scale, 8*scale)
            pixbuf.fill(int('00000022', 16))
        gtkimage.set_from_pixbuf(pixbuf)
        eventbox.add(gtkimage)
        return pixbuf

    # Turns a puzzle into an Image
    def puzzle_to_image(self,puzzle, scale=1):
        width, height = len(puzzle[0]), len(puzzle)
        # save to temp file
        im = Image.new('RGBA',(scale*8*width,scale*8*height), (0,0,0,34))
        pix = im.load()
        for i,sprLine in enumerate(puzzle):
            for j,sprnumber in enumerate(sprLine):
                if 0<=sprnumber<len(self.nesrom.sprList):
                    for x,line in enumerate(
                        bin2spr(self.nesrom.sprList[sprnumber])):
                        for y,pixel in enumerate(line):
                            for a in range(scale):
                                for b in range(scale):
                                    pix[a+scale*(8*j+y),b+scale*(8*i+x)] = COLOR[pixel]
        return im

    # Displays a sprite in a widget
    def displaySprite(self, widget, sprnum, scale, x, y, 
                         # infos for late instanciation
                        source, posx, posy, puzzlename, flags):
        eventbox = gtk.EventBox()
        # get pixbuf for icon of sourcewidget
        pixbuf = self.putSprInWidget(eventbox, sprnum, scale)
        eventbox.pixbuf = pixbuf
        self.setDestWidget(eventbox, puzzlename, posx, posy)
        if source:
            self.setSourceWidget(eventbox, sprnum, pixbuf, flags)
        widget.put(eventbox, x, y)
        return eventbox

 
###################################
# launch editor from command line #
###################################
      
if __name__ == '__main__':
    app = GTKeditor()
    gtk.main()

