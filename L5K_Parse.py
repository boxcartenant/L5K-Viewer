import re, string


class DataModel:
    def __init__(self):
        self.tree_data = {}
        #self.button_grid_data = {}
        self.canvas_data = {}
        self.second_tree_data = {}

#file is parsed into the following format:
# controller_info['controller name'] = {
#                   'ATTRIBUTES': ["attribute"],
#                   'DATATYPES': {'datatype name' : [("member type", "member name")]},
#                   'MODULES': {'module name' :{'module attribute' : "value"}}
#                   'AOI':
#                   {
#                       'aoi name' :
#                       {
#                           'PARAMETERS': {'parameter': [type, description]}
#                           'TAGS': {'tag name' : {'type': tag_datatype, 'value': tag_value}}
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
#                              'TAGS' : {'tag name' : {'type': tag_datatype, 'value': tag_value}},
#                              'ROUTINES' : {'routine name' : ["individual line"]}
#                           }
#                       }
#                   }
#
#So to get to a line of code, you'll do:
# controller_info['controller name']['TASKS']['task name']['program name']['ROUTINES']['routine name'][index]
#to see a controller scoped tag, you'll use:
# controller_info['controller name']['TAGS']['tag name']

#Lines in ladder are stored in nested lists, using the Instruction(name, [args]) datatype.
# Branching sets are in an "outer list", with each branch stored as an "inner list".
# So, the L5K rung, "e[eee[e[ee,e]e,eee][ee,eee,e]e,e[e,ee]eeee[e,e,e]ee]" (where each "e" is an instruction)
# will produce the following nested list structure:
# [e,[[e,e,e,[[e,[[e,e],[e]],e],[e,e,e]],[[e,e],[e,e,e],[e]],e],[e,[[e],[e,e]],e,e,e,e,[[e],[e],[e]],e,e]]]


class Instruction:
    #for ladder, the args will be a list.
    #for fbd, the args will be a dict.
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"[Instruction: Name:{self.name}, Args:{self.args}]"
    def __str__(self):
        return f"Name:{self.name}, Args:{self.args}"

