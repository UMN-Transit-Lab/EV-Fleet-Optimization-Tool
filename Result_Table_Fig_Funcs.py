# -*- coding: utf-8 -*-
"""
'''-------------------------------------------------------
*** EV Transition Optimization Tool ***
    Copyright 2026 Nastaran Tork, Behnam Davazdah Emami, and Alireza Khani
    Licensed under the GNU General Public License v3.0
    
    Code primarily written by Nastaran Tork and Behnam Davazdah Emami
	Under supervision of Alireza Khani

Contact:
    Alireza Khani:  akhani@utexas.edu or akhani@email.arizona.edu
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

import pandas as pd 
import matplotlib.pyplot as plt
from math import ceil
import numpy as np
from matplotlib.ticker import MaxNLocator 
from pyomo.environ import value

def create_summary_table(model, phases, vehicle_types):
    columns = [
    'Routes','Current Fleet', '# EVs', '# Chargers', 
    'Budget', 'EVs cost', 'Charging Station Cost', 'Surplus Budget'
]

    index = [f'Phase {p}' for p in phases] + ['Total']
    df = pd.DataFrame(index=index, columns=columns)
    
    route_details = {}
    phase_results = {p: {} for p in phases}
    
    for phi in phases:
        # Routes - count electrified routes in this phase
        electrified_routes = [j for j in model.J if model.y[phi, j].value > 0.5]
        route_details[phi] = electrified_routes
        phase_results[phi]['Routes'] = len(electrified_routes)
        phase_results[phi]['Route_Ids'] = electrified_routes
        
        # EVs - sum across vehicle types
        phase_results[phi]['EVs'] = sum(
        model.z[phi, j].value 
        for j in model.J
        if model.z[phi, j].value is not None
    )
        
        
        # Chargers - new charging piles in this phase
        if phi == min(phases):
            phase_results[phi]['Chargers'] = sum(model.u[phi, i, p].value for i in model.I for p in model.Ctype)
        else:
            phase_results[phi]['Chargers'] = sum(
            model.u[phi, i, p].value - model.u[phi-1, i, p].value
            for p in model.Ctype
            for i in model.I)

        def Construction_Cost(m, phi):
            return sum(m.x_new[phi, i].value * m.ConstructionCost[phi, i] for i in m.I)
        
        def charger_cost(m, phi):
            return sum(m.u_new[phi, i, p].value * m.Charger[phi, p]  for i in m.I for p in m.Ctype)
        
        def purchasing_cost(m, phi):
            return sum(m.z_new[phi, a].value * m.FleetPurchaseCost[phi, a] for a in m.Vtype)            
            
        b_cost1 = value(Construction_Cost(model, phi))
        b_cost2 = value(charger_cost(model, phi))
        b_cost3 = value(purchasing_cost(model, phi))
        surplus = value(model.b[phi])
        
        phase_results[phi]['Charging Station Cost'] = b_cost1 + b_cost2
        phase_results[phi]['EVs cost'] = b_cost3
        phase_results[phi]['Surplus Budget'] = surplus
        phase_results[phi]['Budget'] = value(model.Budget[phi])
    
    # Populate table
    for phi in phases:
        df.loc[f'Phase {phi}', 'Routes'] = phase_results[phi]['Routes']
        df.loc[f'Phase {phi}', 'Current Fleet'] = 'Manual'  # Placeholder
        df.loc[f'Phase {phi}', '# EVs'] = phase_results[phi]['EVs']
        df.loc[f'Phase {phi}', '# Chargers'] = phase_results[phi]['Chargers']
        df.loc[f'Phase {phi}', 'Budget'] = phase_results[phi]['Budget']
        df.loc[f'Phase {phi}', 'EVs cost'] = phase_results[phi]['EVs cost']
        df.loc[f'Phase {phi}', 'Charging Station Cost'] = phase_results[phi]['Charging Station Cost']
        df.loc[f'Phase {phi}', 'Surplus Budget'] = phase_results[phi]['Surplus Budget']
    
    # Calculate totals
    df.loc['Total', 'Routes'] = phase_results[phi]['Routes'] 
    df.loc['Total', '# EVs'] = phase_results[phi]['EVs'] 
    df.loc['Total', '# Chargers'] = sum(phase_results[phi]['Chargers'] for phi in phases)
    df.loc['Total', 'Budget'] = sum(phase_results[phi]['Budget'] for phi in phases)
    df.loc['Total', 'EVs cost'] = sum(phase_results[phi]['EVs cost'] for phi in phases)
    df.loc['Total', 'Charging Station Cost'] = sum(phase_results[phi]['Charging Station Cost'] for phi in phases)
    df.loc['Total', 'Surplus Budget'] = sum(phase_results[phi]['Surplus Budget'] for phi in phases)  # Final surplus
    
    return df, route_details


def plot_station_charging_activity(model, phases, stations, save_path=None):
    """
    Plot charging activity for each station in separate subplots
    
    Parameters:
    model -- Solved Pyomo model
    phase -- Phase to visualize (e.g., 1, 2, 3)
    save_path -- Optional path to save figure
    """

    time_slots = sorted(list(model.T))
    n_stations = len(stations)
    n_phases = len(phases)
    
    n_cols = min(1, n_stations)  
    n_rows = ceil(n_stations / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 6 * n_rows))
    
    if n_stations == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    phase_colors = plt.cm.viridis(np.linspace(0, 1, n_phases))
    
    bar_width = 0.8 / n_phases
    x = np.arange(len(time_slots))
    
    for idx, ax in enumerate(axes):
        label = f'({chr(97 + idx)})' 
        ax.text(-0.02, 1.08, label, transform=ax.transAxes, 
                fontsize=18, fontweight='bold', 
                va='top', ha='left', 
                )
    
    csv_data = []
    
    for station_idx, i in enumerate(stations):
        ax = axes[station_idx]
        
        # Find max EVs for this station across all phases
        max_evs = 0
        for t in time_slots:
            for phase in phases:
                station_evs = sum(value(model.omega[phase, i, j, t]) for j in model.J)
                if station_evs > max_evs:
                    max_evs = station_evs
                    
        y_max = max_evs * 1.2 if max_evs > 0 else 1
        
        # Create grouped bars for each phase
        for phase_idx, phase in enumerate(phases):
            ev_counts = []
            for t in time_slots:
                station_evs = sum(value(model.omega[phase, i, j, t]) for j in model.J)
                ev_counts.append(station_evs)
                csv_data.append({'Station': i, 'Phase': phase, 'Time': t, 'EVs Charging': station_evs})
            
            positions = x + phase_idx * bar_width
            
            bars = ax.bar(
                positions, 
                ev_counts, 
                width=bar_width,
                color=phase_colors[phase_idx],
                label=f'Stage {phase}'
            )
         
        
        # Format subplot
        #ax.set_title(f'Station {i} Charging Activity', fontsize=14)
        ax.set_xlabel('Time of Day', fontsize=16, weight='bold')
        ax.set_ylabel('EVs Charging', fontsize=16, weight='bold')
        ax.set_xticks(x + bar_width * (n_phases-1)/2)
        ax.set_xticklabels(time_slots)
        ax.set_ylim(0, y_max)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(loc='upper right', fontsize=16)
        
        # Add time period shading
        ax.axvspan(-1, 4.2, color='gray', alpha=0.1)
        ax.axvspan(4.2, 14.2, color='orange', alpha=0.1)
        ax.axvspan(14.2, 19.2, color='yellow', alpha=0.1)
        ax.axvspan(19.2, 23, color='orange', alpha=0.1)
        
        # Add time period labels
        ax.text(1.5, y_max * 0.9, 'Supper off-peak', ha='center', fontsize=14, fontweight='bold')
        ax.text(9.5, y_max * 0.9, 'Off-peak', ha='center', fontsize=14, fontweight='bold')
        ax.text(16.5, y_max * 0.9, 'On-peak', ha='center', fontsize=14, fontweight='bold')
        ax.text(20.5, y_max * 0.9, 'Off-peak', ha='center', fontsize=14, fontweight='bold')
        ax.tick_params(axis='both', labelsize=16)
    
    for idx in range(n_stations, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)  # Space for suptitle
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        csv_path = save_path.replace('.png', '.csv')
        pd.DataFrame(csv_data).to_csv(csv_path, index=False)
    
    plt.show()


def plot_cost_breakdown(model, phases, routes, path_file):
    """
    Plot objective cost breakdown by route and phase
    
    """
    cost_components = [
        'ICE Operation cost', 
        'EV Maintenance cost',
        'Charging cost',
        'Penalty cost',
        'Deadheading cost'
    ]
    
    component_colors = [
        "#332288",  # Indigo
        "#88CCEE",  # Light Blue
        "yellow",  # Teal
        "#117733",  # Green
        "#999933",  # Olive
        "#DDCC77",  # Sand
        "#CC6677",  # Rose
        "#882255",  # Wine
        "#AA4499"   # Purple
    ]
    
    suffix_to_vtype = {
        'H': 'Heavy-Duty',
        'M': 'Medium-Duty',
        'L': 'Light-Duty'
    } 
    
    results = {comp: np.zeros((len(phases), len(routes))) for comp in cost_components}
    
    for phi_idx, phi in enumerate(phases):
        for route_idx, j in enumerate(routes):
            # Operation cost (diesel)
            results['ICE Operation cost'][phi_idx, route_idx] = value(
                model.DieselOperatingCost[j] * (1 - model.y[phi, j])
            )
            
            # Maintenance cost (EV)
            results['EV Maintenance cost'][phi_idx, route_idx] = value(
                model.EVMaintenance[j] * model.y[phi, j]
            )
            
            # Charging cost
            charging_cost = 0
            for i in model.I:
                for t in model.T:
                    charging_cost += value(
                        model.ChargingCost[t] * model.omega[phi, i, j, t]
                    )
            results['Charging cost'][phi_idx, route_idx] = charging_cost
            
            # Penalty cost
            penalty_cost = 0
            for i in model.I:
                for t in model.T:
                    suffix = j.split('_')[-1]
                    vehicle_type = suffix_to_vtype[suffix]
                    penalty_cost += value(
                        model.PenaltyCost[phi, vehicle_type] * model.omega_hat[phi, i, j, t]
                    )
            results['Penalty cost'][phi_idx, route_idx] = penalty_cost
            
            # Relocation cost
            relocation_cost = 0
            for i in model.I:
                for t in model.T:
                    suffix = j.split('_')[-1]
                    vehicle_type = suffix_to_vtype[suffix]
                    relocation_cost += value(
                        model.RelocDistance[i, j] * model.RelocationCost[phi, vehicle_type] * model.omega[phi, i, j, t]
                    )
            results['Deadheading cost'][phi_idx, route_idx] = relocation_cost
            

    phase_dfs = []
    for phi_idx, phi in enumerate(phases):
        df = pd.DataFrame()
        for comp in cost_components:
            df[comp] = results[comp][phi_idx]
        df['Route'] = routes
        df['Phase'] = phi

        phase_dfs.append(df)
    
    cost_df = pd.concat(phase_dfs)
    if path_file:
        csv_path = path_file.replace('.png', '.csv')
        cost_df.to_csv(csv_path, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    for i, ax in enumerate(axes):
        label = f'({chr(97+i)})'  # a, b
        ax.text(0.02, 1.05, label, transform=ax.transAxes,
                fontsize=14, fontweight='bold', va='top', ha='left')

    
    # 1. Stacked bar plot by phase
    phase_totals = cost_df.groupby('Phase')[cost_components].sum()
    phase_totals.plot.bar(stacked=True, ax=axes[0], color=component_colors)
    axes[0].set_ylabel('Cost ($)', fontsize=14, weight='bold')
    axes[0].set_xlabel('Phase', fontsize=14, weight='bold')
    #axes[0].set_xlabel('Stage', fontsize=14, weight='bold')
    axes[0].tick_params(axis='x', rotation=0)
    axes[0].tick_params(axis='both', labelsize=14) 
    axes[0].legend(title='Cost Component', title_fontsize=14, fontsize=12)
    
    # 2. Cost by route (averaged across phases)
    #axes[1].set_title('Average Cost Breakdown by Route', fontsize=14)
    #route_labels = [f'Route {i+1}' for i in range(len(routes))]
    last_phase = phases[-1]
    last_phase_df = cost_df[cost_df['Phase'] == last_phase]
    # route_avgs = cost_df.groupby('Route')[cost_components].sum()
    route_last_phase = last_phase_df.groupby('Route')[cost_components].sum()
    
    #route_avgs.index = route_labels
    def route_to_group(route_str):
        if '0_H' in route_str:
            #return 'Fleet Group 1'
            return 'Route 1'
        elif '0_M' in route_str:
            #return 'Fleet Group 2'
            return 'Route 2'
        elif '0_L' in route_str:
            #return 'Fleet Group 3'
            return 'Route 3'
        elif '1_M' in route_str:
            #return 'Fleet Group 4'
            return 'Route 4'
        elif '1_L' in route_str:
            #return 'Fleet Group 5'
            return 'Route 5'
        elif '2_L' in route_str:
            #return 'Fleet Group 6'
            return 'Route 6'
        elif '3_M' in route_str:
            #return 'Fleet Group 7'
            return 'Route 7'
        elif '3_L' in route_str:
            #return 'Fleet Group 8'
            return 'Route 8'
        else:
            return route_str  # Fallback to original name if no pattern matches
    
    # Generate new labels based on route names
    route_last_phase = route_last_phase.sort_index(
        key=lambda idx: [int(route_to_group(r).split()[-1]) for r in idx])
    
    new_labels = [route_to_group(route) for route in route_last_phase.index]
    
    # 4) Plot
    route_last_phase.plot.bar(stacked=True, ax=axes[1], color=component_colors)
    

    axes[1].set_xticklabels(new_labels, rotation=45, ha='right')
    axes[1].set_ylabel('Aggregated Cost ($)', fontsize=14, weight='bold')
    #axes[1].set_xlabel('Fleet Group', fontsize=14, weight='bold')
    axes[1].set_xlabel('Route', fontsize=14, weight='bold')
    axes[1].tick_params(axis='both', labelsize=14) 
    axes[1].legend(title='Cost Component', title_fontsize=14, fontsize=12)
    
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.95, hspace=0.4)
    plt.savefig(path_file, dpi=300)
    plt.show()
    plt.close()
    

