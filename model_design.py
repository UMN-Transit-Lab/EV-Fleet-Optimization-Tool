# -*- coding: utf-8 -*-
"""
'''-------------------------------------------------------
*** EV Transition Optimization Tool ***
    Copyright 2026 Nastaran Tork, Behnam Davazdah Emami, and Alireza Khani
    Licensed under the GNU General Public License v3.0
    
    Code primarily written by Nastaran Tork and Behnam Davazdah Emami
	Under supervision of Alireza Khani

Contact:
    Alireza Khani:  akhani@umn.edu or akhani.phd@gmail.com
    Nastaran Tork: 	tork0100@umn.edu
    Behnam Davazdah Emami:   davaz001@umn.edu
-------------------------------------------------------
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    https://www.gnu.org/licenses/gpl-3.0.en.html
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-------------------------------------------------------'''
"""

from pyomo.core import *
from Result_Table_Fig_Funcs import create_summary_table, plot_station_charging_activity
from Result_Table_Fig_Funcs import plot_cost_breakdown 
import matplotlib.pyplot as plt
import os

# Setup relative paths for Github
current_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.join(current_dir, 'Results')

# Create directories if they don't exist
os.makedirs(results_dir, exist_ok=True)

model = AbstractModel()


# parameters
model.stage = Param(within = PositiveIntegers)
model.station = Param(within = PositiveIntegers)
model.route = Param(within = PositiveIntegers)
model.Time = Param(within = PositiveReals)
model.num_selected_routes = Param(within = PositiveIntegers)
model.InterestP = Param(within = NonNegativeReals)
model.M = Param(initialize=1000)


# Sets
# All phases
model.phi =  RangeSet(1, model.stage);
# phases >= 1
model.phi2 =  RangeSet(2, model.stage);
# stations
model.I = Set()
# routes
model.J = Set()
# time intervals
model.T = Set()
model.T2 = Set()
# vehicle types
model.Vtype = Set()
model.PeriodLength =  Param(model.phi); 
# Charger types
model.Ctype = Set()
# Charger types for each Class
model.CPower = Set(dimen=2)

# Costs
# Operating cost for each non-electrified route (fuel cost + maintenance cost)*length (c_o)
model.DieselOperatingCost =  Param(model.J)
# EV maintenance cost --> unit cost * route length (c_m)
model.EVMaintenance =  Param(model.J)  
# Charging cost --> electricity tariffs at time t * charging rate * time slot length  (p_t)
model.ChargingCost =  Param(model.T) 
# Penalty cost (c_p)
model.PenaltyCost =  Param(model.phi, model.Vtype) 
# Relocation cost (c_r)
model.RelocationCost =  Param(model.phi, model.Vtype) 
# Distance between station i and route terminal j 
model.RelocDistance =  Param(model.I, model.J)
# Maximum capacity of candidate station i  
model.MaxCapacity =  Param(model.I)
# Charging station construction cost
model.ConstructionCost =  Param(model.phi, model.I)
# Charger purchasing cost
model.Charger =  Param(model.phi, model.Ctype); 
# Budget for period phi        
model.Budget =  Param(model.phi);  
# Minimum fleet size j  based on schedule
model.RouteMinSize =  Param(model.J, model.T) 
# Required fleet based on mileage consumption (energy)  of route j by time t
model.Consumption =  Param(model.J, model.T)
# Fleet purchasing cost 
model.FleetPurchaseCost =  Param(model.phi, model.Vtype)  
# Power rating for charger type
model.Alpha = Param(model.Ctype)
# Maximum power of candidate station i  
model.MaxPower =  Param(model.I)
# Battery energy of vehicle types
model.BatteryE = Param(model.Vtype)
# Number of vehicles need to be electrified
model.Num_Vehicles = Param(model.Vtype)


