# mesoweatherepw.py
# MesoWest Weather CSVs to Hourly Weather for input to EPW file via Elements
# Author(s):    Brian Woo-Shem
# Version:      0.6 Beta
# Last Updated: 2021-08-09

# Change Parameter Variables to match input csv
# See instructions on Google Doc or PDF.

# Import ----------------------------------------------------------------
import csv
import numpy as np

# PARAMETER VARIABLES TO CHANGE -----------------------------------------
# CSV input file
sourcefile = "KSJC_2019_Metric.csv" 

outputfile = "SJ_KSJC_2019_Processed_1.csv"  

# Choose station type for which columns are needed
#   'NWS'   NWS/FAA Type Stations (eg KSJC, KSFO)
#   'APR'   APRSWXNET/Citizen Weather Observer Program stations (eg https://mesowest.utah.edu/cgi-bin/droman/meso_base_dyn.cgi?stn=E6095)
station = 'NWS'

# List of columns from source to look at. Col A is indexed as 0, B = 1, ..., Z = 25
# For NWS/FAA Type Stations (eg KSJC, KSFO)
if station == 'NWS':
    getcols = [3,5,6,30,37]
    # Headers for first row. Leave first four entries as-is!!!
    # First output row will be headers, all others are data
    headers = ['Year','Month','Day','Hour',"Drybulb","RH","Windspeed","Dewpoint","Pressure"]

# For APRSWXNET/Citizen Weather Observer Program stations (eg https://mesowest.utah.edu/cgi-bin/droman/meso_base_dyn.cgi?stn=E6095)
elif station == 'APR':
    getcols = [3,4,5,9,12,16]
    headers = ['Year','Month','Day','Hour',"Drybulb","RH","Windspeed","SolarRad","Dewpoint","Pressure"]

elif station == 'E9060': #This one was different for no apparent reason
    getcols = [3,4,5,9,11,15]
    headers = ['Year','Month','Day','Hour',"Drybulb","RH","Windspeed","SolarRad","Dewpoint","Pressure"]

# For custom
elif station == 'custom':
    getcols = [3,5,6,11,13]
    headers = ['Year','Month','Day','Hour',"Drybulb","RH","Windspeed","Dewpoint","Pressure"]


# When to start - must match input data
startyear = 2019
startmonth = 1
startday = 1
starthour = 0

# length of output = header + 365 days * 24 hours per day
numdays = 7 # How many days of data; often want 365
tsperday = 24 #Timesteps per day; usually want 24
outrows = int(1 + numdays*tsperday) # Don't change this

# Number of header rows (non-data) at top to skip
headrows = 8 #Usually 8

verbose = False

# Automatic - Don't change ----------------------------------------------
# Initializing variables, indices, etc.
y = startyear
m = startmonth
d = startday
h = starthour

r = 1
s = 0

dat = np.zeros((24,len(getcols)+4))
dat.fill(np.nan) # For first data row

print('\n================ MesoWest Weather -> EPW V0.6 ================')

# Date & Time Handling Functions ----------------------------------------

# Function for figuring out what day is tomorrow ---
# Handles end of month, end of year, and leap year
def tmrw(y, m, d):
    leap = False #temporary override to ignore leap year for EP data
    if d < 1: # Handle invalid negative nums or zero
        print('FATAL ERROR: Invalid day, cannot be less than 1. \n\nx x\n >\n ⁔\n')
        exit()
    # Determine leap year. If it is 2000, 2004, 2008, 2012, ..., identify and give Feb 29 days
    if leap and ((y-2000) % 4 == 0): daysinmon = [31,29,31,30,31,30,31,31,30,31,30,31]
    else: daysinmon = [31,28,31,30,31,30,31,31,30,31,30,31] # Normal year or ignoring leap day
    # Check if next day would be beginning of a new month
    if d >= daysinmon[m-1]:
        d = 1
        m += 1 #recall month index mi goes from 0 to 11
        # Check for end of year
        if m > 12: # If m = 13 or more, loop back to new year
            m = 1 # if past December, loop back to Jan
            y += 1
    else: #Double digit, middle of month somewhere
        d += 1
    return [y,m,d]

# Returns writedatetime - readdatetime
def checkday(y, m, d, ry, rm, rd):
    leap = False #temporary override to ignore leap year for EP data
    offset = 0
    if ry != y or rm != m or rd != d:
        # Years
        offset = offset + 365*(y-ry)
        # Months
        # Determine leap year. If it is 2000, 2004, 2008, 2012, ..., identify and give Feb 29 days
        if leap and ((y-2000) % 4 == 0): daysinmon = [31,29,31,30,31,30,31,31,30,31,30,31]
        else: daysinmon = [31,28,31,30,31,30,31,31,30,31,30,31] # Normal year or ignoring leap day
        offset = offset + sum(daysinmon[:m]) - sum(daysinmon[:rm])
        # Days
        offset = offset + d - rd
    return offset

# Turns one or two digit number to two digits string ( 1 -> '01') ( 12 -> '12')
def dig2(n):
    if n < 10: # Handle leading zero on single digit days
        n2str = '0'+str(n)
    else:
        n2str = str(n)
    return n2str

# Returns date as a string. y, m, d should be int, delim is a string. 
# ex: datestr(2020, 2, 3, '-') -> 2020-02-03
def datestr(y, m, d, delim):
    return str(y) + delim + dig2(m) + delim + dig2(d)

def datestr_mdy(y, m, d, delim):
    return dig2(m) + delim + dig2(d) + delim + str(y)

