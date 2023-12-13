import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import L5K_Parse
from L5K_Parse import Instruction
from tkinter.font import Font
from tkinter import Misc

#the L5K data model has this format:
# controller_info['controller name'] = {
#                   'ATTRIBUTES': ["attribute"],
#                   'DATATYPES': {'datatype name' : [("member type", "member name")]},
#                   'MODULES': {'module name' :{'module attribute' : "value"}}
#                   'AOI':
#                   {
#                       'aoi name' :
#                       {
#                           'PARAMETERS': {'parameter': [type, description]} #the first parameter is 'description': ["aoi description", '']
#                           'TAGS': {'tag name' : {'type': tag_datatype, 'value': tag_value}, 'description': tag_description}
#                           'ROUTINES': {'routine name' : ["individual line"]}
#                       }
#                   }   
#                   'TAGS': {'tag name' : {'type': tag_datatype, 'value': tag_value}}
#                   'TASKS':
#                   {
#                       'task name' :
#                       {
#                           'program name' :
#                           {
#                              'TAGS' : {'tag name' : {'type': tag_datatype, 'value': tag_value}, 'description': tag_description},
#                              'ROUTINES' : {'routine name' : ["individual line"]}
#                           }
#                       }
#                   }
#   }
#So to get to a line of code, you'll do:
# controller_info['controller name']['TASKS']['task name']['program name']['ROUTINES']['routine name'][index]
#to see a controller scoped tag, you'll use:
# controller_info['controller name']['TAGS']['tag name']

#Lines in ladder are stored in nested lists, using the Instruction(name, [args]) datatype.
# Branching sets are in an "outer list", with each branch stored as an "inner list".
# So, the L5K rung, "e[eee[e[ee,e]e,eee][ee,eee,e]e,e[e,ee]eeee[e,e,e]ee]" (where each "e" is an instruction)
# will produce the following nested list structure:
# [e,[[e,e,e,[[e,[[e,e],[e]],e],[e,e,e]],[[e,e],[e,e,e],[e]],e],[e,[[e],[e,e]],e,e,e,e,[[e],[e],[e]],e,e]]]

class Branch:
    def __init__(self, l, h, y, x):
        self.l = l
        self.h = h
        self.y = y
        self.x = x

pngAssets = ['ONS','OTE','OTL','OTU','XIC','XIO'] #we ended up not using the 'wire', ',', '[', and ']'
#pngWidth = 77
#pngHeight = 39
textlinegap = 2
textelbowroom = 10 #that's "elbow room" for left and right spacing
fbdCircleDiam = 10
data_model = {}

class MainWindow:
    def __init__(self, master, window1to2callback):
        self.master = master
        global data_model
        self.window1to2callback = window1to2callback

        self.master.geometry("800x400")

        self.paned_window = ttk.PanedWindow(self.master, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True)

        self.navigation_tree = NavigationTree(self.master, self.paned_window, self.tree_to_canvas_callback, self.window1to2callback)
        self.canvas_view = CanvasView(self.master, self.paned_window, self.canvas_to_tree_callback, self.window1to2callback)
        #self.button_grid = ButtonGrid(self.master, data_model, self.paned_window)

    def tree_to_canvas_callback(self, item, data):
        # handle canvas-related actions caused by tree interactions here
        # You can call the CanvasView methods to update the canvas
        # For example, self.canvas_view.display_attributes(attributes)
        self.canvas_view.display_attributes(item, data)
        self.canvas_view.reset_scrollregion(item)
        

    def canvas_to_tree_callback(self, data):
        # handle tree-related actions caused by canvas interactions here
        1;

