# getWholesaleCAISO.py
# Author(s):    Brian Woo-Shem
# Version:      1.2 Stable
# Last Updated: 2021-11-07
# Changelog:
# - Bug fix (array indexing issue) so output is correctly synchronized to 5 minute timesteps.
#   WARNING: Older data using older code versions is incorrect - data is offset by tshr * h!
#
# Get wholesale data from CAISO website
# Handles any number of days (tested 1 day to over 1 year), so long as CAISO data exists
# Can get leap day as an option
# Long code but most is error handling for date inputs and data received. 

# This version backdates 1 so it writes 2nd to last day in filename so it can go into UCEF sim better

# getWholesaleCAISO.py <data_type> <year> <month> <day> <number_of_days> <optional_options>
# <data_type>  d for day ahead, r for real time
# <year>       four digit year of first day to get (eg. 2020)
# <month>      month of the first day to get (eg. January, Jan, or 1)
# <day>        day of month for the first day (eg. 21)
# <number_of_days>    how many days to get data for. 1 = only get the day specified
# <optional_options>  Additional parameters, optional
#   -v      verbose: provide extra outputs for user readability
#   -d      debug: provide detailed outputs for debugging
#   -leap   include leap years in date calculation
#   -s      safe: waits 10 seconds between calls to caiso server to avoid breaking it
#   -fast   fast unsafe: removes all time delays for fastest data acquisition. WARNING: you are responsible if this mode breaks something or violates the CAISO Terms of Use.
# Example Inputs:
#   getWholesaleCAISO.py d 2020 8 3 7     #Returns week starting Aug 3, 2020 with day-ahead values
#   getWholesaleCAISO.py d 2020 August 3 7 -v     #Same as prior but with more outputs


# Import ---------------------------------------------------------------
import bs4 as BeautifulSoup
import re
import urllib3
import numpy as np
import sys
import requests
import time
# also need to install module lxml as a dependency for one of these

header = '\n=========== getWholesaleCAISO.py V1.2 ==========='
closer = '================================================\n'

# Accept User Inputs ---------------------------------------------------
# Catch not enough arguments
if 6 > len(sys.argv): 
    # Catch only the filename.py
    if 2 > len(sys.argv): print('FATAL ERROR: Missing parameters.\nFor more info, run\n\tgetWholesaleCAISO.py -h \n\nx x\n >\n ⁔\n')
    # Identify single entry options
    elif 2 == len(sys.argv):
        if "-h" == sys.argv[1]:
            helpme = "\nSYNTAX:\n\tgetWholesaleCAISO.py <data_type> <year> <month> <day> <number_of_days> <optional_options>\n\n\t<data_type>  d for day ahead, r for real time\n\t<year>       four digit year of first day to get (eg. 2020)\n\t<month>      month of the first day to get (eg. January, Jan, or 1)\n\t<day>        day of month for the first day (eg. 21)\n\t<number_of_days>    how many days to get data for. 1 = only get the day specified\n\t<optional_options>  Additional parameters, optional\n\t   -v      verbose: provide extra outputs for user readability\n\t   -d      debug: provide detailed outputs for debugging\n\t   -leap   include leap years in date calculation\n\t   -s      Server Safe mode; adds delay to avoid crashing server but takes longer.\n\t   -fast   fast unsafe: removes all time delays for fastest data acquisition. WARNING: you are responsible if this mode breaks something or violates the CAISO Terms of Use.\n\nFor licensing info, run\n\tgetWholesaleCAISO.py -l\n\nRequired Modules: beautifulsoup4, urllib3, numpy, os_sys, lxml, requests\n"
            print(header+helpme+closer)
        elif "l" in sys.argv[1]:
            GNU_GPL3 = "\nLICENSE:\n\tThis program is free software; you can redistribute it and/or modify\n\tit under the terms of the GNU General Public License v3.0\n\tFor details see <www.gnu.org/licenses/gpl-3.0.html>.\n\tThis program is distributed in the hope that it will be useful,\n\tbut WITHOUT ANY WARRANTY; without even the implied warranty of\n\tMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n\tGNU General Public License for more details.\n\n"
            CAISO_TOU = "DATA:\n\tPricing data is property of the California Independent System Operator (CAISO)\n\tand governed by the CAISO Terms of Use, available at\n\t<www.caiso.com/Pages/PrivacyPolicy.aspx#TermsOfUse>\n\tAuthor(s) of this program disclaim ALL LIABILITY for use of this program. \n\tYou are responsible for ensuring that your usage of this program\n\tadheres to the CAISO Terms of Use and all applicable state and federal laws.\n\n"
            print(header+GNU_GPL3+CAISO_TOU+closer)
        else: print('FATAL ERROR: Input parameter not recognized.\nFor more info, run\n\tgetWholesaleCAISO.py -h \n\nx x\n >\n ⁔\n')
    # Catch more than 2 but stilltoo long 
    elif 4 > len(sys.argv): print('FATAL ERROR: Wrong number of parameters.\nFor more info, run\n\tgetWholesaleCAISO.py -h \n\nx x\n >\n ⁔\n')
    exit()

