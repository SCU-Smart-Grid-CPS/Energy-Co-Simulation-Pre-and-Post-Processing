#  eppp.py    Identical to epPostProcess.py, with shorter name that is easier to type
#  
#  Author(s):   Brian Woo-Shem, Kaleb Pattawi
#  Updated:     2021-08-04
#  Version:     2.0
#  
#  Instructions:
#   - Prerequisite libraries os, ipypublish, pandas, numpy
#   - Set analysis parameters in terminal OR by changing values in code below, marked by ===> <===
#
# Run As:
#           python3 eppp.py < parameters >
#
# < Parameters > can go in any order!
#   inputfilename.csv  OR  input=inputfilename.csv  Any number of source EP data files to analyze
#   output=[outputfilename].csv   File to output results to. Note output=none means no output file
#   graph=detail  Extra detail graph (not yet implemented, does nothing)
#   graph=none    Suppress graphs
#   -v            Verbose. Additional dataframe outputs to terminal
#   days <startday> <endday>  Three inputs separated by space; startday and endday must be integers
#   wholesale=l  or legacy       Accepts older price csv files from before getWholesaleCAISO. Default is style from getWholesaleCAISO
#   wholesale=d   Day-ahead
#   wholesale=r   Real-time. Default setting.
#   date=[date_range]     Set date range to get data for
#   -c=filename   Outputs comfort data file as "original_file_filename.csv"
#   -c=none       Do not output comfort data file
#   ts=         Number of timesteps per hour
#   calibration=  Number of EP calibration rows

#Import Scientific and numerical computing libraries --------------------
import os
import sys
from ipypublish import nb_setup
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv

# Suppress annoying warning
pd.set_option('mode.chained_assignment', None)

# Adds the .csv file extension if it is not already present to a string representing the output file name
def addFileType(c):
    if c[len(c)-4: len(c)] != ".csv": c = c + ".csv"
    return c

# UI
header = '\n=================== epPostProcess.py V2.0 ==================='
closer = '===========================================================\n'
print(header)

# Preset Values & Indices -----------------------------------------------
# Values that can be designated here, or using command-line input. 
# Command line input supercedes anything here.

# < input= > ===> File Name(s) of Energy Plus result csv file(s) <=== 
# List all of them here, separated by commas, eg. ["file1.csv", "file2.csv"]
files = ["Demo_EP_Data.csv"]

# < date= > ===> WHEN TO RUN - must match EP run period! <===
# Legacy Options: 
#   'Jan1thru7'
#   'Feb12thru19'
#   'Sept27-Oct3_SJ'
date_range = '2020-6-29_2020-7-05'

# < output= > ===> Default output csv file <===
# Calling it "None" or "none" will make it not make this file
outFile = "epPostProcessOutput.csv"

# < days first last > ===> Start & End Day <=== 
firstDay = 0  # 0 to 6
lastDay = 7  # 1 to 7

# < graph= > ===> Graph Settings <===
# Display graph?
graph = True
# Show more detailed graph? - currently does nothing
detailGraph = False

# < wholesale= > ===> Wholesale Data Type <===
#   r = Real-Time
#   d = Day-Ahead
#   l = legacy = Older data, before GetWholesaleCAISO
wholesaleType = 'r'

# < -c= > ===> Output Comfort Data <===
# What name to add to the input file to designate the comfort data file as "InputFile_filename.csv"
# Calling it "None" or "none" will make it output nothing
comfortSuffix = "comfort.csv"

# < -v > ===> Verbose - Show detailed outputs to command line <===
verbose = False

# < ts= > ===> Timestep Length [min] <===
timestep = 5 # minutes

# < calibration= > ===> Set working data range <=== 
# How many rows of calibration data at beginning of file
# Changes based on variables you are outputting, for default simulation use 2305-1
numEPlusCalibrationRows = 2305 - 1  # -1 because first row is column headers

# Constants & Indices that should not be changed
ns = len(sys.argv)
i = 1
nf = 0