# Variables
# if charging station i been opened
model.x =  Var(model.phi, model.I, domain =  Binary)
model.x_new =  Var(model.phi, model.I, domain =  Binary)
# if route j has been electrified 
model.y =  Var(model.phi, model.J, domain =  Binary);
# if route j is assigned to charging station i 
model.s =  Var(model.phi, model.I, model.J, domain =  Binary)
# fleet size of route j at stage \phi (Integer).
model.z =  Var(model.phi, model.J, domain =  NonNegativeIntegers)
model.z_new_aux = Var(model.phi, model.J, domain =  NonNegativeIntegers)
model.z_new =  Var(model.phi, model.Vtype, domain =  NonNegativeIntegers)
# number of vehicles charging at station i in time slot t from route j at period \phi (Integer).
model.omega =  Var(model.phi, model.I, model.J, model.T , domain = NonNegativeIntegers)
# number of non-electric vehicles to satisfy consumption demand from route j 
model.omega_hat =  Var(model.phi, model.I, model.J, model.T , domain = NonNegativeIntegers)

# number of accumulated charging piles (BASED ON TYPE) in station i up to phase \phi (Integer).
model.u =  Var(model.phi, model.I, model.Ctype, domain =  NonNegativeIntegers)
model.u_new =  Var(model.phi, model.I, model.Ctype, domain =  NonNegativeIntegers)

# Amount of money not spend at period \phi.
model.b =  Var(model.phi, domain =  NonNegativeReals)
# Active fleet activity for each time interval
model.v = Var(model.phi, model.I, model.J, model.T, domain = NonNegativeReals)

# Auxiliary variable for linearization a constraint
model.w = Var(model.phi, model.J,  domain=NonNegativeIntegers)

# Constraints

# Constraint_2:
def x_sequence(m, phi, i):
    return m.x[phi, i] >= m.x[phi-1, i]

model.const_2 =  Constraint(model.phi2, model.I, rule = x_sequence)

# Constraint_3:
def x_x_new_start(m, i):
    return m.x_new[1, i] >= m.x[1, i]

model.const_3 =  Constraint(model.I, rule = x_x_new_start)

# Constraint_4:
def x_x_new(m, phi, i):
    return m.x_new[phi, i] == m.x[phi, i] - m.x[phi-1, i]

model.const_4 =  Constraint(model.phi2, model.I, rule = x_x_new)

# Constraint_5:
def u_u_new_start(m, i, p):
    return m.u_new[1, i, p] == m.u[1, i, p]

model.const_5 =  Constraint(model.I, model.Ctype, rule = u_u_new_start)

# Constraint_6:
def u_u_new(m, phi, i, p):
    return m.u_new[phi, i, p] == m.u[phi, i, p] - m.u[phi-1, i, p]

model.const_6 =  Constraint(model.phi2, model.I, model.Ctype, rule = u_u_new)

# Constraint_7:
def ux_station_capacity(m, phi, i):
    return sum(m.u[phi, i, p] for p in m.Ctype) <= m.MaxCapacity[i] * m.x[phi, i] 
model.const_7 =  Constraint(model.phi, model.I, rule = ux_station_capacity)


# Constraint_8:
def ux_power_capacity(m, phi, i):
    return sum(m.u[phi, i, p] * m.Alpha[p]  for p in m.Ctype) <= m.MaxPower[i] * m.x[phi, i] 
model.const_8 =  Constraint(model.phi, model.I, rule = ux_power_capacity)


# Constraint 9:
def y_sequence(m, phi, j):
    return m.y[phi, j] >= m.y[phi - 1, j]

model.const_9 = Constraint(model.phi2, model.J, rule = y_sequence)    

# Constraint 10:
    
def assign_z_y(m, phi, j):
    return m.z[phi, j] <= m.M * m.y[phi, j]

model.const_10 = Constraint(model.phi, model.J, rule = assign_z_y)  

# Constraint 11: sum(s) = y
def assign_s_y(m, phi, j):
    return sum(m.s[phi, i, j] for i in m.I) == m.y[phi, j]

model.const_11 = Constraint(model.phi, model.J, rule = assign_s_y)    