class SecondWindow:
    def __init__(self, master, window2to1callback):
        self.master = master
        global  data_model
        self.window2to1callback = window2to1callback

        self.master.geometry("600x400")

        self.paned_window = ttk.PanedWindow(self.master, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True)

        self.second_tree = SecondTree(self.master, self.paned_window, self.tree_to_LabelList_callback)
        self.label_list = LabelList(self.master, self.paned_window, self.LabelList_to_tree_callback, self.window2to1callback)
    def xrefTag(self, data):
        tag_name = data["tag"]
        scope_name = data["scope"]
        global data_model
        
        def get_local_occurrences(tag_name, scope_name, scope_routines):
            occurrences = []
            for routine_name, routine_lines in scope_routines.items():
                rung = 0
                for idx, line in enumerate(routine_lines):
                    if line[0] == "fbd":
                        #fbds have sheets with lists of elements in line[1]. The arguments for the elements include coordinates, etc.
                        sheet = 1

                        while sheet < len(line):
                            for instr in line[sheet]:
                                if (tag_name in instr.name) or any(tag_name in item for item in instr.args.values()):
                                    occurrences.append({'Scope': scope_name, 'Routine': routine_name, 'RungSheet': sheet+rung, 'Index': idx, 'Instruction': instr})
                            sheet += 1
                            rung += 1
                    elif line[0] == "ST":
                        for part in line:
                            if tag_name in part:
                                occurrences.append({'Scope': scope_name, 'Routine': routine_name, 'RungSheet': sheet+rung, 'Index': idx, 'Instruction': part})
                                rung += 1
                    elif line[0] == "RC:":
                        #comments just have the text for the comment in line[1]
                        if tag_name in line[1]:
                            occurrences.append({'Scope': scope_name, 'Routine': routine_name, 'RungSheet': rung, 'Index': idx, 'Instruction': Instruction(name = "Comment", args = [line[1]])})
                    elif line[0] == "N:":
                        #Ladder rungs consist of nested lists in line[1]
                        def xref_my_ladder(routine_name, rung, idx, tag_name, line, depth=0):
                            found_instances = []
                            for item in line:
                                if isinstance(item, Instruction):
                                    #if item is an instruction, check its elements for tag_name and add dictionary to found_instances.
                                    if tag_name in item.args:
                                        found_instances.append({'Scope': scope_name, 'Routine': routine_name, 'RungSheet': rung, 'Index': idx, 'Instruction': item})
                                elif isinstance(item, list):
                                    #if item is a list, recursively call xref_my_ladder and add results to found_instances.
                                    for found_thing in xref_my_ladder(routine_name, rung, idx, tag_name, item, depth+1):
                                        found_instances.append(found_thing)
                            return found_instances
                        for found_thing in xref_my_ladder(routine_name, rung, idx, tag_name, line[1]):
                            occurrences.append(found_thing)
                            
                        rung += 1
 
            return occurrences

        def get_controller_occurrences(tag_name, controller_name, controller_data):
            occurrences = []
            for aoi_name, aoi_data in controller_data['AOI'].items():
                for instance in get_local_occurrences(tag_name, aoi_name, aoi_data['ROUTINES']):
                    occurrences.append(instance)
            for task_name, programs in controller_data['TASKS'].items():
                for program_name, program_data in programs.items():
                    for instance in get_local_occurrences(tag_name, program_name, program_data['ROUTINES']):
                        occurrences.append(instance)
            return occurrences
            
        tag_occurrences = []
        itemID = ''
        for controller_name, controller_data in data_model.items():
            if scope_name == controller_name:
                itemID = "/"+controller_name+"/TAGS/"+tag_name
                tag_occurrences = get_controller_occurrences(tag_name, scope_name, controller_data)
                break
            elif 'AOI' in controller_data and scope_name in controller_data['AOI']:
                itemID = "/"+controller_name+"/AOI/"+scope_name+"/TAGS/"+tag_name
                for test_tag, tag_data in controller_data['AOI'][scope_name]['TAGS'].items():
                    if tag_name == test_tag:
                        #print("it's an AOI tag")
                        tag_occurrences = get_local_occurrences(tag_name, scope_name, controller_data['AOI'][scope_name]['ROUTINES'])
                        break
                if tag_occurrences == []:
                    #print("triggered by AOI instance, but not an AOI tag")
                    splitItem = itemID.split('/')
                    itemID = '/'+splitItem[1]+'/TAGS/'+splitItem[-1]
                    tag_occurrences = get_controller_occurrences(tag_name, controller_name, controller_data)
                break
            elif 'TASKS' in controller_data:
                for task_name, programs in controller_data['TASKS'].items():
                    if scope_name in programs:
                        itemID = "/"+controller_name+"/TASKS/"+task_name+"/"+scope_name+"/TAGS/"+tag_name
                        for test_tag, tag_data in controller_data['TASKS'][task_name][scope_name]['TAGS'].items():
                            if tag_name == test_tag:
                                #print("it's a program tag")
                                tag_occurrences = get_local_occurrences(tag_name, scope_name, controller_data['TASKS'][task_name][scope_name]['ROUTINES'])
                                break;
                        if tag_occurrences == []:
                            #print("triggered by program instance, but not a program tag")
                            splitItem = itemID.split('/')
                            itemID = '/'+splitItem[1]+'/TAGS/'+splitItem[-1]
                            tag_occurrences = get_controller_occurrences(tag_name, controller_name, controller_data)
                        break
        if tag_occurrences == []:
            print("No instances found or invalid xref data for tag")
            return None  # Invalid scope name
        else:
            #instances are {'Scope': scope_name, 'Routine': routine_name, 'RungSheet': rung, 'Index': idx, 'Instruction': item}
            #the difference between rung and idx is a mystery to me right now.
            try:
                self.second_tree.tree.selection_set(itemID)
            except:
                1;#nop
                #print(f"Failed to navigate to item in tree: {itemID}")
            self.label_list.display_attributes(itemID, tag_occurrences)
            
        
        
    def tree_to_LabelList_callback(self, item, data):
        # handle canvas-related actions caused by tree interactions here
        # You can call the CanvasView methods to update the canvas
        # For example, self.canvas_view.display_attributes(attributes)

        #in this context, item is the path to a tag, including the tagname, and data is a dict like {'type': 'BOOL', 'value': '0'}
        self.xrefTag({"tag": item.split('/')[-1], "scope": item.split('/')[-3]})
        #xrefTag calls display_attributes for us.
        #self.label_list.display_attributes(item, data)
        

    def LabelList_to_tree_callback(self, data):
        # handle tree-related actions caused by canvas interactions here
        1;

