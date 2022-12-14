#  eppp.py    Identical to epPostProcess.py, with shorter name that is easier to type
#  
#  Author(s):   Brian Woo-Shem, Kaleb Pattawi
#  Updated:     2022-05-23
#  Version:     3.0 (Add occupancy comfort bounds generator, Full support for limited range of days)
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
#
#   graph=detail  Extra detail graph (not yet implemented, does nothing)
#   graph=none    Suppress graphs
#
#   -v            Verbose. Additional dataframe outputs to terminal
#
#   days <startday> <endday>  Three inputs separated by space; startday and endday must be integers
#                               this is the range of days to process days for
#
#   pconst <a> <b>  Three inputs separated by space; a = pricing multiplier, b = pricing offset
#                               both can be floating point values.
#
#   price=l  or legacy       Accepts older price csv files from before getWholesaleCAISO. Default is style from getWholesaleCAISO
#   price=d   Day-ahead
#   price=r   Real-time. Default setting.
#
#   date=[date_range]     Set date range to get data for
#
#   -c=filename   Outputs comfort data file as "original_file_filename.csv"
#   -c=none       Do not output comfort data file
#
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
from scipy.stats import norm

# Suppress annoying warning
pd.set_option('mode.chained_assignment', None)

# Adds the .csv file extension if it is not already present to a string representing the output file name
def addFileType(c):
    if c[len(c)-4: len(c)] != ".csv": c = c + ".csv"
    return c

# UI
header = '\n=================== epPostProcess.py V3.0 ==================='
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
date_range = '2020-08-01_2020-08-31'

# < output= > ===> Default output csv file <===
# Calling it "None" or "none" will make it not make this file
outFile = "_summary.csv"

# < days first last > ===> Start & End Day <=== 
firstDay = 0  # 0 to 6
lastDay = 7  # 1 to 7

# < graph= > ===> Graph Settings <===
# Display graph?
graph = True
# Show more detailed graph? - currently does nothing
graphType = "normal"

# < wholesale= > ===> Wholesale Data Type <===
#   r = Real-Time
#   d = Day-Ahead
#   l = legacy = Older data, before GetWholesaleCAISO
priceType = 'r'

# < -c= > ===> Output Comfort Data <===
# What name to add to the input file to designate the comfort data file as "InputFile_filename.csv"
# Calling it "None" or "none" will make it output nothing
comfortSuffix = "comfort.csv"
pmultiplier = 8
poffset = 0.015

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
    elif "-c=" in sys.argv[i]:
        comfortSuffix = addFileType(sys.argv[i].replace("-c=",""))
    elif ".csv" in sys.argv[i] or "data=" in sys.argv[i] or "input=" in sys.argv[i]: # Number of files. First one replaces the default file
        if nf==0: files= [addFileType(sys.argv[i].replace("data=","").replace("input=",""))]
        else: files.append(addFileType(sys.argv[i].replace("data=","").replace("input=",""))) # after that it adds more files to the list
        nf += 1
    elif "date=" in sys.argv[i]:
        date_range = sys.argv[i].replace("date=","")
    elif "pconst" in sys.argv[i]:
        i += 1
        try: pmultiplier = float(sys.argv[i])
        except ValueError:
            print('Warning: Invalid price multiplier, using default = 4 instead.')
            i -= 1
        except IndexError:
            print('Warning: Missing price multiplier, using default = 4 instead.')
            i -= 1
        i += 1
        try: 
            poffset = float(sys.argv[i])
        except ValueError:
            print('Warning: Invalid price offset, using default = 0.10 instead.')
            i -= 1
        except IndexError:
            print('Warning: Missing price offset, using default = 0.10 instead.')
            i -= 1
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
        if "detail" in sys.argv[i]: graphType = "detail"
        elif "cool" in sys.argv[i]: graphType = "coolSetpoints"
        elif "heat" in sys.argv[i]: graphType = "heatSetpoints"
        elif "none" in sys.argv[i]: graph = False
        else: print('Warning: invalid graph type, using default graph configuration instead.')
    elif "-v" in sys.argv[i]: verbose = True
    elif "price" in sys.argv[i]:
        if "=d" in sys.argv[i]: priceType = 'd'
        elif "=r" in sys.argv[i]: priceType = 'r'
        elif "E-1" in sys.argv[i]: priceType = 'E-1'
        elif "E-TOU-C_S" in sys.argv[i]: priceType = 'E-TOU-C_Summer'
        elif "E-TOU-C_W" in sys.argv[i]: priceType = 'E-TOU-C_Winter'
        elif "E-TD-Z" in sys.argv[i]: priceType = 'E-TD-Z'
        elif "=l" in sys.argv[i]: priceType = 'l'
        else: print('Warning: invalid wholesale price type, using default, ', priceType, ' instead.')
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
datastart = int(firstDay * dayrows)
dataend = int(lastDay * dayrows) - 1
if verbose:
    print("datastart = ", datastart)
    print("dataend = ", dataend)

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
avgDailyEnergy = [0]*len(files)
avgDailyCost = [0]*len(files)
heatPrice = [0]*len(files)
coolPrice = [0]*len(files)
linestyles = ['-','--','-.','-','--','-.','-','--','-.','-','--','-.']

