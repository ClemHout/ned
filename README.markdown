# NED - A NES ROM sprite editor #

## Usage ##

Just type `python ned.py` to load the GUI.
To load a new ROM file, use the _File  / Import ROM_ menu.

## The main window ##

The main window is divided in three parts, __from right to left__:

* the ROM panel where the graphics found in the ROM file are displayed,
* the Puzzle panel where you can drag graphics from the ROM panel and use them in tiling puzzles.
* the Puzzle list when the puzzles that you have created are listed.

![ned screenshot](https://github.com/ClemHout/ned/raw/master/screenshot.png "ned screenshot")

## What you can do with it ##

To create (and delete) new puzzles, use the buttons below the Puzzle list.
The buttons below the Puzzle panel allow you to expand the puzzle with new rows
and new columns and to edit the current puzzle.
To put graphics in the puzzles, just drag them from the ROM panel to the Puzzle panel.
To delete graphics in a puzzle, just drag them back to the ROM panel.
Finally the buttons below the ROM panel allow you to display different sets of graphics in the ROM file.

## Saving your work ##

Once you have created nice puzzles and edited the graphics in the ROM, you can save your work
using the menu _File / Save Dump File_. Then you will be able to reload such a
file using the menu _File / Open Dump File_.