def parse_file_content(content):
    #print("Acquired File...")
    #print(content)
    alnumpattern = re.compile('[\W_]+')
    # Define data structures to store information
    controller_info = {}
    current_controller = None
    current_program = None
    current_routine = None
    current_fbd_sheet = None
    current_fbd_routine = None
    current_st_routine = None
    current_fbd_block = None
    current_task = None
    current_attributes = None
    current_datatype = None
    current_module = None
    current_aoi = None
    current_tags = None
    current_parameters = None
    programs_to_assign = []  # Store programs temporarily
    current_routine_data = []  # Store routine lines
    skipGarbage = False
    skipTagForceData = False
    for line in content:
        line = line.strip()
        #print(line);

        #---------------CONTROLLER
        #TO DO: fix it so it captures the processorType and doesn't look for lines that start with '('
        if len(line.strip()) > 0:
            if line.startswith('CONTROLLER'):
                # Start of a controller section
                #print("Controller: " + str(line))
                controller_name = line.split(' ')[1]
                current_controller = controller_name
                controller_info[current_controller] = {'ATTRIBUTES': [], 'DATATYPES': {}, 'MODULES': {}, 'AOI':{}, 'TAGS': [], 'TASKS': {}}
                current_attributes = []
                try:
                    proc = line.split(':=')[0].split('(')[1].strip()
                    val = line.split(':=')[1].strip()[:-1]
                    current_attributes.append([proc, val])
                except:
                    1;
            
            elif current_controller is not None and line.startswith(')') or line.endswith(')') and current_task is None and current_attributes is not None:
                # End of controller attributes
                controller_info[current_controller]['ATTRIBUTES'] = current_attributes
                current_attributes = None

            elif current_controller is not None and current_task is None and current_attributes is not None:
                # Inside controller attributes
                attributes = line[:-1].split(':=')
                #print("attribute: " + str(attributes))
                current_attributes.append(attributes)

            #--------------DATATYPE
            elif line.startswith('DATATYPE'):
                # Start of a datatype section
                datatype_name = line.split(' ')[1]
                current_datatype = datatype_name
                #print("Datatype: " + str(datatype_name))
                datatype_info = {}
                
            elif line == 'END_DATATYPE' and current_datatype is not None:
                # End of the datatype section
                controller_info[current_controller]['DATATYPES'][current_datatype] = datatype_info
                current_datatype = None

            elif current_datatype is not None:
                # Inside the datatype section (member information)
                #print("member: " + str(line.split(' ')))
                member_type, member_name = line.split(' ')[:2]
                datatype_info[member_name] = member_type

            #-------------MODULE
            elif line.startswith('MODULE'):
                # Start of a module section
                module_name = line.split(' ')[1]
                #print("module: " + str(module_name))
                current_module = module_name
                module_info = {}
                #the first module data point is often on the same line as the module header. Capture these.
                try:
                    term = line.split(':=')[0].split('(')[1].strip()
                    val = line.split(':=')[1].strip()
                    module_info[term] = val
                except:
                    1;
                    
            elif line == 'END_MODULE' and current_module is not None:
                # End of the module section
                #detect duplicate module names
                if current_module in controller_info[current_controller]['MODULES']:
                    current_module = f"{module_name}_{len(controller_info[current_controller]['MODULES'])}"
                controller_info[current_controller]['MODULES'][current_module] = module_info
                current_module = None

            elif current_module is not None:
                # Continuation of module attributes
                #print("module data: " + str(line))
                try:
                    key, value = line.split(':=')
                    module_info[key.strip()] = value.strip()
                except:
                    1;#this has the effect of ignoring any lines with no ":=" or more than one ":="
                
            #---------------ADD_ON_INSTRUCTION
            elif line.startswith('ADD_ON_INSTRUCTION_DEFINITION'):
                #start of AOI section
                aoi_name = line.split(' ')[1]
                #print("aoi: " + str(aoi_name))
                current_aoi = aoi_name
                aoi_info = {'PARAMETERS': {}, 'TAGS': {}, 'ROUTINES': {}}
                #the first aoi data point is often on the same line as the aoi header. Capture these.
                try:
                    term = line.split(':=')[0].split('(')[1].strip()
                    val = line.split(':=')[1].strip()
                    aoi_info['PARAMETERS'][term] = [val,'']
                except:
                    1;

            elif line == 'END_ADD_ON_INSTRUCTION_DEFINITION' and current_aoi is not None:
                # end of the aoi section
                controller_info[current_controller]['AOI'][current_aoi] = aoi_info
                current_aoi = None
                current_tags = None #tags are declared inside AOIs
                current_routine = None #routines are declared inside AOIs
                current_parameters = None #parameters are declared inside AOIs

            #---AOI section includes parameters, tags, and routines, so the "current_aoi is not none" block is after those.

            #---------------PARAMETERS for AOI
            elif line.startswith('PARAMETERS') and current_aoi is not None:
                current_parameters = {}

            elif line.startswith('END_PARAMETERS') and current_parameters is not None and current_aoi is not None:
                aoi_info['PARAMETERS'] = current_parameters
                current_parameters = None
                
            elif current_parameters is not None:
                try:
                    if '(' in line:
                        #we only care about the first line in the parameter definition
                        parameter_name = line.split(' ')[0]
                        parameter_info = [line.split(' ')[2],'']
                        if "Description" in line:
                            #Sometimes parameters have useful descriptions.
                            parameter_info[1] = line.split(':=')[1].strip()
                        current_parameters[parameter_name] = parameter_info
                except:
                    1; #It's ok if we don't get every parameter. This is low priority data.
                            

            #---------------TAG
            #'TAGS': {'tag name' : {'type': tag_datatype, 'value': tag_value}}
            elif line.startswith('TAG') or (line.startswith('LOCAL_TAGS') and current_aoi is not None):
                #if (line.startswith('LOCAL_TAGS') and current_aoi is not None):
                    #print("found some AOI tags")
                # Start of a tag section
                #print("Getting tags for scope (program): " + str(current_program))
                current_tags = {}  # Initialize a list to store tag information

            elif line == 'END_TAG' or line == 'END_LOCAL_TAGS':
                # End of the tag section
                if current_aoi is not None:
                    aoi_info['TAGS'] = current_tags
                elif current_program is not None:
                    program_info['TAGS'] = current_tags
                elif current_controller is not None:
                    controller_info[current_controller]['TAGS'] = current_tags
                current_tags = None
                    
            elif current_tags is not None:
                # Inside the TAG section
                #print("tag line: " + str(line))
                #get tag name and datatype


                #---------------------TO DO
                #--------------------- Improve tag parsing and get rid of all the "try except" in this elif.
                if current_aoi is not None:
                    #these lines are usually: "tagname : datatype (garbage...
                    if '(' in line:
                        try:
                            tagstuff = line.split(' ')
                            tag_value = 'N/A'
                            tag_name = tagstuff[0].strip()
                            tag_datatype = tagstuff[2].strip()
                            tag_description = 'N/A'
                            if ("Description" in line) and (' := ' in line) and (len(line.split(' := ')) > 1):
                                tag_description = line.split(' := ')[1]
                            current_tags[tag_name] = {'type': tag_datatype, 'value': tag_value, 'description': tag_description}
                        except:
                            1;

                else:
                    if line.startswith("TagForceData"):
                        skipTagForceData = True
                    if skipTagForceData:
                        if ';' in line:
                            skipTagForceData = False
                    else:
                        if not skipGarbage:
                            parts = line.split(':')
                            tag_name = parts[0].strip()
                            tag_description = 'N/A'
                            if ("Description" in line) and (' := ' in line) and (len(line.split(' := ')) > 1):
                                tag_description = line.split(' := ')[1]
                            if " OF " in line:
                                tag_datatype = line.split(' ')[2]
                                tag_value = "Alias" #no value for alias tags
                            else:
                                try:
                                    tag_datatype = parts[1].split(':=')[0].strip().split()[0]
                                except:
                                    pass
                            if '(' in line and not ')' in line:
                                skipGarbage = True
                        
                        #get tag value
                        if not " OF " in line: #no value for alias tags
                            if ')' in line: #detect multi-line tags. Value will be on the last line.
                                try:
                                    tag_value = line.split(')')[1].split(':=')[1][:-1].strip()
                                    current_tags[tag_name] = {'type': tag_datatype, 'value': tag_value, 'description': tag_description}
                                    skipGarbage = False;
                                except:
                                    skipGarbage = False;
                                    pass
                            elif not skipGarbage:
                                try:
                                    tag_value = line.split(':=')[1][:-1].strip()
                                    current_tags[tag_name] = {'type': tag_datatype, 'value': tag_value, 'description': tag_description}
                                except:
                                    pass

            #----------------PROGRAM
    #                           {
    #                              'TAGS' : {'tag name' : {'type': tag_datatype, 'value': tag_value}},
    #                              'ROUTINES' : {'routine name' : ["individual line"]}
    #                           }
            elif line.startswith('PROGRAM'):
                # Start of a program section
                program_name = line.split(' ')[1]
                current_program = program_name
                #print("Program: " + str(program_name))
                program_info = {'TAGS' : {}, 'ROUTINES' : {}}

            elif line == 'END_PROGRAM':
                # End of the program section
                programs_to_assign.append((current_program, program_info))
                current_program = None

            #------------FBD Routine
            elif (current_program or current_aoi) and line.startswith('FBD_ROUTINE'):
                
                fbd_routine_name = line.split(' ')[1]
                current_fbd_routine = fbd_routine_name
                getting_comment = False
                current_fbd_routine_data = []
                #print("routine: " + str(fbd_routine_name) + " - " + current_program)
                fbd_sheet_list = []
                skipGarbage = False

            elif current_fbd_routine and line.startswith('END_FBD_ROUTINE'):
                #print("Contents: " + str(current_fbd_routine_data))
                if current_aoi:
                    aoi_info['ROUTINES'][current_fbd_routine] = current_fbd_routine_data
                elif current_program:
                    program_info['ROUTINES'][current_fbd_routine] = current_fbd_routine_data
                current_fbd_routine = None

            elif current_fbd_routine is not None:
                #routine is list of sheets.
                #each sheet = [
                #                "fbd",
                #                [Instruction, Instruction, Instruction]
                #               ]
                #current_fbd_sheet = None
                #current_fbd_routine = None
                #current_fbd_block = None
                if line.startswith('LOGIC') and ("Orig" not in line):
                    #we only care about the "original" code. We will not display online or offline edits saved in the l5k file.
                    skipGarbage = True
                elif line.startswith('END_LOGIC'):
                    skipGarbage = False
                if not skipGarbage:
                    #print("it's not garbage")
                    if line.startswith('SHEET'):
                        #print("starting a sheet")
                        #beginning of fbd_sheet
                        #sheets are treated like a rung of code starting with "fbd" instead of the ladder "RC:" or "N:"
                        current_fbd_routine_data.append(["fbd"])
                        current_fbd_sheet = []
                    elif line.startswith('END_SHEET'):
                        #end of sheet section
                        #print("closing a sheet")
                        #print(current_fbd_sheet is None)
                        current_fbd_routine_data[-1].append(current_fbd_sheet)
                        current_fbd_sheet = None
                    elif (current_fbd_sheet is not None) and (current_fbd_block is None):# and not ("(" in line):
                        #beginning of fbd_block
                        #instructions in sheets are given as blocks
                        #print("sheet is not none, and block is none", line)
                        splitline = line.split(' ')
                        #print(splitline)
                        #get the block name
                        current_fbd_block = [splitline[0].strip(), {}]
                        #print(current_fbd_block)
                        #blocks usually have a block ID for wire drawing on the same line as the name
                        current_fbd_block[1][alnumpattern.sub('', splitline[2]).strip()] = alnumpattern.sub('', splitline[-1]).strip()
                    elif (current_fbd_block is not None) and line.startswith('END_'+current_fbd_block[0]):
                        #print("block is not none and it's the end of a block.", line)
                        #end of block
                        current_fbd_sheet.append(Instruction(name = current_fbd_block[0], args = current_fbd_block[1]))
                        #print(current_fbd_block)
                        current_fbd_block = None
                    elif current_fbd_block is not None:
                        #print("block is not none, and we're expecting line data", line)
                        splitline = line.split(':=')
                        #inside blocks are several rows of "A := B,)"
                        current_fbd_block[1][splitline[0].strip()] = splitline[1][:-1].replace('$n','\n').strip()
                    elif not (line.startswith("SheetSize") or line.startswith("SheetOrientation")):
                        print("Unhandled FBD Rung: ", line)

            #------------Structured Text Routine
            elif (current_program or current_aoi) and line.startswith('ST_ROUTINE'):
                # Start of a routine section within a program
                current_st_routine = line.split(' ')[1]
                #print("routine: " + str(routine_name) + str(" -program" if current_program else " -aoi"))
                current_st_routine_data = []

            elif current_st_routine is not None and line == 'END_ST_ROUTINE':
                #print("closing out st routine with...\n",current_st_routine_data)
                if current_aoi:
                    aoi_info['ROUTINES'][current_st_routine] = current_st_routine_data
                elif current_program:
                    program_info['ROUTINES'][current_st_routine] = current_st_routine_data
                current_st_routine = None

            elif current_st_routine is not None:
                #print("appending line to st routine\n\t", line)
                current_st_routine_data.append(["ST",line])
            
            #------------Ladder Routine
            elif (current_program or current_aoi) and line.startswith('ROUTINE'):
                # Start of a routine section within a program
                routine_name = line.split(' ')[1]
                current_routine = routine_name
                getting_comment = False
                #print("routine: " + str(routine_name) + str(" -program" if current_program else " -aoi"))
                current_routine_data = []

            elif current_routine and line == 'END_ROUTINE':
                # End of the routine section
                #print("Size: " + str(len(current_routine_data)) + " rungs")
                if current_aoi:
                    aoi_info['ROUTINES'][current_routine] = current_routine_data
                elif current_program:
                    program_info['ROUTINES'][current_routine] = current_routine_data
                current_routine = None

            elif current_routine is not None:
                # Inside the routine section, store each line in the routine data array

                if line.startswith("RC:") or (getting_comment and not line.startswith("N:")):
                    # Display rung comments as plain text
                    if getting_comment:
                        if line.replace('"','').strip() not in ["$N", ';']:
                            current_routine_data.append(["RC:",line.replace('$N','')])
                    else:
                        label_text = line[4:]  # Remove "RC:" prefix
                        if label_text.replace('"','').strip() not in ["$N", ';']:
                            current_routine_data.append(["RC:",label_text.replace('$N','')])
                    getting_comment = True
                elif line.startswith("N:") or line.startswith("rN:"): #rN is for rungs being replaced. We don't care about edits.
                    getting_comment = False
                    #Logical_Rung = [
                    #                "N:",
                    #                ["instruction",["arg1","arg2","arg2"]],
                    #                ["[",[]],
                    #                [",",[]]
                    #                ...["",[]]
                    #               ]
                    #process logical rungs
                              
                    
                    #get rid of "N:"
                    rung = line[2:].strip() #for "rN:" rungs, this takes us to ":", which will be ignored by the if-statements to follow.
                    #First we iterate through once to separate all the elements.
                    def parse_my_rung(istring, i=0):
                        current_instruction = ["",[]]
                        current_item = ""
                        getting_instruction = False;
                        getting_arguments = False;
                        current_rung = []
                        comma = False
                        parentheses_nest = 0
                        while i < len(istring): #TO DO: Improve parentheses handling for CPT instructions.
                            letter = istring[i]
                            #Instructions and instruction arguments are alphanumeric
                            if letter.isalnum() or letter == "_" or (getting_arguments and letter not in ",)"):
                                if not (getting_arguments or getting_instruction):
                                    getting_instruction = True
                                current_item += letter
                            #Instruction Arguments are in parentheses, comma separated.
                            elif letter == "(" and getting_instruction:
                                getting_instruction = False
                                getting_arguments = True
                                current_instruction[0] = current_item
                                current_item = ""
                            elif letter == "(" and getting_arguments:
                                #it's probably a CPT statement...
                                parentheses_nest += 1
                                current_item += letter
                            elif letter == "," and getting_arguments:
                                current_instruction[1].append(current_item)
                                current_item = ""
                            elif letter == ")" and getting_arguments:
                                if parentheses_nest > 0:
                                    parentheses_nest -= 1
                                    current_item += letter
                                else:
                                    getting_arguments = False
                                    current_instruction[1].append(current_item)
                                    current_item = ""
                                    #if current_routine == "AO_Mapping":
                                    #    print(current_instruction)
                                    current_rung.append(Instruction(current_instruction[0],current_instruction[1]))
                                    current_instruction = ["",[]]
                            #I don't know if instructions can exist without parentheses.
                            elif letter == "," and getting_instruction:
                                #print("found odd comma")
                                #print(current_routine, istring, current_instruction)
                                getting_instruction = False
                                #current_rung.append(current_instruction)
                                current_instruction = ["",[]]
                            #logical branching is any bracket or comma not already covered
                            elif letter == "[":
                                rungGroup = []
                                nested_rung, i, comma = parse_my_rung(istring, i+1)
                                while comma:
                                    rungGroup.append(nested_rung)
                                    nested_rung, i, comma = parse_my_rung(istring, i+1)
                                rungGroup.append(nested_rung)
                                current_rung.append(rungGroup)
                            elif letter == ",":
                                return current_rung, i, True
                            elif letter == "]":
                                return current_rung, i, False
                            i += 1
                        return current_rung, i, False
                    this_rung = ["N:"]
                    notblah, blah, blah = parse_my_rung(rung)
                    this_rung.append(notblah)
                    current_routine_data.append(this_rung)
                    #then we recurse the separated list to generate a more manageable data structure

                else:
                    print("Unhandled rung: " + str(line))

            #-----------TASK
            elif line.startswith('TASK'):
                # Start of a task section
                task_name = line.split(' ')[1]
                current_task = task_name
                current_task_programs = {}
                skipGarbage = True

            elif line == 'END_TASK':
                # End of the task section
                if current_controller:
                    for program, programdata in current_task_programs.items():
                        controller_info[current_controller]['TASKS'][current_task] = current_task_programs
                    #controller_info[current_controller]['TASKS'][current_task] = {'PROGRAMS': current_task_programs}
                current_task = None
                current_task_programs = {}

            elif current_task is not None:
                # Inside the task section, look for programs
                # Programs are listed as semicolon-separated values, let's split them and assign them
                if line.strip().endswith(')'):
                    skipGarbage = False
                if not skipGarbage:
                    programs_list = line.split(';')
                    for program_name in programs_list:
                        program_name = program_name.strip()
                        if program_name:
                            # Find the program info in programs_to_assign and assign it to the current task
                            for program, program_info in programs_to_assign:
                                if program == program_name:
                                    current_task_programs[program] = program_info

    # Now, you have parsed the L5K file and organized the data into the desired data structure.

    # You can access the extracted data as needed.
    #print("Controller Info:")
    #print(controller_info)
    return controller_info
