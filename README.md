# L5K-Viewer
This is a tool to show a graphical representation of a L5K file. It currently supports ladder and FBD (although FBD is kinda ugly). It opens two windows: one for the programs, and one for tag xref.

The main window shows the controller, modules, programs, routines, etc in a tree on the left side. If you click a tag scope in the tree in the main window, it will list the tags in the viewer area on the right side of the window. The program has VERY LIMITED tag parsing capabilities. If it recognizes a tag name, and you click it anywhere in the viewer area of the main window, it will pull up that tag in the secondary (tag xref) window, and show routine names and line numbers for instances of that tag.

The secondary window focuses on tag scopes in the tree viewer. If you drill down to a tag scope, all the tags will appear in the tree. Selecting a tag in the tree will show xref data on the right-side of the window.

This program is intended for people who are able to fix the bugs themselves. This isn't a professional piece of software. Obviously, by using this you agree that the developer(s) is(are) not liable for anything at all, ever. 

I made this program because my company only has one license for Rockwell software, and it is bound to a laptop that the maintenance team uses. I occasionally need information about the programs on our PLCs, and I use this tool as a quick/dirty reference to see how the code is written. Almost all our code is ladder, and our IO maps are tidy, so this kind of viewer works well enough for me.

To use the program, run the L5K Viewer.py, and probably it'll go ahead and open up the windows its supposed to open. There's a button in the main window for you to select and open an L5K file. 

This was written using whatever version of python was latest when I installed python a couple of months ago (October 2023). It makes use of TKinter.