# Additional Options
# Defaults
debug = False
verbose = False
leap = False
safeguard = 2.5
# Detect any number of the optional inputs
i = 6
while i < len(sys.argv): 
    if sys.argv[i] == "-v": verbose = True
    elif sys.argv[i] == "-d": debug = True
    elif sys.argv[i] == "-leap": leap = True
    elif sys.argv[i] == "-s": safeguard = 10
    elif sys.argv[i] == "-fast": safeguard = 0.01
    else: print("Warning: optional input parameter not recognized; ignoring.")
    i += 1



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
    
# Function for figuring out what day is tomorrow ---
# Handles end of month, end of year, and leap year
def tmrw(y, m, d,leap):
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


# Handle Type of Data Request
if sys.argv[1] == 'd': #Day Ahead
    baseurl = 'http://www.caiso.com/Documents/Day-AheadDailyMarketWatch'
    filename = 'WholesaleDayAhead_'
    tshr = 12 #timesteps per hour
    keystart = "var lmp_pgae_ifm = [" # Search key in HTML
    keyend = "lmp_sce_ifm = ["
elif sys.argv[1]== 'r': # Real-Time, Fifteen Minute
    baseurl = 'http://www.caiso.com/Documents/Real-TimeDailyMarketWatch'
    filename = 'WholesaleRealTime_'
    tshr = 4 #Timesteps per hour
    keystart = "lmp_pgae_rtpd = [" #Search key
    keyend = "lmp_sce_rtpd = ["
else:
    print('FATAL ERROR: Invalid type, check <data_type> string.\nFor more info, run\n\tgetWholesaleCAISO.py -h  \n\nx x\n >\n ⁔\n')
    exit()

if debug:
    print("Keys for finding correct data: ")
    print (keystart)
    print (keyend)
# Keep year as string
year = int(sys.argv[2])
yearstart = year # Yearstart doesn't get modified for filenaming only (year can change)