# Constraint 12: s <= x
def assign_s_x(m, phi, i, j):
    return m.s[phi, i, j] <= m.x[phi, i]

model.const_12 = Constraint(model.phi, model.I, model.J, rule = assign_s_x)

# Additional Constraint: if a station is opened must be assigned to a route
def assign_s_x_aux(m, phi, i):
    return m.x[phi, i] <= sum(m.s[phi, i, j] for j in m.J) 

model.const_12_aux = Constraint(model.phi, model.I, rule = assign_s_x_aux)


# Constraint 13: s <= sum(u)

def assign_s_u(m, phi, i, j):
    
    suffix = j.split('_')[-1]
    vehicle_type = suffix_to_vtype[suffix]
    # Get all charger types for this vehicle type
    allowed_chargers = [p for (a, p) in m.CPower if a == vehicle_type]
    return m.s[phi, i, j] <= sum(m.u[phi, i, p] for p in allowed_chargers)

model.const_13 = Constraint(model.phi, model.I, model.J, rule=assign_s_u)


#------ Auxiliary for Constraint_14 & 15 ------
def z_sequence_start(m, j):
    return m.z_new_aux[1, j] == m.z[1, j] 

model.const_14_aux_1 = Constraint(model.J, rule = z_sequence_start)

def z_sequence(m, phi, j):
    return m.z_new_aux[phi, j] == m.z[phi, j] - m.z[phi-1, j] 

model.const_15_aux_1 = Constraint(model.phi2, model.J, rule = z_sequence)
#--------------------------------

# Constraint_14 & 15:

def z_new_vtype(m, phi, a):
    
    routes_for_vtype = [
        j for j in m.J 
        if j.endswith(tuple(suffix_to_vtype.keys())) 
        and suffix_to_vtype[j.split('_')[-1]] == a   
    ]
    
    return m.z_new[phi, a] == sum(m.z_new_aux[phi, j] for j in routes_for_vtype)

model.const_15 = Constraint(model.phi, model.Vtype, rule = z_new_vtype)

#======================Constraints 16 - 19 =================================#
suffix_to_vtype = {
    'H': 'Heavy-Duty',
    'M': 'Medium-Duty',
    'L': 'Light-Duty'
}  


# Linearization constraints
def w_upper_bound_z_rule(m, j):
    return m.w[m.stage, j] == m.z[m.stage, j]
model.w_upper_bound_z = Constraint(model.J, rule=w_upper_bound_z_rule)

def w_upper_bound_My_rule(m, j):
    return m.w[m.stage, j] <= m.M * m.y[m.stage, j]
model.w_upper_bound_My = Constraint(model.J, rule=w_upper_bound_My_rule)

def w_lower_bound_rule(m, j):
    return m.w[m.stage, j] >= m.z[m.stage, j] - m.M * (1 - m.y[m.stage, j])
model.w_lower_bound = Constraint(model.J, rule=w_lower_bound_rule)

# Original constraint

def y_sequence_end(m, a):
    
    routes_for_vtype = [
        j for j in m.J 
        if j.endswith(tuple(suffix_to_vtype.keys())) 
        and suffix_to_vtype[j.split('_')[-1]] == a   
    ]
    
    return sum(m.w[m.stage, j] for j in routes_for_vtype) >= m.Num_Vehicles[a]

model.const_16 = Constraint(model.Vtype, rule=y_sequence_end)

#=======================================================#

# Constraint_17
def Construction_Cost(m, phi):
    return sum(m.x_new[phi, i] * m.ConstructionCost[phi, i] for i in m.I)

def charger_cost(m, phi):
    return sum(m.u_new[phi, i, p] * m.Charger[phi, p]  for i in m.I for p in m.Ctype)

def purchasing_cost(m, phi):
    return sum(m.z_new[phi, a] * m.FleetPurchaseCost[phi, a] for a in m.Vtype)

