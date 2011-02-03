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
import StringIO

import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import gobject

COLOR = [(242, 241, 240), (0, 0, 255), (0, 255, 0), (255, 0, 0)]

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

def image_to_pixbuf (image):
    file = StringIO.StringIO ()
    image.save (file, 'ppm')
    contents = file.getvalue()
    file.close ()
    loader = gtk.gdk.PixbufLoader ('pnm')
    loader.write (contents, len (contents))
    pixbuf = loader.get_pixbuf ()
    loader.close ()
    return pixbuf


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

FILE_CHOOSER = 'filechooserdialog1'

ROM_OPEN = 'rom_open'
ROM_SAVE = 'rom_save'
DUMP_OPEN = 'dump_open'
DUMP_SAVE = 'dump_save'

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
        self.nesrom = None
    	# initialize events
        events = {
            # for menu:
            'delete': self.quit,
            'openDumpFile': self.openDumpFile,
            'saveDumpFile': self.saveDumpFile,
            'importRom': self.importRom,
            'exportRom': self.exportRom,
            'exportImage': self.notImplemented ,
            'exportAllImages': self.notImplemented ,
            'importImage': self.notImplemented ,
            'importAllImages': self.notImplemented ,
            'zoom': self.notImplemented ,
            'dezoom': self.notImplemented ,
            'colors': self.notImplemented ,
            'about': self.notImplemented ,
            # for puzzle buttons
            'newPuzzle': self.newPuzzle ,
            'deletePuzzle' : self.notImplemented ,
            # for file dialog:
            'closeFileDialog' : self.closeFileDialog ,
            'openfile' : self.openfile,
            # for clicking on puzzle treeview:
            'displayPuzzle' : self.displayCurrentPuzzle,
            }
        self.mainwindow.signal_autoconnect(events)
        self.filechooser.signal_autoconnect(events)
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
        print "exiting"

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
            treeview1 = self.mainwindow.get_widget(PUZZLE_LIST)
            self.putListInTreeview(treeview1, self.nesrom.puzzles.keys(), 'Puzzles')

    # Open Dump File callback TODO - continue
    def openDumpFile(self, source=None, event=None):
        self.filechooser.filetype = DUMP_OPEN
        self.outputmsg('choose a dump file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

    # Save Dump File callback TODO - continue
    def saveDumpFile(self, source=None, event=None):
        self.filechooser.filetype = DUMP_SAVE
        self.outputmsg('choose a dump file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

    # import ROM callback
    def importRom(self, source=None, event=None):
        self.filechooser.filetype = ROM_OPEN
        self.outputmsg('choose a rom file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

    # export ROM callback
    def exportRom(self, source=None, event=None):
        self.filechooser.filetype = ROM_SAVE
        self.outputmsg('choose a rom file')
        self.filechooser.get_widget(FILE_CHOOSER).show()

# TODO : deprecated
    # Open File dialog callback
#    def openFileDialog(self, source=None, event=None, flag=None):
#        self.filechooser.filetype = flag
#        self.filechooser.get_widget(FILE_CHOOSER).show()

    # Close File dialog callback
    def closeFileDialog(self, source=None, event=None):
        self.filechooser.get_widget(FILE_CHOOSER).hide()

    # callback when the treeview is edited
    def treeview_edited(self, cellrenderedtext, path, newtext, liststore, column):
        oldtext = liststore[path][column]
        self.outputmsg ( '{0} -> {1}'.format(oldtext, newtext))
        if oldtext != newtext and newtext != '':
            self.nesrom.puzzles[newtext] = self.nesrom.puzzles[oldtext]
            del self.nesrom.puzzles[oldtext]
            liststore[path][column] = newtext
            self.displayCurrentPuzzle(self.mainwindow.get_widget(PUZZLE_LIST))

    # Open File callback -> when filechooser clicked 'ok'
    def openfile(self, source=None, event=None):
        self.closeFileDialog()
        filetype = self.filechooser.filetype
        filename = self.filechooser.get_widget(FILE_CHOOSER).get_filename()

        # save dump file
        if filetype == DUMP_SAVE:
            with open(filename, 'r') as f:
                pickle.dump(f, self.nesrom)

        # export rom
        elif filetype == ROM_SAVE:
            with open(filename, 'w') as f:
                for line in self.nesrom.sprList:
                    f.write(line)

        # open dump file
        elif filetype == DUMP_OPEN:
            # TODO -> move to initFromDumpFile
            with open(filename, 'r') as f:
                self.nesrom = pickle.load(f)
            self.outputmsg(os.path.basename(filename) +
                            ' loaded: ' +
                            str(len(self.nesrom.puzzles)) +
                            'puzzles found')

        # open rom
        elif filetype == ROM_OPEN:
            # construct new rom
            self.nesrom = Nesrom()
            self.nesrom.import_rom(filename)
            self.outputmsg(os.path.basename(filename) +
                            ' loaded: ' +
                            str(len(self.nesrom.sprList)) +
                            'sprites found')

        # puts puzzle list in treeview
        treeview1 = self.mainwindow.get_widget(PUZZLE_LIST)
        self.putListInTreeview(treeview1, self.nesrom.puzzles.keys(), 'Puzzles')
        # clear puzzlelayout
        puzzlelayout = self.mainwindow.get_widget(PUZZLE_AREA)
        for child in puzzlelayout.get_children():
            puzzlelayout.remove(child)
        # TODO -> move to printSpritsFromDumpFile
        spritlayout = self.mainwindow.get_widget(SPRITE_AREA)
        scale=6
        perline = 8
        offset = 2049
        spritlayout.set_size(perline*scale*8,
            (len(self.nesrom.sprList)-offset)*8*scale/perline)
        for sprnum in range(offset,len(self.nesrom.sprList)):
            eventbox = gtk.EventBox()
            pixbuf = self.putSprInWidget(eventbox, sprnum, scale)
            self.setSourceWidget(eventbox, sprnum, pixbuf, to_image)
            index = sprnum - offset
            spritlayout.put(eventbox,
                            8*scale*(index - perline*(index/perline)),
                            scale*8*(index/perline))
        spritlayout.show_all()

    # Callback to display current puzzle
    def displayCurrentPuzzle(self, treeview):
        puzzlename = self.getTreeviewSelected(treeview)
        currentpuzzle = self.nesrom.puzzles[puzzlename]
        self.outputmsg('displaying ' + puzzlename)
        puzzlearea = self.mainwindow.get_widget(PUZZLE_AREA)
        for child in puzzlearea.get_children():
            puzzlearea.remove(child)
            #child.destroy()
        scale=6
        width = scale*8*len(currentpuzzle[0])
        height = scale*8*len(currentpuzzle)
        puzzlearea.set_size(width, height)
        for i,line in enumerate(currentpuzzle):
            for j, sprnum in enumerate(line):
                if 0<sprnum<len(self.nesrom.sprList):
                    self.displaySprite(puzzlearea, sprnum, scale, scale*8*j, scale*8*i,
                                        True, i, j, puzzlename, from_image)
                else:
                    self.displaySprite(puzzlearea, sprnum, scale, scale*8*j, scale*8*i,
                                        False, i, j, puzzlename, from_image)
        puzzlearea.show_all()

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
        eventbox.connect('drag_data_get', self.sendImage)
        eventbox.drag_source_unset()
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

    # get selected value in a Treeview Widget
    def getTreeviewSelected(self, treeview):
        treeselection = treeview.get_selection()
        #treeselection.set_mode(gtk.SELECTION_SINGLE)
        (model, iter) = treeselection.get_selected()
        if iter == None: return None
        else: return model.get_value(iter, 0)


    # general method for outputing a message in the statusbar
    def outputmsg(self, message):
        statusbar = self.mainwindow.get_widget(STATUS_BAR)
        cid = statusbar.get_context_id('Messages')
        statusbar.push(cid, message)

    # Print a sprite in a Widget (usually an EventBox)
    def putSprInWidget(self, eventbox, sprnum, scale=1):
        gtkimage = gtk.Image()
        pixbuf = image_to_pixbuf(self.puzzle_to_image([[sprnum]], scale))
        gtkimage.set_from_pixbuf(pixbuf)
        eventbox.add(gtkimage)
        return pixbuf

    # Turns a puzzle into an Image
    def puzzle_to_image(self,puzzle, scale=1):
        width, height = len(puzzle[0]), len(puzzle)
        # save to temp file
        im = Image.new('RGB',(scale*8*width,scale*8*height))
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
    def displaySprite(self, puzzlearea, sprnum, scale, x, y, 
                         # infos for late instanciation
                        source, posx, posy, puzzlename, flags):
        eventbox = gtk.EventBox()
        # get pixbuf for icon of sourcewidget
        pixbuf = self.putSprInWidget(eventbox, sprnum, scale)
        self.setDestWidget(eventbox, puzzlename, posx, posy)
        if source:
            self.setSourceWidget(eventbox, sprnum, pixbuf, flags)
        puzzlearea.put(eventbox, x, y)
 
###################################
# launch editor from command line #
###################################
      
if __name__ == '__main__':
    app = GTKeditor()
    gtk.main()