class NavigationTree:
    def __init__(self, master, paned_window, tree_to_canvas_callback, window1to2callback, weight=1):
        self.master = master
        global data_model
        self.paned_window = paned_window
        self.tree_item_data = {}
        self.treeFont = Font()
        self.tree_to_canvas_callback = tree_to_canvas_callback
        self.window1to2callback = window1to2callback
        
        # Create a frame for the button and tree
        self.tree_frame = ttk.Frame(self.paned_window)
        self.tree_frame.grid(row=0, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(1, weight=1) #tree stretches to bottom of window

        # Create a button for opening the file dialog
        self.open_button = tk.Button(self.tree_frame, text="Open File", command=self.open_file_dialog)
        self.open_button.grid(row=0, column=0, sticky="nsew") #button to open new files

        # Create a tree view
        self.tree = ttk.Treeview(self.tree_frame, show='tree')
        self.tree.grid(row=1, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.paned_window.add(self.tree_frame)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_item_click)

        self.paned_window.bind("<B1-Motion>", self.on_sash_drag)

    def on_sash_drag(self,event):
        # Get the new sash position
        new_sash_position = event.x
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.configure(width=new_sash_position)
        self.tree.column("#0", width=new_sash_position)
        
    def populate_tree(self, data, parent_id):
        for key, value in data.items():
            item_id = self.tree.insert(parent_id, 'end', text=key, iid=parent_id+"/"+key)
            self.tree_item_data[item_id] = value  # Store the associated data
            if (parent_id.split('/')[-1] == "MODULES" or key == "TAGS" or key == "PARAMETERS" or parent_id.split('/')[-1] == "DATATYPES"):
                1;
            elif isinstance(value, dict) and value:
                self.populate_tree(value, item_id)

    def on_tree_item_click(self, event):
        try:
            item_id = self.tree.selection()[0]
            children = self.tree.get_children(item_id)
                
            self.tree.column("#0", stretch=False)
            self.tree.update_idletasks()
            
            text_width = self.treeFont.measure(self.tree.item(item_id, 'text').strip())
            tab_width = self.tree.bbox(item_id, column="#0")[0]  # Get the width of the last column
            content_width = text_width+tab_width

            if content_width > self.tree.winfo_width():
                self.tree.column("#0", width=content_width)  # Adjust the column width
            else:
                self.tree.column("#0", width=self.tree.winfo_width())  # Set the width to the visible width

            item_data = self.tree_item_data.get(item_id)
            # Use the callback in the NavigationTree class to handle the canvas update
            self.tree_to_canvas_callback(item_id, item_data)
        except IndexError:
            #clicking white space on the list throws this error. Just don't update the item.
            pass 

    
    def open_file_dialog(self):
        global data_model
        file_path = filedialog.askopenfilename()
        if file_path and file_path[-4:] == '.L5K':
            print(f"Selected file: {file_path}")
            with open(file_path, 'r') as file:
                content = file.readlines()
            data_model = L5K_Parse.parse_file_content(content)
            self.populate_tree(data_model, '')
            self.window1to2callback(self, "tree", None)
        else:
            print("Invalid file! It's gotta be an L5K file.")
            

class CanvasView:
    def __init__(self, master, paned_window, canvas_to_tree_callback, window1to2callback):
        self.canvas_to_tree_callback = canvas_to_tree_callback
        self.master = master
        global data_model
        self.paned_window = paned_window
        self.canvasFont = Font(size = 10)
        self.commentFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.window1to2callback = window1to2callback

        #preload image assets for ladder viewer
        self.image_assets = {}
        global pngAssets
        for instruction_name in pngAssets:
            image_filename = f"Assets/{instruction_name}.png"
            photo_image = tk.PhotoImage(file = image_filename)
            self.image_assets[instruction_name] = photo_image

        self.canvas_frame = ttk.Frame(self.paned_window)
        #self.canvas_frame.bind("<Configure>", self.reset_scrollregion)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Add scrollbars to the canvas frame
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.paned_window.add(self.canvas_frame)

        # Draw on the canvas (e.g., lines, rectangles, text, images)
        self.canvas.create_text(90, 125, text="L5K Viewer!", fill="green", font = self.canvasFont)
        self.photo = tk.PhotoImage(file="Assets/xic.png")
        self.image = self.canvas.create_image(50, 150, anchor=tk.NW, image=self.photo)
        
        # Configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
    def on_text_click(self, event, item_id, scopename):
        # Get the text associated with the clicked object
        clicked_text = self.canvas.itemcget(item_id, 'text')
        #------Send tag data to the second window for cross referencing
        window1to2callback(self, "tagXref", {"tag": clicked_text, "scope": scopename})
        
    def reset_scrollregion(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("ALL"))
    
    def display_attributes(self, item, data):
        self.canvas.delete("all")
        y_offset = 40  # Initial Y offset
        rung_number = 0
        Label_offset = -25
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        global textlinegap, fbdCircleDiam

        item_hierarchy = item.split('/')

        if item_hierarchy[-1] == "ATTRIBUTES":
            for attribute, value in data:
                label_text = f"{attribute.strip()}: {value.strip()}"
                self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
                y_offset += 20  # Increase Y offset for the next item
        elif item_hierarchy[-2] == "DATATYPES" or item_hierarchy[-2] == "MODULES":
            for attribute, value in data.items():
                label_text = f"{attribute.strip()}: {value.strip()}"
                self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
                y_offset += 20  # Increase Y offset for the next item
        elif  item_hierarchy[-1] == "TAGS":
            for tag, tdata in data.items():
                label_text = str(tag.strip())
                text_object = self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
                self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object: self.on_text_click(event, item_id, item_hierarchy[-2]))
                label_text = f"\tTYPE: {tdata['type'].strip()}\t\tVALUE: {tdata['value'].strip()}\t\tDESCRIPTION: {tdata['description'].strip()}"
                self.canvas.create_text(10, y_offset+textlineheight+textlinegap, text=label_text, anchor=tk.W, font = self.canvasFont)
                y_offset += 2*textlineheight+3*textlinegap # Increase Y offset for the next item
        elif item_hierarchy[-1] == "PARAMETERS":
            for tag, tdata in data.items():
                label_text = f"{tag.strip()}\n\tTYPE: {tdata[0].strip()}\t\tCOMMENT: {tdata[1].strip()}"
                self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
                y_offset += 40  # Increase Y offset for the next item
        elif item_hierarchy[-2] == "ROUTINES":
            for rung in data:
                #Routines are ["type",[rung/sheet],[rung/sheet],...]
                #Function Block Diagrams
                
                if rung[0] == "fbd":
                    #One rung in FBD has one sheet.
                    #FBD sheets are [instruction, instruction, ...], where the name is the type of block, and the args are location, etc...
                    self.canvas.create_text(5,5+y_offset, text="Sheet " + str(rung_number), anchor=tk.W, font = self.canvasFont)
                    
                    boldlineheight = Font.metrics(self.boldFont)["linespace"]
                    
                    rungIDs = {}
                    k = 1
                    lowest_y = 0
                    #----------------TO DO: Review the whole "lowest_y" usage here to verify whether single "rung" in "data" has multiple "sheets", so that we can know whether this is done appropriately
                    i = 0
                    while i < len(rung[1]):
                        elem = rung[1][i]
                        #every instruction or I/OREF object has an "ID"
                        if "ID" in elem.args:
                            myName = "[" + str(elem.name) + "]"
                            myX = int(elem.args['X'])
                            myY = int(elem.args['Y'])
                            rungIDs[elem.args["ID"]] = [myX, myY, 0] #the third item is for an offset for multiple connections
                            if "Operand" in elem.args:
                                myOperand = elem.args["Operand"].replace('"','')
                            else:
                                myOperand = ""
                            text_to_show = []
                            for blub, stuff in elem.args.items():
                                #get any additional tags associated with the instruction
                                if blub not in ["N/A", "Type", "ID", "Operand",
                                               "ArrayName", "Name", "X", "Y",
                                               "AutotuneTag", "HideDesc", "VisiblePins",
                                               "Description", "FBDContent",
                                                "EncryptionInfo", "EncryptedContent",
                                               "EncryptedSegments", "HideDescription"]:
                                    text_to_show.append(str(blub) + " " + str(stuff))
                            textblockheight = textlineheight * (len(text_to_show) + 1) #plus 1 for the operand
                            textblockheight += boldlineheight #for the block name
                            textblockheight += textlinegap * len(text_to_show)
                            self.canvas.create_circle(myX, myY+y_offset, 10, fill = "tan", outline = "black", width = 3)
                            text_object = self.canvas.create_text(myX, myY + fbdCircleDiam + textlinegap+y_offset, text = myName, anchor = tk.NW, font=self.boldFont)
                            text_object = self.canvas.create_text(myX, myY + fbdCircleDiam + textlinegap*2 + boldlineheight+y_offset, text = myOperand, anchor = tk.NW, font=self.canvasFont)
                            self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object: self.on_text_click(event, item_id, item_hierarchy[-3]))
                            if myY + fbdCircleDiam + textlinegap*2 + boldlineheight+y_offset > lowest_y:
                                lowest_y = myY + fbdCircleDiam + textlinegap*2 + boldlineheight
                            j = 0
                            starty = myY + fbdCircleDiam + textlinegap*3 + boldlineheight + textlineheight
                            while j < len(text_to_show):
                                #Show all the text_to_show here
                                text_object = self.canvas.create_text(myX, starty+(textlinegap+textlineheight)*j+y_offset, text=text_to_show[j].replace("$N","\n"), anchor=tk.NW, font=self.canvasFont)
                                if starty+(textlinegap+textlineheight)*j+y_offset > lowest_y:
                                    lowest_y = starty+(textlinegap+textlineheight)*j
                                if (text_to_show[j][0] not in "0123456789"): #trying to filter out things that aren't tag names
                                    self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object: self.on_text_click(event, item_id, item_hierarchy[-3]))
                                j+= 1
                            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                        elif "FromElementID" in elem.args:
                            #We assume that wires and attachments come after all the other objects so that IDs are established
                            fidx = rungIDs[elem.args["FromElementID"]][0] + fbdCircleDiam
                            fidy = rungIDs[elem.args["FromElementID"]][1] - ((textlineheight+textlinegap)*rungIDs[elem.args["FromElementID"]][2])+y_offset
                            tidx = rungIDs[elem.args["ToElementID"]][0] + fbdCircleDiam
                            tidy = rungIDs[elem.args["ToElementID"]][1] - ((textlineheight+textlinegap)*rungIDs[elem.args["ToElementID"]][2])+y_offset
                            #offset for future connections
                            rungIDs[elem.args["FromElementID"]][2] += 1
                            rungIDs[elem.args["ToElementID"]][2] += 1
                            self.canvas.create_line(fidx, fidy, tidx, tidy)
                            if "FromParameter" in elem.args:
                                self.canvas.create_text(fidx, fidy-textlineheight, text=elem.args["FromParameter"], anchor=tk.NW, font=self.commentFont)
                                self.canvas.create_text(tidx, tidy-textlineheight, text=elem.args["ToParameter"], anchor=tk.NW, font=self.commentFont)
                            else:
                                #attachments don't have parameter names, but we should still represent them to avoid confusion.
                                self.canvas.create_text(fidx, fidy-textlineheight, text="_", anchor=tk.NW, font=self.commentFont)
                                self.canvas.create_text(tidx, tidy-textlineheight, text="_", anchor=tk.NW, font=self.commentFont)
                            if fidy > lowest_y:
                                lowest_y = fidy
                            if tidy > lowest_y:
                                lowest_y = tidy
                            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                        i += 1
                    rung_number += 1
                    y_offset = textlineheight*2+textlinegap*2+lowest_y
                #Structured Text
                elif rung[0] == "ST":
                    textlineheight = Font.metrics(self.canvasFont)["linespace"]
                    text_object = self.canvas.create_text(textelbowroom, y_offset + rung_number*(textlineheight+textlinegap), text=rung[1], anchor=tk.NW, font = self.canvasFont)
                    rung_number += 1
                
                #Ladder Rung Comments
                elif rung[0] == "RC:":
                    #Rung comments are ["RC:", "comment contents"]. RC rungs are not enumerated for visual rung numbering.
                    self.canvas.create_text(10, y_offset, text=rung[1], anchor=tk.W, font = self.commentFont)
                    y_offset += 20
                #Ladder Logical Rungs
                elif rung[0] == "N:":
                    #Ladder rungs are stored in nested lists, using the Instruction(name, [args]) datatype.
                    # Branching sets are in an "outer list", with each parallel branch stored as an "inner list". This is because commas are between every item in a python list, in contrast to L5K rungs
                    # So, the L5K rung, "e[eee[e[ee,e]e,eee][ee,eee,e]e,e[e,ee]eeee[e,e,e]ee]" (where each "e" is an instruction)
                    # will produce the following nested list structure:
                    # [e,[[e,e,e,[[e,[[e,e],[e]],e],[e,e,e]],[[e,e],[e,e,e],[e]],e],[e,[[e],[e,e]],e,e,e,e,[[e],[e],[e]],e,e]]]
                    
                    y_offset += 10 #first offset gets away from comments

                    def get_png_details(element):
                        global textlinegap
                        photo_image = None
                        text_width = 0
                        text_height = 0
                        textlineheight = Font.metrics(self.canvasFont)["linespace"] #vertical pixel size for font
                        image_height = 0
                        image_width = 0
                        if element.name in pngAssets:
                            photo_image = self.image_assets[element.name]
                            image_width = photo_image.width()
                            image_height = photo_image.height()
                        else:
                            image_width = self.boldFont.measure("[" + element.name.strip() + "]")
                        width = image_width
                        height = image_height
                        if len(element.args) > 0:
                            for arg in element.args:
                                text_width = self.canvasFont.measure(arg.strip()) #horizontal pixel size for text
                                if text_width > width:
                                    width = text_width
                                if len(element.args) > 1: #this is not a simple XIC/OTE type element
                                    text_height += textlineheight + textlinegap
                                    if text_height + (textlinegap*2) + image_height > height:
                                        height = (textlinegap*2) + text_height
                        if width < 20:
                            width = 20
                        if height < 20:
                            height = 20
                        return width, height, textlineheight, image_width, photo_image

                    def getTagDescription(checkTag, itemHierarchy):
                        #returns the tag description for a given tag name or returns None
                        global data_model
                        if checkTag.replace('"','').strip()[0] in '0123456789':
                            #tag names cannot start with a number.
                            return None
                        #first check local tags (e.g. AOI or Program tags)
                        TAGS = None
                        #every section in data_model that has "ROUTINES" also has "TAGS" at the same level in the hierarchy
                        #(this is a prank I'm playing on some future troubleshooter who wants to update the data_model)
                        if itemHierarchy[2] == 'TASKS':
                            TAGS = data_model[itemHierarchy[1]]['TASKS'][itemHierarchy[3]][itemHierarchy[4]]['TAGS']
                        elif itemHierarchy[2] == 'AOI':
                            TAGS = data_model[itemHierarchy[1]]['AOI'][itemHierarchy[3]]['TAGS']
                        if TAGS is not None:
                            tag_description = next((value['description'] for key, value in TAGS.items() if checkTag in key), None)
                            if tag_description is not None and tag_description.strip() in ['','N/A','\n','\t']:
                                #Don't show garbage tag descriptions
                                return None
                            if tag_description is not None:
                                return tag_description.replace('$N',' ')
                        #now check controller tags
                        TAGS = data_model[itemHierarchy[1]]['TAGS']
                        tag_description = next((value['description'] for key, value in TAGS.items() if checkTag in key), None)
                        if tag_description is not None:
                            tag_description = tag_description.replace('$N',' ')
                            if tag_description.strip() in ['','N/A','\n','\t']:
                                #Don't show garbage tag descriptions
                                return None
                        return tag_description
                    
                    def draw_ladder(parsed_elements, x, y):
                        max_height = 0
                        branch_y = 0
                        branches = []
                        space_between_elements = 30
                        text_y_offset = -20
                        #"wiregap" brings the wire to the midpoint between elements (for vertical lines), and the midpoint of my png elements (for horizontal lines)
                        wiregap = space_between_elements/2 
                        global textlinegap
                        global textelbowroom
                        is_branch_group = False
                        
                        for element in parsed_elements:
                            if isinstance(element, Instruction):
                                element_width, element_height, textlineheight, image_width, photo_image = get_png_details(element)
                                x += space_between_elements
                                #-------------DRAW THE ELEMENT HERE--------------------
                                if photo_image != None:
                                    if len(element.args) > 1:
                                        print("routine:" + str(item) + "\nRung: \n" + str(rung) + "\nToo many args for: " + str(instruction))
                                    text_object = self.canvas.create_text(x, y+text_y_offset, text=element.args[0], anchor=tk.NW, font = self.canvasFont)
                                    self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object: self.on_text_click(event, item_id, item_hierarchy[-3]))
                                    self.canvas.create_image(x, y, image=photo_image, anchor=tk.NW)
                                    self.canvas.create_line(x+image_width,y+wiregap,x+element_width+space_between_elements,y+wiregap)
                                else:
                                    self.canvas.create_text(x, y+text_y_offset, text="["+element.name+"]", anchor=tk.NW, font = self.boldFont)
                                    self.canvas.create_rectangle(x, y, x+element_width+2*textelbowroom, y+element_height, fill='white')
                                    if element.args != ['']:
                                        i = 0
                                        while i < len(element.args):
                                            text_object = self.canvas.create_text(x+textelbowroom, y+textlinegap+((textlineheight+textlinegap)*i), text=element.args[i], anchor=tk.NW, font = self.canvasFont)
                                            if (element.args[i][0] not in "0123456789\""): #trying to filter out text things that aren't tag names
                                                self.canvas.tag_bind(text_object, '<Button-1>', lambda event, item_id=text_object: self.on_text_click(event, item_id, item_hierarchy[-3]))
                                            i += 1
                                    element_width += 2*textelbowroom
                                    
                                    self.canvas.create_line(x+element_width,y+wiregap,x+element_width+space_between_elements,y+wiregap)

                                #Print tag descriptions below instructions
                                
                                if element.args != ['']:
                                    description_lines = 1 #starts at 1 to offset the first line
                                    for tag_to_check in element.args:
                                        #put a line between descriptions of different tags:
                                        if description_lines > 1:
                                            self.canvas.create_text(x,y+element_height+textlinegap+(textlinegap+textlineheight)*description_lines,text="- - - -", anchor=tk.W, font=self.commentFont)
                                            #that line is a line in the description text block, so increment description_lines
                                            description_lines += 1
                                        tag_description = getTagDescription(tag_to_check, item_hierarchy)
                                        #print descriptions for tags
                                        if tag_description is not None:
                                            textToPrint = ''
                                            for c in tag_description.split(' '):
                                                cwidth = self.commentFont.measure(str(textToPrint)+ " " + c) + textelbowroom
                                                if cwidth < element_width:
                                                    textToPrint += " " + c
                                                else:
                                                    self.canvas.create_text(x,y+element_height+(textlinegap+textlineheight)*description_lines,text=textToPrint, anchor=tk.W, font=self.commentFont)
                                                    description_lines += 1
                                                    textToPrint = c
                                            self.canvas.create_text(x,y+element_height+textlinegap+(textlinegap+textlineheight)*description_lines,text=textToPrint, anchor=tk.W, font=self.commentFont)
                                            description_lines += 1
                                    element_height += textlinegap+(textlinegap+textlineheight)*description_lines
                                
                                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                                x += element_width
                                max_height = max(max_height, y+element_height)
                            elif isinstance(element, list):
                                #if the element is a list, then it's a branch or branch group
                                if len(branches) > 0:
                                    #if this is a branch on a branch, then the start y is going to be the y of the lowest branch already drawn
                                    branch_y = branches[-1].h + space_between_elements
                                else:
                                    #otherwise, the start y will be the y of this rung
                                    branch_y = y 
                                #------------DRAW start-of-branch WIRES HERE---------------------
                                #vertical line to branch
                                self.canvas.create_line(x+wiregap,y+wiregap,x+wiregap,branch_y+wiregap)
                                #horizontal line to first element place in branch.
                                self.canvas.create_line(x+wiregap,branch_y+wiregap,x+space_between_elements,branch_y+wiregap)
                                #recurse to draw the new branch. the return values enable me to treat it as a single instruction for the remainder of this pass.
                                bl, bh, bgReturn = draw_ladder(element, x, branch_y)
                                if bgReturn: #it was a branch group, not an individual branch
                                    #------------DRAW post-branch-group horizontal WIRES HERE---------------------
                                    #If the return value indicates this was a branch group, then draw a wire from the branch group to the next instruction.
                                    self.canvas.create_line(bl,y+wiregap,bl+space_between_elements,y+wiregap)
                                    x = bl#+space_between_elements
                                else: #it was a branch in a group
                                    #if the return value indicates this was a single branch, then just append it to the list.
                                    branches.append(Branch(l=bl, h=bh, y=branch_y, x=x))
                                max_height = max(max_height, bh)
                                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                        if len(branches) > 0:
                            #If more than one branch was found in this pass, then close the branches
                            longest = max(branches, key=lambda testbranch: testbranch.l).l + space_between_elements
                            #----------------DRAW end-of-branch vertical WIRES HERE-----------------------
                            self.canvas.create_line(longest, y+wiregap, longest, branches[-1].y+wiregap)
                            i = 0
                            while i < len(branches):
                                if branches[i].l < longest:
                                    #---------------------DRAW branch-filling horizontal WIRES HERE------------------
                                    self.canvas.create_line(branches[i].l, branches[i].y+wiregap, longest, branches[i].y+wiregap)
                                i += 1
                            x = longest
                            branches = []
                            is_branch_group = True
                        #else:
                        #THis next if-statement was previously inside the above "else". If there's a problem with shorts rendering correctly, consider putting it back.
                        if len(parsed_elements) == 0:
                            print("found a shorted (0 length) branch")
                            #Update the y offset for branches with no instructions.
                            max_height += space_between_elements*5 #hopefully enough to make it look good, without making too much space either
                        return x, max_height, is_branch_group

                    #draw the rung number
                    self.canvas.create_text(2, y_offset, text=str(rung_number), anchor=tk.W, font = self.canvasFont)
                    x_offset, y_offset, nothing2 = draw_ladder(rung[1], 10, y_offset)
                    y_offset += 20 #second offset gets away from prior rungs
                    rung_number +=1

                #is there anything else?
                else:
                    print("Unhandled Rung in " + str(item) + ": \n" + str(rung))

        # Configure the scroll region to make the canvas scrollable
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