def budget_constraint(m, phi):
    b_cost1 = Construction_Cost(m, phi)
    b_cost2 = charger_cost(m, phi)
    b_cost3 = purchasing_cost(m, phi)
    
    
    return b_cost1 + b_cost2 + b_cost3 + m.b[phi] == m.Budget[phi]

model.const_17 =  Constraint(model.phi, rule = budget_constraint)


# Constraint_18:
def omega_station_capacity(m, phi, i, j, t):
    return m.omega[phi, i, j, t] <= m.MaxCapacity[i] * m.s[phi, i, j]
model.const_18 =  Constraint(model.phi, model.I, model.J, model.T, rule = omega_station_capacity)

# Constraint_19:
def omega_u_charge_chargers(m, phi, i, t, a):
    
    routes_for_vtype = [
        j for j in m.J 
        if j.endswith(tuple(suffix_to_vtype.keys())) 
        and suffix_to_vtype[j.split('_')[-1]] == a
    ]
    
    total_charging_flow = sum(m.omega[phi, i, j, t] for j in routes_for_vtype)
    allowed_chargers = [p for (vehicle_type, p) in m.CPower if vehicle_type == a]
    
    return total_charging_flow <= sum(m.u[phi, i, p] for p in allowed_chargers)

model.const_19 = Constraint(model.phi, model.I, model.T, model.Vtype, rule = omega_u_charge_chargers)

# Constraint_20:
def omega_u_energy(m, phi, i, t, a):
    
    routes_for_vtype = [
        j for j in m.J 
        if j.endswith(tuple(suffix_to_vtype.keys())) 
        and suffix_to_vtype[j.split('_')[-1]] == a
    ]
    
    total_charging_flow = sum(m.omega[phi, i, j, t] * m.BatteryE[a] for j in routes_for_vtype)
    allowed_chargers = [p for (vehicle_type, p) in m.CPower if vehicle_type == a]
    
    return total_charging_flow <= sum(m.u[phi, i, p] * m.Alpha[p] for p in allowed_chargers)

model.const_20 = Constraint(model.phi, model.I, model.T, model.Vtype, rule = omega_u_energy)


# Constraint_21:
def zmin_omega_fleetSize(m, phi, j, t):
    return m.RouteMinSize[j, t] * m.y[phi, j] + sum(m.omega[phi, i, j, t] for i in m.I) <= m.z[phi, j]
model.const_21 = Constraint(model.phi, model.J, model.T, rule = zmin_omega_fleetSize)

# Constraint_22:
# =============================================================================
def total_zmin_fleetSize(m, phi, j):
     return sum(m.RouteMinSize[j, t] * m.y[phi, j] for t in m.T) <= m.z[phi, j]
model.const_22 = Constraint(model.phi, model.J, rule = total_zmin_fleetSize)
# =============================================================================

# Constrain_23 & Constraint_24:
#-----------------------
# Active EV from route j at time t
def v_t_definition(m, phi, i, j, t):
    return m.v[phi, i, j, t] + m.omega[phi, i, j, t] + m.omega_hat[phi, i, j, t] - m.Consumption[j,t] * m.s[phi, i, j] == m.v[phi, i, j, t+1]

model.const_23 = Constraint(model.phi, model.I, model.J, model.T2, rule = v_t_definition)

def v_t_definition_end(m, phi, i, j):
    return m.v[phi, i, j, m.Time] + m.omega[phi, i, j, m.Time] + m.omega_hat[phi, i, j, m.Time] - m.Consumption[j, m.Time] * m.s[phi, i, j] == m.v[phi, i, j, 1]

model.const_23_end = Constraint(model.phi, model.I, model.J, rule = v_t_definition_end)

#-----------------------
# Constrain_25:
    
def v_z_relationship(m, phi, i, j ,t):
    return m.v[phi, i, j, t]  <= m.z[phi, j] 

model.const_25 = Constraint(model.phi, model.I, model.J, model.T, rule = v_z_relationship)