# Months - handle 'January', 'Jan', or '1'
# Constant arrays for month calendar parameters
monthlist = ['Jan','Feb','Mar','Apr','May','Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
try: 
    mi = int(sys.argv[3]) - 1
    if mi > 11: 
        print('FATAL ERROR: Unrecognized month.\nFor more info, run\n\tgetWholesaleCAISO.py -h  \n\nx x\n >\n ⁔\n')
        exit()
    month = monthlist[mi]
except ValueError: 
    monin = sys.argv[3]
    month = monin[0:3]
    if month in monthlist: mi = monthlist.index(month)
    else: 
        print('FATAL ERROR: Unrecognized month.\nFor more info, run\n\tgetWholesaleCAISO.py -h  \n\nx x\n >\n ⁔\n')
        exit()
monthstart = mi+1 #only for filenaming

# Get Day info to int
try: day = int(sys.argv[4])
except ValueError: 
    print('FATAL ERROR: Invalid day, must be integer.\nFor more info, run\n\tgetWholesaleCAISO.py -h  \n\nx x\n >\n ⁔\n')
    exit()

# d gets modified; day is constant
d = day
daystr = str(dig2(day))

# Number of days
try: nd = int(sys.argv[5])
except ValueError: 
    print('FATAL ERROR: Invalid number of days, must be integer.\nFor more info, run\n\tgetWholesaleCAISO.py -h  \n\nx x\n >\n ⁔\n')
    exit()

# Print Verbose Header
if verbose:
    print(header)
    print('Getting ' + filename + 'data for ' + str(nd) + ' days, starting ' + month + ' ' + str(day) + ', ' + str(year) )


# Get Data from CAISO ==================================================
# Initialize Wholesale Price array
wsprice = np.array([])

# Repeat for the number of days specified ------------------------------
for cd in range(day,day+nd):
    # Previous for filenaming trick
    prevdate = datestr(year,mi+1,d,'-')
    
    month = monthlist[mi] #Name of mon, 3 letter string
    daystr = dig2(d) # 2 digit string
    
    # The URL for the CAISO data, created based on date info -------
    url = baseurl + month + daystr + '-' + str(year) +'.html'
    
    # Get html from CAISO webpage ----------------------------------
    http = urllib3.PoolManager()
    
    if verbose: print("\nGetting URL:   " + url)
    #Server request delay safeguard to avoid crashing server or getting banned. If safeguard is off, sleeps for 0
    time.sleep(safeguard)
    
    caisodat = requests.get(url)
    
    # Processing webdata to get values needed ---------------------
    # Convert html to a single usable string
    sdat = BeautifulSoup.BeautifulSoup(caisodat.content, 'lxml')

    caisohtml = sdat.prettify()
    
    if debug:
        print(type(caisohtml))
        print(len(caisohtml))
    
    # find index of keylines labeling the array in html we want
    dstart = caisohtml.find(keystart)
    # find index of keylines that are the next variable we don't want
    dend = caisohtml.find(keyend)
    # price data string with only the data for the price we want
    pdatstr = caisohtml[dstart:dend]
    if debug: 
        print("Start & End Indices")
        print(dstart)
        print(dend)
        print("Initial String of Price Values")
        print(pdatstr)  
    
    # Remove extra bracket at the end (already has a comma, keep that)
    pdatstr = pdatstr.replace("]","")
    if debug:
        print("Removed bracket ]")
        print(pdatstr)
    
    # Initially still has starting variable name; remove it
    pdatstr = pdatstr.replace(keystart,"")
    if debug:
        print("Removed \'" + keystart + "\'")
        print(pdatstr)
        print(type(pdatstr))
    
    # Remove any bad values
    pdatstr = pdatstr.replace("\"NA\",","")
    
    # Create numpy array from the string that looks like '12.3, 45.6, 78.9, ...'
    npd = np.fromstring(pdatstr, sep=",", dtype=float)
    if verbose:
        print("Data Array for " + month + ' ' + daystr + ', ' + str(year) + ': ')
        print(npd)
    
    try: # Add the data from this iteration to any existing data ----
        wsprice = np.append(wsprice,npd)
    except TypeError: 
        wsprice = npd #crude way to handle first time pricedat is empty so can't concatenate empty
    
    if debug: 
        print(wsprice)
        n = len(npd)
        if n > 24*tshr: #ignore if only off by one - seems to work anyway
            print("Warning: Too many data points found! Expected: " + str(24*tshr) + "   Got: " + str(n)+"\n" )
        if n < 24*tshr:
            print("Warning: Too few data points found! Expected: " + str(24*tshr) + "   Got: " + str(n)+"\n" )
    
    # Determine day & month or year incrementing
    year, mi, d = tmrw(year,mi,d,leap)
    
# End repeated code. All days are complete here ------------------------

# Final processing. wsprice is array with all the values ===============
#Remove garbage values (usually -1). Len(wsprice) may change.
wsprice = wsprice[wsprice>=0]

n = len(wsprice)

if debug:
    print("\nEntire Price Dataset: ")
    print(wsprice)
    print("\n\nTotal " + str(n) + " values, expect " + str(nd * 24 * tshr) + "\n")

# Convert long row of data to long column & get 5 min timesteps---------
# Numpy array in columns instead of rows
newprc = np.zeros((int(n*12/tshr),1))

# Repeat the same value 12/tshr times for 5 min timesteps.
# Note: Assumes that 12/tshr is an integer; ie tshr is an integer multiple of 5. Other input timesteps not supported.
if int(12/tshr) != 12/tshr: print("\nWARNING: Timestep of input data is not evenly divisible by 5 min output timesteps. \n")
for i in range (0,n):
    for j in range (0,int(12/tshr)):
        newprc[int(i*12/tshr+j),0] = wsprice[i]

if debug: 
    print(newprc) # Sanity check before writing
    print("\n\nTotal " + str(len(newprc)) + " values, expect " + str(nd * 24 * 12) + "\n")

# Write File with Data =================================================
# Filename in form of example: WholesaleDayAhead_2020-08-03_2020-08-10.csv
outfile = filename + datestr(yearstart,monthstart,day,'-') + "_" + prevdate + '.csv'
np.savetxt(outfile, newprc[:,0], delimiter=',')

if verbose: # Show final result ----------------------------------------
    print('\n COMPLETED - SUCCESS! \n File is saved as: ' + outfile)
    print('================================================\n')
else: print('\n COMPLETE! File is saved as: ' + outfile)