# Get unified time and indoor temp --------------------------------------
data = pd.read_csv(files[i])
# remove the energyplus calibration part 
data = data[numEPlusCalibrationRows:]
#data = data[datastart:dataend]
#print(len(data))
#newIndex = np.array(range(0,dataend-datastart))
newIndex = np.array(range(0,len(data['Date/Time'])))
data = data.set_index(newIndex)
if verbose:
    print("Source Data Matrix: ")
    print(data.head())
# Global outdoor temperature
outdoorTemp = data['Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)']
# Total data time
time = np.linspace(0,24*(lastDay-firstDay),len(data['Date/Time']))


# Get generated occupancy data -------------------------------------------
occupancy_data = pd.read_csv('occupancy_5min.csv', nrows=(dataend))

# Occupancy
occupancy_df = pd.read_csv('occupancy_1hr.csv', nrows=int(24*(lastDay-firstDay)+2))
occupancy_df = occupancy_df.set_index('Dates/Times')
occupancy_df.index = pd.to_datetime(occupancy_df.index)

# hourly occupancy probability data to 5 minute intervals
occ_prob_all = occupancy_df.Probability.resample('5min').interpolate(method='linear')
#print(occ_prob_all)

# Compute thermal comfort bounds based on outdoor temp -------------------
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

occsetptout = True

if occsetptout:
    # Determine Occupancy Adaptive Comfort Bounds -------------------------------------
    occsetpt = pd.DataFrame(columns=['outdoor','occ_status','occ_prob','occ_prob_comfort_range'])
    occsetpt['outdoor'] = outdoorTemp.copy()
    occsetpt['occ_status'] = occupancy_data.copy()
    #experimenting
    #occsetpt['occ_prob'] = outdoorTemp.copy()
    #print(occ_prob_all[0:len(outdoorTemp)])
    test = pd.DataFrame(columns=['occ_prob'])
    test['occ_prob'] = occ_prob_all[0:len(outdoorTemp)].copy()
    #print(test) #test works
    #Not sure why this one doesn't work and occ_prob ends up blank
    occsetpt['occ_prob'] = test['occ_prob'].copy() #occ_prob_all[0:len(outdoorTemp)].copy()

    pb = 0.90 # 90%
    sigma = 3.937 # This was calculated based on adaptive comfort being normally distributed
    # Comfort range at probability pb
    cr = norm.ppf(((1-pb)/2)+1/2)*sigma
    print("Comf range expansion: ", cr)

    #Apply comfort bound function - requires using dataframe to do the lambda
    op_comfort_range = occ_prob_all.iloc[:len(outdoorTemp)].apply(lambda x: (1-x)/2)+1/2
    op_comfort_range = np.array(op_comfort_range.apply(lambda y: norm.ppf(y)*sigma))
    occsetpt['occ_prob_comfort_range'] = op_comfort_range

    occsetpt['occ_prob_heat'] = temp_100comfort_heating-op_comfort_range
    occsetpt['occ_prob_cool'] = temp_100comfort_cooling+op_comfort_range

    occsetpt['occ_heat'] = occsetpt['occ_prob_heat']
    occsetpt['occ_cool'] = occsetpt['occ_prob_cool']

    # If occupied, use 90% comfort band
    occsetpt['occ_heat'].loc[(occsetpt['occ_status'] == 1)] = temp_100comfort_heating.loc[(occsetpt['occ_status'] == 1)] - cr
    occsetpt['occ_cool'].loc[(occsetpt['occ_status'] == 1)] = temp_100comfort_cooling.loc[(occsetpt['occ_status'] == 1)] + cr
    
    print("Computed occupancy-based adaptive setpoints:")
    print(occsetpt)

    # Export to file
    occsetptFile = 'OccupancySetpoints_' + date_range + '.csv'
    occsetpt.to_csv(occsetptFile, header=True)
    print("\nOccupancy Setpoints Exported to: ", occsetptFile)



# Get pricing data -------------------------------------------------------
# Below we get the wholesale price and convert to price for the users using a simple equation (the way we determine the users price will likely change in the future). Then we can determine the total cost over the whole simulation. Similar we can print out the total heating/cooling energy over the simulation.
if 'l' in priceType:
    wholesale = pd.read_excel('WholesalePrice.xlsx', sheet_name=date_range)
    price = wholesale.apply(lambda x: 4*x/1000 + 0.1)
    try: price.columns = ['Price [$/MWh]']
    except ValueError: price.columns = ['Price [$/MWh]', "col2", "col3"]

