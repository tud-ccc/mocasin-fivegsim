# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo

class TraceFileManager():
    """ Allows navigation along a LTE trace file with the following format:    
    <number of UE>
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    ---------- <Subframe Number>
    """
    def __init__(self, TF_name, TF_directory = "."):
        self.TF_name = TF_name
        self.TF_directory = TF_directory
        self.TF_file = open(self.TF_directory + '/' + self.TF_name, "r")
                
        self.TF_current_subframe = 0            # Current subframe Id
        self.TF_current_subf_size = 0           # Size of current subframe
        self.TF_current_trace = 0               # index of current trace on current subframe
        self.TF_current_line = 0                # current line in file 
        
        self.TF_error = False                   # TODO: error handling
        self.TF_EOF = False                     # End of File
        
        self.end_of_frame = True                # End of frame
        self.nextline = self.TF_file.readline() # read first line    
    
    class Trace():
        """ Represents a single LTE trace.
        """
        def __init__(self, base_station_id, CRNTI, PRBs, layers, modulation_scheme, UE_criticality,  is_CRNTI_new):
            self.base_station_id = base_station_id          # Base Station Identifier which serves the UE
            self.CRNTI = CRNTI                              # A kind of UE Identifier
            self.PRBs = PRBs                                # The number of physical resource blocks allocated to the UE
            self.layers =  layers                           # The number of (independent) layers of communication
            self.modulation_scheme =  modulation_scheme     # Modulation scheme
            self.UE_criticality = UE_criticality            # UE Traffic type
            self.is_CRNTI_new = is_CRNTI_new                # Is CRNTI seen before for [No/Yes] ?

    class Subframe():
        """ Represents a LTE subframe containing a collection of LTE traces.
        """
        def __init__(self, subf_id):
            self.trace = list()
            self.id = subf_id
            
        def add_trace(self, trace):
            self.trace.append(trace) # Add new trace to subframe
            
    def read_file(self):
        """ Reads the whole file and returns a list of Subframe objects containing all LTE subframes contained in file
        
        Do not use together with get_next_line(), get_next_trace(), get_next_subframe() or get_subframe methods(), which allow 
        a faster way to navigate through the file.
        read_file instead reads the whole file at once slowing down the process, specially when only one subframe is needed.
        """
        if self.TF_file.mode == 'r':    # file is open with read permissions
            lines = self.TF_file.readlines()    # load all lines
            lines.insert(0, self.nextline)
            lines = [x.strip() for x in lines]
            lines = [x.strip('-') + ' 0' if x.find("----------") != -1 else x for x in lines] # remove '-' chars and replace them with '0'
            lines = [x.split() for x in lines]              # split lines
            lines = [list(map(int, line)) for line in lines] # cast string to int

            subframe_list = list()
            traces = list()
            sf_lenght=0
            trace_cnt = 0
            state = 0
            
            for line in lines:
                if state == 0:
                    if len(line) == 1:
                        sf_lenght = line[0]
                        if sf_lenght == 0:
                            state = 2
                        else:
                            state = 1
                    #else :          #drop line
                        #lines.pop(lines.index(line))
                elif state == 1:
                    if len(line) == 7:
                        ntrace = self.Trace(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
                        traces.append(ntrace)
                        trace_cnt += 1
                        if sf_lenght == trace_cnt:
                            state = 2
                    #else :          #drop line
                        #lines.pop(lines.index(line))
                elif state == 2:
                    if len(line) == 2:
                        subframe = self.Subframe(line[0])
                        subframe.trace = traces
                        subframe_list.append (subframe)
                        traces = list()
                        trace_cnt = 0
                        state = 0
                    #else :          #drop line
                        #lines.pop(lines.index(line))
                        
        return subframe_list
            
    
    def get_next_line(self):
        """ Allows navigation along the file line by line
        reads the next line in file and returns list object with all int numbers in line.
        """
        if self.TF_file.mode == 'r':    # file is open with read permissions
            line = self.nextline
            self.nextline = self.TF_file.readline()
            
            if line=="":                # End of File
                self.TF_EOF = True
                return None
            
            line = line.strip(" /n").split()
            
            # 3 types of line
            if len(line) == 1:            # start subframe
                self.TF_current_subf_size = int(line[0])
                self.TF_current_trace = 0
                self.TF_current_subframe += 1
                self.end_of_subframe = False
                
            elif len(line) == 2:          # end of subframe
                if line[0].find('-') != -1:
                    line.pop(0)
                    self.end_of_subframe = True
                    if int(line[0]) != self.TF_current_subframe:
                        self.TF_error= True
                    if self.TF_current_trace != self.TF_current_subf_size:
                        self.TF_error= True
                
            elif len(line) == 7:          # LTE trace
                self.TF_current_trace += 1
                
            else:
                self.TF_error= True
                
            line = [int(i) for i in line]   # cast string to int
            self.TF_current_line +=1
            
        if self.nextline.find('-') != -1:
            self.end_of_subframe = True
            
        return line
                
    def get_next_trace(self):
        """ search for next LTE trace into the file and returns Trace object with LTE trace
        """
        while True:
            line =self.get_next_line()
            if self.TF_EOF == True:
                ntrace = None
                break
            if len(line) == 7:
                ntrace = self.Trace(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
                break
        return ntrace
               
    def get_next_subframe(self):
        """ search for next subframe into the file and returns Subframe object with the whole subframe
        """
        
        while True:                         # Go to the next starting frame line
            line = self.get_next_line()
            if self.TF_EOF == True:
                break
            elif (len(line) == 1) and (self.end_of_subframe == False):
                break
            
        subf_id = self.TF_current_subframe
        subframe = self.Subframe(subf_id)
            
        while True:                         # Add all traces in current subframe
            ntrace = self.get_next_trace()
            subframe.add_trace(ntrace)      # Add trace to subframe
            if self.TF_EOF == True:
                break
            if self.end_of_subframe == True:
                break
            
        return subframe
    
    def get_subframe(self, subf_id):
        """ search for subframe with id subf_id in file and returns Subframe object
        """
        while True:
            nsubframe = self.get_next_subframe()
            if self.end_of_file() == True:
                break
            if nsubframe.id == subf_id:
                break
        return nsubframe
            
    def end_of_subframe(self):
        """ Returns True if the next line in file is an endOfSubframe line
        """
        return self.end_of_subframe
    
    def end_of_file(self):
        """ Returns True if end of file
        """
        return self.TF_EOF