#-----------------------
# Constrain_new_1:
M = 10000
def y_z_relationship(m, phi, j):
    return m.z[phi, j, ]  <= m.y[phi, j] * M 

model.const_new = Constraint(model.phi,  model.J, rule = y_z_relationship)


# Objective Function

def ComputeCost_rule(m):
    Operation_cost = sum(sum(m.DieselOperatingCost[j] * (1 - m.y[phi , j])  for j in m.J) for phi in m.phi)
    Maintenance_cost = sum(sum(m.EVMaintenance[j] * (m.y[phi , j])  for j in m.J) for phi in m.phi)
    Charging_Cost = sum(sum(sum(sum(m.ChargingCost[t] * m.omega[phi , i, j, t] for t in m.T) for j in m.J) for i in m.I) for phi in m.phi)
    
    Penalty_Cost = 0
    for phi in m.phi:
        for i in m.I:
            for j in m.J:
                # Extract vehicle type from route name
                suffix = j.split('_')[-1]
                vehicle_type = suffix_to_vtype[suffix]
                for t in m.T:
                    Penalty_Cost += m.PenaltyCost[phi, vehicle_type] * m.omega_hat[phi, i, j, t]


    
    Relocation_Cost = 0
    for phi in m.phi:
        for i in m.I:
            for j in m.J:
                # Extract vehicle type from route name
                suffix = j.split('_')[-1]
                vehicle_type = suffix_to_vtype[suffix]
                for t in m.T:
                    Relocation_Cost += m.RelocDistance[i,j] * m.RelocationCost[phi, vehicle_type] * m.omega[phi , i, j, t]
  
   
    Saved_Money = sum(m.b[phi]/m.PeriodLength[phi]  for phi in m.phi)

    return Operation_cost + Maintenance_cost + Charging_Cost + Penalty_Cost + Relocation_Cost -  m.InterestP * Saved_Money

model.Cost = Expression(rule = ComputeCost_rule)
def total_cost_rule(m):
    return m.Cost
model.Total_Cost_Objective = Objective(rule=total_cost_rule, sense=minimize)


from pyomo.environ import SolverFactory
param_file = os.path.join(current_dir, 'parameters.dat')
instance = model.create_instance(param_file)

# Solve the model
solver = SolverFactory('gurobi')

solver.options['LogFile'] = 'gurobi.log'  # Log output to a file
solver.options['OutputFlag'] = 1  # Enable solver output
solver.options['MIPGap'] = 0.01  # Set the MIP gap to 1%
solver.options['TimeLimit'] = 7200  # Set a time limit of 600 seconds
results = solver.solve(instance, tee=True)  # Set tee=True to display solver output in the notebook

detailed_data = []

print("\nCharging Stations Opened:")
for i in instance.I:
    for phi in instance.phi:
        if instance.x[phi, i].value > 0.5:
            print(f"- Station {i} is opened at Phase {phi}")
            detailed_data.append({'Category': 'Opened Charging Station', 'Phase': phi, 'Station': i, 'Route': '', 'Time': '', 'Charger Type': '', 'Value': '', 'Description': f'Station {i} is opened at Phase {phi}'})
            break


print("\nElectrified Routes:")
for j in instance.J:
    for phi in instance.phi:
        if instance.y[phi, j].value > 0.5:
           print(f"- Route {j} is electrified at Phase {phi}")
           detailed_data.append({'Category': 'Electrified Route', 'Phase': phi, 'Station': '', 'Route': j, 'Time': '', 'Charger Type': '', 'Value': '', 'Description': f'Route {j} is electrified at Phase {phi}'})

print("\nFleet Size (z) values:")
for phi in instance.phi:
    for j in instance.J:
        val = instance.z[phi, j].value
        if val is not None:  
            print(f"Phase {phi}, Route {j}: {val:.0f} vehicles")
            if val > 0:
                detailed_data.append({'Category': 'Fleet Size', 'Phase': phi, 'Station': '', 'Route': j, 'Time': '', 'Charger Type': '', 'Value': int(val), 'Description': f'Phase {phi}, Route {j}: {val:.0f} vehicles'})
  