#class ButtonGrid:
#    def __init__(self, master, data_model, paned_window):
#        self.master = master
#        self.data_model = data_model
#
#        self.button_frame = ttk.Frame(paned_window)
#        self.button_frame.grid(row=0, column=1, sticky="nsew")
#
#        self.button_grid = ttk.Frame(self.button_frame)
#        self.button_grid.grid(row=0, column=0, padx=10, pady=10)
#
#        for i in range(3):
#            for j in range(3):
#                self.add_button(f"Button {i*3 + j + 1}", i, j)
#               
#
#        self.paned_window = paned_window
#        self.paned_window.add(self.button_frame)
#
#    def add_button(self, text, i, j):
#        self.data_model.button_grid_data[text] = {}
#        button = ttk.Button(self.button_grid, text=text)
#        button.grid(row=i, column=j, padx=5, pady=5)

class SecondTree:
    def __init__(self, master, paned_window, tree_to_LabelList_callback):
        self.master = master
        global data_model
        self.paned_window = paned_window
        self.tree_item_data = {}
        self.treeFont = Font()
        self.tree_to_LabelList_callback = tree_to_LabelList_callback
        
        # Create a frame for the button and tree
        self.tree_frame = ttk.Frame(self.paned_window)
        self.tree_frame.grid(row=0, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1) #tree stretches to bottom of window

        # Create a tree view
        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.paned_window.add(self.tree_frame)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_item_click)

        self.paned_window.bind("<B1-Motion>", self.on_sash_drag)
        
    def on_sash_drag(self,event):
        # Get the new sash position
        new_sash_position = event.x
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.configure(width=new_sash_position)
        self.tree.column("#0", width=new_sash_position)

    def add_node(self, parent, text):
        self.tree.insert(parent, "end", iid=text, text=text)
        
    def populate_tree(self, data, parent_id):
        for key, value in data.items():
            if key not in ["ATTRIBUTES", "DATATYPES", "MODULES", "ROUTINES", "PARAMETERS"]:
                item_id = self.tree.insert(parent_id, 'end', text=key, iid=parent_id+"/"+key)
                self.tree_item_data[item_id] = value  # Store the associated data
                if parent_id.split('/')[-1] in ["TAGS"]:
                    1;
                elif isinstance(value, dict) and value:
                    self.populate_tree(value, item_id)
                


    def on_tree_item_click(self, event):
        try:
            item_id = self.tree.selection()[0]
            children = self.tree.get_children(item_id)
                
            self.tree.column("#0", stretch=False)
            self.tree.update_idletasks()
            
            text_width = self.treeFont.measure(self.tree.item(item_id, 'text').strip())
            tab_width = self.tree.bbox(item_id, column="#0")[0]  # Get the width of the last column
            content_width = text_width+tab_width

            if content_width > self.tree.winfo_width():
                self.tree.column("#0", width=content_width)  # Adjust the column width
            else:
                self.tree.column("#0", width=self.tree.winfo_width())  # Set the width to the visible width

            if item_id.split('/')[-2] == "TAGS":
                #print("cross referencing: ", item_id)
                item_data = self.tree_item_data.get(item_id)
                # Use the callback in the NavigationTree class to handle the canvas update
                self.tree_to_LabelList_callback(item_id, item_data) #item_id.split('/')[-3] is the scope.
        except IndexError:
            #clicking white space on the list throws this error. Just don't update the item.
            pass 