# Get parameter inputs from command line --------------------------------
while i < ns:
    if "output=" in sys.argv[i]: #must go before filenames because will include .csv in string
        outFile = addFileType(sys.argv[i].replace("output=",""))
    elif ".csv" in sys.argv[i] or "data=" in sys.argv[i] or "input=" in sys.argv[i]: # Number of files. First one replaces the default file
        if nf==0: files= [addFileType(sys.argv[i].replace("data=","").replace("input=",""))]
        else: files.append(addFileType(sys.argv[i].replace("data=","").replace("input=",""))) # after that it adds more files to the list
        nf += 1
    elif "date=" in sys.argv[i]:
        date_range = sys.argv[i].replace("date=","")
    elif "days" in sys.argv[i]:
        i += 1
        try: firstDay = int(sys.argv[i])
        except ValueError:
            print('Warning: Invalid start day, using default = 0 instead.')
            i -= 1
        except IndexError:
            print('Warning: Missing start day, using default = 0 instead.')
            i -= 1
        i += 1
        try: lastDay = int(sys.argv[i])
        except ValueError:
            print('Warning: Invalid end day, using default = 7 instead.')
            i -= 1
        except IndexError:
            print('Warning: Missing end day, using default = 7 instead.')
            i -= 1
    elif "graph=" in sys.argv[i]:
        if "detail" in sys.argv[i]: detailGraph = True
        elif "none" in sys.argv[i]: graph = False
        else: print('Warning: invalid graph type, using default graph configuration instead.')
    elif "-v" in sys.argv[i]: verbose = True
    elif "wholesale" in sys.argv[i]:
        if "d" in sys.argv[i]: wholesaleType = 'd'
        elif "r" in sys.argv[i]: wholesaleType = 'r'
        elif "l" in sys.argv[i]: wholesaleType = 'l'
        else: print('Warning: invalid wholesale price type, using default, ', wholesaleType, ' instead.')
    elif "-c=" in sys.argv[i]:
        comfortSuffix = addFileType(sys.argv[i].replace("-c=",""))
    elif "calibration" in sys.argv[i]:
        try: numEPlusCalibrationRows = int(sys.argv[i].replace("calibration=",""))
        except ValueError: print('Warning: invalid calibration rows, using default =', str(numEPlusCalibrationRows))
    elif "ts" in sys.argv[i]:
        try: numEPlusCalibrationRows = int(sys.argv[i].replace("ts=",""))
        except ValueError: print('Warning: invalid timestep, using default =', str(timestep))
    else: print('Warning: Unrecognized parameter. Using defaults instead.')
    i += 1

# UI
if nf == 0: print('FYI: Using preset input data files from code.')
print("Processing Files: ")
print(files)

# Data range to plot
#datarows = 2016 # number of rows with data [0:2040]
dayrows = int(60 / timestep * 24) #Usually = 288 = int(datarows/7) = number of rows with data per day = timestepsperhour * 24
# Set bounds to plot. Integer to multiply is the day number, must be on bounds (typically 0 - 7)
startplot = int(firstDay * dayrows)
endplot = int(lastDay * dayrows)
print(startplot)
print(endplot)

# Constants & Indices ----------------------------------------------------
# Constant for energy
convTokWh = 2.77778e-7

# Index
i = 0
# Initialize empty lists for data so it doesn't overwrite or get indexing errors later
labels = []*len(files)
totHeatElec = [0]*len(files)
totCoolElec = [0]*len(files)
meanDiff100 = [0]*len(files)
meanComfBand = [0]*len(files)
totalPrice = [0]*len(files)
pctTimeComf90 = [0]*len(files)
pctTimeComf80 = [0]*len(files)
linestyles = ['-','--','-.','-','--','-.','-','--','-.','-','--','-.']

# Get unified time and indoor temp --------------------------------------
data = pd.read_csv(files[i])
# remove the energyplus calibration part 
data = data[numEPlusCalibrationRows:]
# Global outdoor temperature
outdoorTemp = data['Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)']
# Total data time
time = np.linspace(0,24*7,len(outdoorTemp))

    
# Get pricing data -------------------------------------------------------
# Below we get the wholesale price and convert to price for the users using a simple equation (the way we determine the users price will likely change in the future). Then we can determine the total cost over the whole simulation. Similar we can print out the total heating/cooling energy over the simulation.
if 'l' in wholesaleType:
    wholesale = pd.read_excel('WholesalePrice.xlsx', sheet_name=date_range)
    price = wholesale.apply(lambda x: 4*x/1000 + 0.1)
    try: price.columns = ['Price [$/MWh]']
    except ValueError: price.columns = ['Price [$/MWh]', "col2", "col3"]
else: #For GetWholesaleCAISO data sets
    if wholesaleType == 'd':
        pfile = "WholesaleDayAhead_" + date_range + ".csv"
    elif wholesaleType == 'r':
        pfile = "WholesaleRealTime_" + date_range + ".csv"
    wholesale= np.genfromtxt(pfile, max_rows=len(data), delimiter=',')
    