print("\n-- Route-to-Station Assignments (s=1) --")
for phi, i, j in instance.s:
    if value(instance.s[phi, i, j]) > 0.5:     # treat as binary
        print(f"Phase={phi:>2},  Station={i:>3},  Route={j:>3}")
        detailed_data.append({'Category': 'Route-to-Station Assignment', 'Phase': phi, 'Station': i, 'Route': j, 'Time': '', 'Charger Type': '', 'Value': '', 'Description': f'Route {j} assigned to Station {i} at Phase {phi}'})


print("\nChargers (u) values:")
for phi in instance.phi:
    for i in instance.I:
        for p in instance.Ctype:
            val = instance.u[phi, i, p].value
            if val is not None:  
                print(f"Phase {phi}, Station {i}, Charger type {p}: {val:.0f} charger")
                if val > 0:
                    detailed_data.append({'Category': 'Chargers Installed', 'Phase': phi, 'Station': i, 'Route': '', 'Time': '', 'Charger Type': p, 'Value': int(val), 'Description': f'{val:.0f} charger(s) of type {p} at Station {i}, Phase {phi}'})


print("\n-- Vehicles Charging (omega) --")
for (phi, i, j, t), var in instance.omega.items():
    v = value(var)
    if v:
        print(f"Phase={phi}, Station={i}, Route={j}, Time={t} --> omega = {v}")
        detailed_data.append({'Category': 'Vehicles Charging', 'Phase': phi, 'Station': i, 'Route': j, 'Time': t, 'Charger Type': '', 'Value': int(v), 'Description': f'At Time {t}, {v} vehicles from Route {j} charge at Station {i} in Phase {phi}'})

print("\n-- ICE Back-ups (omega_hat) --")
for (phi, i, j, t), var in instance.omega_hat.items():
    v = value(var)
    if v:
        print(f"Phase={phi}, Station={i}, Route={j}, Time={t} --> omega_hat = {v}")
        detailed_data.append({'Category': 'ICE Back-up Vehicles', 'Phase': phi, 'Station': i, 'Route': j, 'Time': t, 'Charger Type': '', 'Value': int(v), 'Description': f'At Time {t}, {v} ICE backup vehicles used for Route {j} at Station {i} in Phase {phi}'})

import pandas as pd
df_detailed = pd.DataFrame(detailed_data)
df_detailed.to_csv(os.path.join(results_dir, 'detailed_result.csv'), index=False)
    

# Active routes with their assigned stations
# Last phase
phi_val = instance.phi[-1]
active_routes = []
route_assignments = {}  # {route: station}

for j in instance.J:
    if instance.y[phi_val, j].value > 0.5:
        assigned_station = None
        for i in instance.I:
            if instance.s[phi_val, i, j].value > 0.5:
                assigned_station = i
                break
        if assigned_station:
            active_routes.append(j)
            route_assignments[j] = assigned_station



#------------ Summary Result Table ------------#

summary_table, route_details = create_summary_table(instance, instance.phi, instance.Vtype)
summary_table.to_csv(os.path.join(results_dir, 'optimization_summary.csv'))

#------------- Charging activity per station each phase --------#
for phase_idx, phi in enumerate(instance.phi):
    active_stations = []
    for i in instance.I:
        if value(instance.x[phi, i]) > 0.5:
            active_stations.append(i)
plot_station_charging_activity(instance, instance.phi, active_stations, save_path=os.path.join(results_dir, 'station_charging.png'))


#----------------Objective Cost for Phases and Routes -------#
path_file = os.path.join(results_dir, 'Cost_breakdown.png')
plot_cost_breakdown(instance, instance.phi, instance.J, path_file)
# baseline_csv = os.path.join(results_dir, 'baseline_results.csv')
# plot_cost_breakdown_with_baseline(instance, instance.phi, instance.J, path_file, baseline_csv)