# Matches existing PG&E Rates
elif 'E' in priceType:
    if 'E-1' in priceType: pfile = 'E-1_5min.csv'
    elif 'E-TOU-C_Summer' in priceType: pfile = 'E-TOU-C_5min_Summer.csv'
    elif 'E-TOU-C_Winter' in priceType: pfile = 'E-TOU-C_5min_Winter.csv'
    elif 'E-TD-Z' in priceType: pfile = 'E-TD-Z_5min.csv'
    else: #error
        pfile = 'Zero.csv'
    
    #Get data directly from file, no extra multiplier or offset
    eprice= np.genfromtxt(pfile, skip_header=0, max_rows=dataend+1, delimiter=',',usecols=0)

# Using Demand-based CAISO pricing
else:
    if 'd' in priceType.lower(): pfile = "WholesaleDayAhead_" + date_range + ".csv"
    elif 'r' in priceType.lower(): pfile = "WholesaleRealTime_" + date_range + ".csv"
    else: pfile = 'Zero.csv'
    # Get data, with offset and multiplier
    wholesale= np.genfromtxt(pfile, skip_header=0, max_rows=dataend+1, delimiter=',',usecols=0)
    eprice = wholesale*pmultiplier/1000+poffset


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
    #data = data[datastart:dataend]

    # set index
    newIndex = np.array(range(0,len(data['Date/Time'])))
    data = data.set_index(newIndex)

    # Indoor temperature for current simulation
    indoorTemp = data['LIVING_UNIT1:Zone Air Temperature [C](TimeStep)']
    #print(indoorTemp)
    
    
    # Cost, energy consumption, and thermal comfort ---------------------------
    # determine price using total electricity times price of energy
    if 'l' in priceType: # Legacy - older files
        pricePaid = price['Price [$/MWh]'].loc[0:len(data)-1]*data['Electricity:Facility [J](TimeStep)']*2.77778e-7
        totalPrice[i] = pricePaid.sum()
    else: # New getWholesaleCAISO files
        print(len(eprice))
        print(len(data))
        print(datastart)
        print(dataend)
        for w in range(datastart,dataend):
            #print(totalPrice[i])
            priceStep = eprice[w]*data['Electricity:Facility [J](TimeStep)'].iloc[w]*convTokWh
            totalPrice[i] = totalPrice[i]+priceStep
            # print(w)
            # print(i)
            # print(wholesale[w])
            # print(data['Electricity:Facility [J](TimeStep)'].iloc[w])
            # print(priceStep)
            heatPrice[i] = heatPrice[i] + eprice[w]*data['Heating:Electricity [J](TimeStep)'].iloc[w]*convTokWh
            coolPrice[i] = coolPrice[i] + eprice[w]*data['Cooling:Electricity [J](TimeStep)'].iloc[w]*convTokWh
    print("Total HVAC Electric Bill [$] = ",totalPrice[i])
    avgDailyCost[i] = totalPrice[i] / (lastDay - firstDay)

    # total energy over whole simulation ------------------------------------------
    elec_kwh = pd.DataFrame(columns=["Heating Electricity [kWh]", "Cooling Electricity [kWh]"])
    elec_kwh["Heating Electricity [kWh]"] = data['Heating:Electricity [J](TimeStep)']*convTokWh
    totHeatElec[i] = elec_kwh["Heating Electricity [kWh]"].iloc[datastart:dataend].sum()
    print("total heating electricity [kWh]:",totHeatElec[i])
    
    elec_kwh["Cooling Electricity [kWh]"] = data['Cooling:Electricity [J](TimeStep)']*convTokWh
    totCoolElec[i] =elec_kwh["Cooling Electricity [kWh]"].iloc[datastart:dataend].sum()
    print("total cooling electricity [kWh]:",totCoolElec[i])
    
    avgDailyEnergy[i] = (totHeatElec[i] + totCoolElec[i]) / (lastDay - firstDay)
    print("Average Daily HVAC Electricity [kWh] = ", avgDailyEnergy[i])

    # thermal comfort -----------------------------------------------------------
    
    
    #print(temp_100comfort_cooling)
    # temperature difference from indoor to 100% comfortable:
    delta_temp = pd.DataFrame(columns=["heating", "cooling"])
    delta_temp["heating"] = temp_100comfort_heating - indoorTemp
    delta_temp["cooling"] = indoorTemp - temp_100comfort_cooling
    
    #print(indoorTemp)
    #print(delta_temp)
    
    delta_temp["heating"].iloc[delta_temp["heating"] < 0] = 0
    delta_temp["cooling"].iloc[delta_temp["cooling"] < 0] = 0
    delta_temp["maximum"] = delta_temp[["heating", "cooling"]].max(axis=1)

    # Convert temperature difference into percent of comfortable occupants:
    from scipy.stats import norm
    delta_temp["percent-comfortable"] = delta_temp["maximum"].apply(lambda x: 100*(2 - 2*norm.cdf(x/3.937)))
    if verbose:
        print("Percent Comfortable Regardless of Occupancy Dataframe")
        print(delta_temp.head(24))
    meanDiff100[i] = delta_temp["maximum"].iloc[datastart:dataend].mean()
    print("\nMean temperature difference from 100% comfortable temperature:", meanDiff100[i])
    meanComfBand[i] = delta_temp["percent-comfortable"].iloc[datastart:dataend].mean()
    print("Mean comfort band percent:", meanComfBand[i])


    # Determine percentage of time that indoor temp is within 90% range ----------
    comfort = pd.DataFrame(columns=['indoor','outdoor','occupancy'])
    comfort['indoor'] = indoorTemp.iloc[datastart:dataend]
    comfort['outdoor'] = outdoorTemp.iloc[datastart:dataend]
    comfort['occupancy'] = occupancy_data.iloc[datastart:dataend]
    comfort['comfort90_min'] = comfort['outdoor'].apply(lambda x: 0.31*x + 15.8)
    comfort['comfort90_max'] = comfort['outdoor'].apply(lambda x: 0.31*x + 19.8)
    
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
    #print(comfort['comf_occ_90'].sum())
    #print(comfort['occupancy'].sum())
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
        if 'l' not in priceType: # Clunky method but works
            ecost = pd.DataFrame(eprice, columns=['Electricity Price [$/kWh]'])
            #comfort['Electric Price [$/kWh]'] = ecost.apply(lambda x: 4*x/1000 + 0.1)
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

        if 'coolSetpoints' in graphType: 
            plt.plot(time[datastart:dataend],coolTemp[datastart:dataend], label=f, linestyle=linestyles[i])
        elif 'heatSetpoints' in graphType:
            plt.plot(time[datastart:dataend],heatTemp[datastart:dataend], label=f, linestyle=linestyles[i])
        else:
            plt.plot(time[datastart:dataend],indoorTemp[datastart:dataend], label=f, linestyle=linestyles[i])
        
        # show heating and cooling setpoints if only plotting one simulation.
        if 'detail' in graphType:
            if totHeatElec[i] > 1:
                plt.plot(time[datastart:dataend], heatTemp[datastart:dataend], label="Heating Setpoint", linestyle='--')
            if totCoolElec[i] > 1:
                plt.plot(time[datastart:dataend], coolTemp[datastart:dataend], label="Cooling Setpoint", linestyle='-.')
    
    i += 1