# Extracts integers for year, month, day from MesoWest time code in form MM/DD/YYYY hh:mm PDT
# Returns as list [year, month, day]
def decodedate(timecode):
    try:
        m = int(timecode[:2])
        d = int(timecode[3:5])
        y = int(timecode[6:10])
    except ValueError:
        print("Error: Invalid DateTime code string")
        exit()
    return [y,m,d]

# Extracts integers for hour, minute from MesoWest time code in form MM/DD/YYYY hh:mm PDT
# Returns as list [hour, minute]
def decodetime(timecode):
    try:
        timeind = timecode.find(':')
        rhour = int(timecode[timeind-2:timeind])
        rminute = int(timecode[timeind+1:timeind+3])
    except ValueError:
        print("Error: Invalid DateTime code string")
        exit()
    return [rhour,rminute]

    
# Open input & output files, main processing code -----------------------
with open(sourcefile, newline='\n') as source, open(outputfile, 'w', newline='') as output:
    # Create csv reader object
    rin = csv.reader(source, delimiter=',')
    
    # convert rin to list so elements can be accessed out of order
    entiresource = list(rin)
    inrows = len(entiresource)
    
    # Create writer obj
    w = csv.writer(output, delimiter=',')
    
    # Write out the headers
    w.writerow(headers)
    wout = 0
    
    # Skip header rows --------------------------------------------------
    # Technically could be accomplished by setting r = headrows and deleting the stuff between the 2 prints
    # Doing it this way so it's easier to debug if it is skipping too much or too little
    print("--- Skipping the following rows ---")
    while r < headrows:
        line = entiresource[r]
        print(line)
        r += 1
    print("-----------------------------------")
    
    # Code for every data row --------------------------------------------
    # Repeat until finished with expected output
    while wout < outrows:
        if r < inrows: # Ensure there is another row left
            
            # line is temporary variable to hold current data row only
            line = entiresource[r]
            print("Read line:")
            print(line)
            
            #Process date row -------------------------------------------
            # Find date
            ry,rm,rd = decodedate(line[1])
            daydiff = checkday(y,m,d,ry,rm,rd)
            # Check if year, month, and day are the same between what the row says and what we want to write
            if daydiff != 0:
                print("Warning: Possible date mismatch.")
                print("Input reader date: ", str(ry),'-',str(rm),'-',str(rd))
                print("Output date: ", str(y),'-',str(m),'-',str(d))
            
            #find time
            rhour, rmin = decodetime(line[1])
            timediff = daydiff*24+h-rhour
            if verbose: 
                print("Input reader date:  ", str(ry),'-',str(rm),'-',str(rd))
                print("Input row time :    ",str(rhour),":",str(rmin))
                print("Offset from output: ", timediff)
            print("Output to: ", datestr(y,m,d,'-'), "   Hour:  ", str(h))
            
            # Determine if it is the next hour --------------------------
            #   Minutes (h-1):31 - h:30 go to hour h
            midnightbug = (rhour == 23 and h == 0)
            if (rhour >= h and rmin > 30 and not midnightbug or timediff < -1):
                # IF next hour, compute average data, write, and reset
                # Write current hour of data to file and clean up data  ##NEED to do this BEFORE iterating the day or else it is off by one hour!!!
                if verbose:
                    print("Data Matrix Since Last Written Hour: ")
                    print(dat)
                # Take average of each col in hrdata, but neglect 
                hrdata = np.nanmean(dat, axis=0)
                #print("Take mean:")
                #print(hrdata)
                # First four columns are year, month, day, hour
                hrdata[0:4] = [y,m,d,h]
                print("Writing data from ", s, " data rows:")#, hrdata.tostring())
                print(hrdata)
                w.writerow(hrdata)#.tostring())
                dat.fill(np.nan) # Reset to empty
                wout += 1 # Increment data lines written to output
                s = 0 # Reset sets per hour counter
                print(" ---> Next hour ---> ")
                
                # Increase hour. Valid hours are [1, 24]
                # If it is the end of a day
                if h >= 23:
                    # Call function to figure out what the next day is (handles month, year, leap day changeovers)
                    y,m,d = tmrw(y,m,d)
                    print("New Day Detected: ", str(y),'-',str(m),'-',str(d))
                    h = 0
                else:
                    h += 1
            # END next hour code -----------------------------
            
            if timediff > 0: #catch if somehow the written data is ahead
                r += 1
            else:
                # Adding current data row
                # Make first 4 cols not nan because they will be used for date + hour info
                dat[s,0:4] = 0
                # For debugging
                if verbose: print("num data row sets since last new hour: ", str(s))
                
                # Add values to associated part of dat ----------------------
                b = 4 # What col index to start on?
                # Check and assign values of interest one at a time
                for c in getcols:
                    try: dat[s,b] = float(line[c])
                    except ValueError: print("Warning: Invalid data point; ignoring:   \'",line[c],"\'") 
                    #print(dat[s,:])
                    b += 1 # next iteration at new col index
                r += 1 # increment num rows completed
                s += 1 # increment sets per hour
        # END code for 1 row --------------------------------------------
        else:
            #something is wrong because there is no more input
            print("Error: Input file is shorter than requested output!!!!!!!!!!! ")
            print("Attempting to write leftover data")
            print("Data Matrix Since Last Written Hour: ")
            print(dat)
            # Take average of each col in hrdata, but neglect 
            hrdata = np.nanmean(dat, axis=0)
            # First four columns are year, month, day, hour
            hrdata[0:4] = [y,m,d,h]
            print("writing data:")
            print(hrdata)
            w.writerow(hrdata)
            print("WARNING: Data set may be incomplete. Ignore if this is the expected last hour.")
            
            break
    
    print("\nData Processing Complete!")
    # Save and exit file
    output.close()
    print("Exported Data as:   "+ outputfile)
    print('\n=======================================================\n')
