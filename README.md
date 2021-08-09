# Energy-Co-Simulation-Pre-and-Post-Processing
Automatically generate weather and electric price input data files using real-life historical data from free, open datasets. A selection of pre-made .epw files. Quickly analyze results of EnergyPlus simulations.

Generate electric price data from CAISO datasets: See https://github.com/SCU-Smart-Grid-CPS/Energy-Co-Simulation-Pre-and-Post-Processing/blob/main/Get%20CAISO%20Pricing%20Data.pdf

Generate EPW (Energy Plus Weather) files from real weather data: See https://github.com/SCU-Smart-Grid-CPS/Energy-Co-Simulation-Pre-and-Post-Processing/blob/main/Create_EPW_RealTime_Data.pdf

EnergyPlus Post-Processing & Analysis: the codes _eppostprocess.py_ and _eppp.py_ are identical except one has a shorter name so it is easier to type. 

Converting hourly .epw data to 5 minute data: The .idf under "Get Weather Solar" very quickly returns just the temperature outdoors and solar radiation needed for the optimization simulation for a specific time frame if you set the DESIGN DAYS to the time you plan to run the later simulation. Do this before running the full simulation, and copy the resulting csv to the deployment folder in the co-sim.