# END For each file loop -----------------------------------------------

if graph: # Final graph display to do one time. --------------------------
    # Plot outdoor temp
    plt.plot(time[datastart:dataend], outdoorTemp[datastart:dataend], label="Outdoor", linestyle=':')
    # Readability
    plt.legend()
    plt.xlabel('Time [hours]')
    plt.ylabel('Temperature [° C]')
    plt.xlim([time[datastart],time[dataend-1]])
    plt.grid()
    plt.show()

# Output results to csv file -----------------------------------------------
if "None" not in outFile and "none" not in outFile:
    # Add title/label rows
    files.insert(0,"")
    totalPrice.insert(0,"Total HVAC Electricity Bill [$]")
    avgDailyCost.insert(0,"Avg Daily Electricity Cost [$/day]")
    totHeatElec.insert(0,"Total Heating Electricity [kWh]")
    totCoolElec.insert(0,"Total Cooling Electricity [kWh]")
    avgDailyEnergy.insert(0,"Avg Daily HVAC Electricity [kWh/day]")
    meanDiff100.insert(0,"Mean Temp Diff from 100% Comfortable [°C]")
    meanComfBand.insert(0,"Mean Comfort Band Percent [%]")
    pctTimeComf90.insert(0,"Percent of occupied time within 90% comfort band [%]")
    pctTimeComf80.insert(0,"Percent of occupied time within 80% comfort band [%]")
    heatPrice.insert(0,"Total Heating Energy Cost [$]")
    coolPrice.insert(0,"Total Cooling Energy Cost [$]")
    # Put all 1D lists into a single 2D list to write
    rows = [files,totalPrice,avgDailyCost,heatPrice, coolPrice, totHeatElec,totCoolElec,avgDailyEnergy,meanDiff100,meanComfBand,pctTimeComf90,pctTimeComf80]
    outFile = "eppp_" + date_range + outFile
    # Write file using csvwrite
    with open(outFile,"w") as out:
        writer = csv.writer(out)
        for r in rows:
            writer.writerow(r)
    print("--------------------------------------------------\n")
    print("Data successfully written to file as: " + outFile)

print(closer)
