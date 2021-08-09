# hourlyTo5min.py
# Author(s):    Brian Woo-Shem
# Version:      0.9
# Last Updated: 2021-07-20
# Simple program to upsample convert hourly csv data to 5 minute data
# Uses nearest value algorithm, repeating each value 12 times.
# Input file has values like: '1, 2, 4, 5, 2, ...'
# Output file has values in columns as needed for UCEF Optimization program

import numpy as np

# Change Source File and Output File <============== !
infile = 'CHANGE_ME.csv'
outfile = 'CHANGE_THIS_NAME.csv'

# Numpy input csv file
vals = np.genfromtxt(infile, delimiter=",")
n = len(vals)

# print(vals) # Uncomment for sanity check

# Numpy array in columns instead of rows
newprc = np.zeros((n*12,1))

# Repeat the same value 12 times for 12 timesteps
for i in range (0,n):
    for j in range (0,12):
        newprc[i*12+j,0] = vals[i]

# print(newprc) # Uncomment for sanity check

np.savetxt(outfile, newprc[:,0], delimiter=',')