# Get generated occupancy data -------------------------------------------
occupancy_data = pd.read_csv('occupancy_5min.csv', nrows=(len(data)))

# Getting data from EP files ---------------------------------------------
# Iterate through files, obtain and compute comfort data
for f in files:
    # Read EP file data ----------------------------------------
    try: data = pd.read_csv(f)
    except FileNotFoundError:
        print("Input file ", f, " does not exist, skipping.")
        continue
    print("-------------------------------------------------\n\nDataset: " + f)
    # remove the EnergyPlus calibration part 
    data = data[numEPlusCalibrationRows:]
    # set index
    newIndex = np.array(range(0,len(data['Date/Time'])))
    data = data.set_index(newIndex)

    # Indoor temperature for current simulation
    indoorTemp = data['LIVING_UNIT1:Zone Air Temperature [C](TimeStep)']
    
    
    # Cost, energy consumption, and thermal comfort ---------------------------
    # determine price using total electricity times price of energy
    if 'l' in wholesaleType: # Legacy - older files
        pricePaid = price['Price [$/MWh]'].loc[0:len(data)-1]*data['Electricity:Facility [J](TimeStep)']*2.77778e-7
        totalPrice[i] = pricePaid.sum()
    else: # New getWholesaleCAISO files
        for w in range(0,len(data)):
            priceStep = (wholesale[w]*4/1000 + 0.1)*data['Electricity:Facility [J](TimeStep)'].iloc[w]*2.77778e-7
            totalPrice[i] = totalPrice[i]+priceStep
    print("total cost:",totalPrice[i])

    # total energy over whole simulation ------------------------------------------
    elec_kwh = pd.DataFrame(columns=["Heating Electricity [kWh]", "Cooling Electricity [kWh]"])
    elec_kwh["Heating Electricity [kWh]"] = data['Heating:Electricity [J](TimeStep)']*convTokWh
    totHeatElec[i] = elec_kwh["Heating Electricity [kWh]"].sum()
    print("total heating electricity [kWh]:",totHeatElec[i])
    
    elec_kwh["Cooling Electricity [kWh]"] = data['Cooling:Electricity [J](TimeStep)']*convTokWh
    totCoolElec[i] =elec_kwh["Cooling Electricity [kWh]"].sum()
    print("total cooling electricity [kWh]:",totCoolElec[i])

    # thermal comfort -----------------------------------------------------------
    # Compute 100% comfort bounds
    temp_100comfort_heating = outdoorTemp.apply(lambda x: 0.31*x + 16.3)
    temp_100comfort_cooling = outdoorTemp.apply(lambda x: 0.31*x + 19.3)
    
    HEAT_TEMP_MAX_100 = 25.7
    HEAT_TEMP_MIN_100 = 18.4
    COOL_TEMP_MAX_100 = 29.7
    COOL_TEMP_MIN_100 = 22.4
    
    # When temps too low or too high set to min or max (See adaptive 100)
    temp_100comfort_cooling.loc[(temp_100comfort_cooling < COOL_TEMP_MIN_100)] = COOL_TEMP_MIN_100
    temp_100comfort_cooling.loc[(temp_100comfort_cooling > COOL_TEMP_MAX_100)] = COOL_TEMP_MAX_100
    temp_100comfort_heating.loc[(temp_100comfort_heating < HEAT_TEMP_MIN_100)] = HEAT_TEMP_MIN_100
    temp_100comfort_heating.loc[(temp_100comfort_heating > HEAT_TEMP_MAX_100)] = HEAT_TEMP_MAX_100
    # temperature difference from indoor to 100% comfortable:
    delta_temp = pd.DataFrame(columns=["heating", "cooling"])
    delta_temp["heating"] = temp_100comfort_heating - indoorTemp
    delta_temp["cooling"] = indoorTemp - temp_100comfort_cooling
    delta_temp["heating"].iloc[delta_temp["heating"] < 0] = 0
    delta_temp["cooling"].iloc[delta_temp["cooling"] < 0] = 0
    delta_temp["maximum"] = delta_temp[["heating", "cooling"]].max(axis=1)

    # Convert temperature difference into percent of comfortable occupants:
    from scipy.stats import norm
    delta_temp["percent-comfortable"] = delta_temp["maximum"].apply(lambda x: 100*(2 - 2*norm.cdf(x/3.937)))
    if verbose:
        print("Percent Comfortable Occupants Dataframe")
        print(delta_temp.head(24))
    meanDiff100[i] = delta_temp["maximum"].mean()
    print("\nMean temperature difference from 100% comfortable temperature:", meanDiff100[i])
    meanComfBand[i] = delta_temp["percent-comfortable"].mean()
    print("Mean comfort band percent:", meanComfBand[i])


    # Determine percentage of time that indoor temp is within 90% range ----------
    comfort = pd.DataFrame(columns=['indoor','outdoor','occupancy'])
    comfort['indoor'] = indoorTemp
    comfort['outdoor'] = outdoorTemp
    comfort['occupancy'] = occupancy_data
    comfort['comfort90_min'] = outdoorTemp.apply(lambda x: 0.31*x + 15.8)
    comfort['comfort90_max'] = outdoorTemp.apply(lambda x: 0.31*x + 19.8)
    
    # Max and min for heating and cooling in adaptive setpoint control for 90% of people [°C]
    HEAT_TEMP_MAX_90 = 26.2
    HEAT_TEMP_MIN_90 = 18.9
    COOL_TEMP_MAX_90 = 30.2
    COOL_TEMP_MIN_90 = 22.9
    
    # When temps too low or too high set to min or max (See adaptive setpoints)
    comfort.loc[(comfort['comfort90_max'] < COOL_TEMP_MIN_90, 'comfort90_max')] = COOL_TEMP_MIN_90
    comfort.loc[(comfort['comfort90_max'] > COOL_TEMP_MAX_90, 'comfort90_max')] = COOL_TEMP_MAX_90
    comfort.loc[(comfort['comfort90_min'] < HEAT_TEMP_MIN_90, 'comfort90_min')] = HEAT_TEMP_MIN_90
    comfort.loc[(comfort['comfort90_min'] > HEAT_TEMP_MAX_90, 'comfort90_min')] = HEAT_TEMP_MAX_90

    comfort['is90'] = comfort['indoor']   # makes new column in dataframe; will be overwritten
    # Determine if temp is within 90% comfort bounds
    comfort['is90'].loc[(comfort['indoor'] > comfort['comfort90_min']) & (comfort['indoor'] < comfort['comfort90_max'])] = 1
    comfort['is90'].loc[(comfort['indoor'] < comfort['comfort90_min']) | (comfort['indoor'] > comfort['comfort90_max'])] = 0
    # Is it both comfortable and occupied? 'is90' and 'occupancy' are both arrays with values of 1 or 0. Multiplying results
    # in 1 if both are true, and 0 otherwise
    comfort['comf_occ_90'] = comfort['is90']*comfort['occupancy']
    # Compare what percent of the time it is comfortable when occupied with the total occupied time
    pctTimeComf90[i] = 100*comfort['comf_occ_90'].sum()/comfort['occupancy'].sum()
    print(comfort['comf_occ_90'].sum())
    print(comfort['occupancy'].sum())
    print('Percent of occupied time indoor temperature is within 90% comfortable:', pctTimeComf90[i])
    
    # 80% range ---------------------------------------------------------------
    pb = 0.80 # 80%
    sigma = 3.937 # This was calculated based on adaptive comfort being normally distributed
    # Comfort range at probability pb
    cr = norm.ppf(((1-pb)/2)+1/2)*sigma
    comfort['is80'] = comfort['indoor'] #create arbitrary column in df
    #100% setpoint band + expanded amount allowed by comfort range
    comfort['comfort80_min'] = outdoorTemp.apply(lambda x: x*0.31 + 16.3 - cr)
    comfort['comfort80_max'] = outdoorTemp.apply(lambda x: x*0.31 + 19.3 + cr)
    
    # When temps too low or too high set to min or max (See adaptive 100)
    comfort.loc[(comfort['comfort80_max'] < COOL_TEMP_MIN_100+cr), 'comfort80_max'] = COOL_TEMP_MIN_100+cr
    comfort.loc[(comfort['comfort80_max'] > COOL_TEMP_MAX_100+cr), 'comfort80_max'] = COOL_TEMP_MAX_100+cr
    comfort.loc[(comfort['comfort80_min'] < HEAT_TEMP_MIN_100-cr), 'comfort80_min'] = HEAT_TEMP_MIN_100-cr
    comfort.loc[(comfort['comfort80_min'] > HEAT_TEMP_MAX_100-cr), 'comfort80_min'] = HEAT_TEMP_MAX_100-cr
    
    # Is it comfortable for 80%?
    comfort['is80'].loc[(comfort['indoor'] > comfort['comfort80_min']) & (comfort['indoor'] < comfort['comfort80_max'])] = 1
    comfort['is80'].loc[(comfort['indoor'] < comfort['comfort80_min']) | (comfort['indoor'] > comfort['comfort80_max'])] = 0
    # Multiply by occupancy status at that time. Both are either 0 or 1, so result is 0 or 1
    comfort['comf_occ80'] = comfort['is80']*comfort['occupancy']
    pctTimeComf80[i] = 100*comfort['comf_occ80'].sum()/comfort['occupancy'].sum()
    print('Percent of occupied time indoor temperature is within 80% comfortable:', pctTimeComf80[i])
    
    if verbose: #Optional output of the first few lines of the data table
        print("Percent of Occupied Time that is Comfortable Dataframe")
        print(comfort.head(20))

    # Output detailed comfort data csv ----------------------------------------
    if "None" not in comfortSuffix and "none" not in comfortSuffix: 
        # Add max and min setpoints, heating and cooling energy to the comfort dataframe
        comfort['Max_Setpt'] = data['LIVING_UNIT1:Zone Thermostat Cooling Setpoint Temperature [C](TimeStep)']
        comfort['Min_Setpt'] = data['LIVING_UNIT1:Zone Thermostat Heating Setpoint Temperature [C](TimeStep)']
        comfort["Cooling Electricity [kWh]"] = elec_kwh["Cooling Electricity [kWh]"]
        comfort["Heating Electricity [kWh]"] = elec_kwh["Heating Electricity [kWh]"]
        if 'l' not in wholesaleType: # Clunky method but works
            ecost = pd.DataFrame(wholesale, columns=['Electricity Price [$/kWh]'])
            comfort['Electric Price [$/kWh]'] = ecost.apply(lambda x: 4*x/1000 + 0.1)
        else:
            comfort['Electric Price [$/kWh]'] = price['Price [$/MWh]']
        # Create and export comfort data
        comfortFile = f.replace(".csv" , "") + "_" + comfortSuffix
        comfort.to_csv(comfortFile, header=True)
        print("\nComfort Data Exported to: ", comfortFile)

    # Plot indoor temp, outdoor temp, and heating/cooling setpoint -------------
    if graph:
        heatTemp = data['LIVING_UNIT1:Zone Thermostat Heating Setpoint Temperature [C](TimeStep)']
        coolTemp = data['LIVING_UNIT1:Zone Thermostat Cooling Setpoint Temperature [C](TimeStep)']

        plt.plot(time[startplot:endplot],indoorTemp[startplot:endplot], label=f, linestyle=linestyles[i])
        
        # show heating and cooling setpoints if only plotting one simulation.
        if len(files)==1:
            if totHeatElec[i] > 1:
                plt.plot(time[startplot:endplot], heatTemp[startplot:endplot], label="Heating Setpoint", linestyle='--')
            if totCoolElec[i] > 1:
                plt.plot(time[startplot:endplot], coolTemp[startplot:endplot], label="Cooling Setpoint", linestyle='-.')
    
    i += 1