class LabelList: #The name for this function, "LabelList", is an artifact from a prior revision of the code. My IDE doesn't have good refactoring or I'd change it.
    def __init__(self, master, paned_window, LabelList_to_tree_callback, window2to1callback):
        self.master = master
        global data_model
        self.LabelList_to_tree_callback = LabelList_to_tree_callback
        self.paned_window = paned_window
        self.canvasFont = Font(size = 10)
        self.commentFont = Font(size = 10, slant = 'italic')
        self.boldFont = Font(size = 10, weight = 'bold')
        self.window2to1callback = window2to1callback

        self.canvas_frame = ttk.Frame(self.paned_window)
        self.canvas_frame.bind("<Configure>", self.reset_scrollregion)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Create a canvas inside a canvas frame
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Create vertical and horizontal scrollbars
        v_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Add scrollbars to the canvas frame
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.paned_window.add(self.canvas_frame)

        # Draw on the canvas (e.g., lines, rectangles, text, images)
        self.canvas.create_text(90, 125, text="L5K Viewer!", fill="green", font = self.canvasFont)
        self.photo = tk.PhotoImage(file="Assets/xic.png")
        self.image = self.canvas.create_image(50, 150, anchor=tk.NW, image=self.photo)
        
        # Configure the scroll region to make the canvas scrollable
        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
    def on_text_click(self, event, item_id, scopename):
        # Get the text associated with the clicked object
        clicked_text = self.canvas.itemcget(item_id, 'text')
        #------Send tag data to the second window for cross referencing
        window2to1callback(self, "tagXref", address)
        #print(f"Text clicked: {clicked_text}")
        #print(f"Scope: {scopename}")
        
    def reset_scrollregion(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    
    def add_label(self, text):
        #self.data_model.button_grid_data[text] = {}
        label = ttk.Label(self.label_list, text=text, width=20)
        label.grid(row=self.label_list.grid_size()[1], column=0, padx=5, pady=5)

    def display_attributes(self, item, data):
        #Here display all the cross reference data.
        #under normal circumstances, "item" will be the tree ID for the tag, and data will be a list of tag instances.
        #tag instances ("data") are dicts like {'Scope': scope_name, 'Routine': routine_name, 'RungSheet': rung, 'Index': idx, 'Instruction': item}
        #the Instruction item will be of type Instruction. For comments, it will be Instruction(name = "Comment", args=["comment text"]
        #the difference between rung and idx is a mystery to me right now. I intend to use some trial and error to determine which is most appropriate for different kinds of instances.

        self.canvas.delete("all")
        y_offset = 40  # Initial Y offset
        textlineheight = Font.metrics(self.canvasFont)["linespace"]
        boldlineheight = Font.metrics(self.boldFont)["linespace"]
        global textlinegap, fbdCircleDiam
        
        self.canvas.create_text(10, y_offset, text=item.replace('/', ' / '), anchor=tk.W, font = self.boldFont)
        y_offset += boldlineheight+2*textlinegap # Increase Y offset for the next item

        for instance in data:
            label_text = f"{instance['Instruction'].name}({instance['Instruction'].args})\t\t{instance['Scope']}/{instance['Routine']}, Rung/Sheet {instance['RungSheet']}"
            self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
            #y_offset += textlineheight+textlinegap # Increase Y offset for the next item
            #label_text = f"\t{instance['Scope']}/{instance['Routine']}, Rung/Sheet {instance['RungSheet']}, Index {instance['Index']}."
            #self.canvas.create_text(10, y_offset, text=label_text, anchor=tk.W, font = self.canvasFont)
            y_offset += textlineheight+2*textlinegap # Increase Y offset for the next item
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

if __name__ == "__main__":
    
    root = tk.Tk()
    root.title("L5K Viewer -- Program Viewer")
    def _create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
    tk.Canvas.create_circle = _create_circle

    second_window = tk.Toplevel(root)
    second_window.title("L5K Viewer -- Tag Cross Reference Tool")
    second_window.geometry("800x400")
    second_window.protocol("WM_DELETE_WINDOW", second_window.destroy)


    def window2to1callback(self, data):
        1;
    
    w2 = SecondWindow(second_window, window2to1callback)

    
    def window1to2callback(self, calltype, data):
        if calltype == "tree":
            w2.second_tree.populate_tree(data_model, '')
        elif calltype == "tagXref":
            w2.xrefTag(data)
        
        1;
    
    
    main_window = MainWindow(root, window1to2callback)
    #main_window = MainWindow(root, data_model)

    

    root.mainloop()