# END For each file loop -----------------------------------------------

if graph: # Final graph display to do one time. --------------------------
    # Plot outdoor temp
    plt.plot(time[startplot:endplot], outdoorTemp[startplot:endplot], label="Outdoor", linestyle=':')
    # Readability
    plt.legend()
    plt.xlabel('Time [hours]')
    plt.ylabel('Temperature [° C]')
    plt.xlim([time[startplot],time[endplot-1]])
    plt.grid()
    plt.show()

# Output results to csv file -----------------------------------------------
if "None" not in outFile and "none" not in outFile:
    # Add title/label rows
    files.insert(0,"")
    totalPrice.insert(0,"Total Electricity Price [$]")
    totHeatElec.insert(0,"Total Heating Electricity [kWh]")
    totCoolElec.insert(0,"Total Cooling Electricity [kWh]")
    meanDiff100.insert(0,"Mean Temp Diff from 100% Comfortable [°C]")
    meanComfBand.insert(0,"Mean Comfort Band Percent [%]")
    pctTimeComf90.insert(0,"Percent of occupied time within 90% comfort band [%]")
    pctTimeComf80.insert(0,"Percent of occupied time within 80% comfort band [%]")
    # Put all 1D lists into a single 2D list to write
    rows = [files,totalPrice,totHeatElec,totCoolElec,meanDiff100,meanComfBand,pctTimeComf90,pctTimeComf80]
    # Write file using csvwrite
    with open(outFile,"w") as out:
        writer = csv.writer(out)
        for r in rows:
            writer.writerow(r)
    print("--------------------------------------------------\n")
    print("Data successfully written to file as: " + outFile)

print(closer)
