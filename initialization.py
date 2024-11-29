# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 15:03:03 2024

@author: samuel.delgado
"""
import numpy as np
import matplotlib.pyplot as plt
import platform
import shutil
import os 
from crystal_lattice import Crystal_Lattice
from superbasin import Superbasin
from pymatgen.ext.matproj import MPRester
import json
from pathlib import Path

import pickle
import shelve


def initialization(n_sim,save_data,ovito_file):
    
    seed = 1
    # Random seed as time
    rng = np.random.default_rng(seed) # Random Number Generator (RNG) object

    # Default resolution for figures
    plt.rcParams["figure.dpi"] = 100 # Default value of dpi = 300
    
    if save_data:
        files_copy = ['initialization.py', 'crystal_lattice.py','Site.py','main.py','KMC.py',
                      'balanced_tree.py','analysis.py','superbasin.py','activation_energies_set.json']
        
        if platform.system() == 'Windows': # When running in laptop
            dst = Path(r'\\FS1\Docs2\samuel.delgado\My Documents\Publications\Material deposition exploration\Simulations\Test')
        elif platform.system() == 'Linux': # HPC works on Linux
            dst = Path(r'/sfiwork/samuel.delgado/Copper_deposition/Varying_substrate/batch_simulation/annealing/TaN/T300/')
            
        paths,Results = save_simulation(files_copy,dst,n_sim) # Create folders and python files
        
    else:
        paths = {'data': ''}
        Results = []
        
    experiments = ['deposition','annealing']
    experiment = experiments[0]

    if experiment == 'deposition':         
# =============================================================================
#         Experimental conditions
#         
# =============================================================================
        sticking_coeff = 1
        partial_pressure = 10 # (Pa = N m^-2 = kg m^-1 s^-2)
        # p = 0.1 - 10 typical values 
        # T = 573 + n_sim * 100 # (K)
        temp = 600
        T = temp # (K)
        
        experimental_conditions = [sticking_coeff,partial_pressure,T,experiment]
    
# =============================================================================
#         Crystal structure
#         
# =============================================================================
        #id_material_COD = 5000216 # Cu
        id_material_Material_Project = "mp-30" # Cu
        crystal_size = (20,20,20) # (angstrom (Å))
        orientation = ['001','111']
        use_parallel = None

        # Create a config.json file with the API key -> To avoid uploading to Github
        with open('config.json') as config_file:
            config = json.load(config_file)
            api_key = config['api_key']
        
        mpr = MPRester(api_key)
        # Retrieve material data
        with MPRester(api_key) as mpr:
            # Retrieve material summary information
            material_summary = mpr.materials.summary.search(material_ids=[id_material_Material_Project])
            formula = material_summary[0].formula_pretty

            
        crystal_features = [id_material_Material_Project,crystal_size,orientation[1],api_key,use_parallel]
        
# =============================================================================
#             Superbasin parameters
#     
# =============================================================================
        n_search_superbasin = 3 # If the time step is very small during 10 steps, search for superbasin
        time_step_limits = 1e-8 # Time needed for efficient evolution of the system
        E_min = 0.6
        superbasin_parameters = [n_search_superbasin, time_step_limits,E_min]
# =============================================================================
#       Different surface Structures- fcc Metals
#       https://chem.libretexts.org/Bookshelves/Physical_and_Theoretical_Chemistry_Textbook_Maps/Surface_Science_(Nix)/01%3A_Structure_of_Solid_Surfaces/1.03%3A_Surface_Structures-_fcc_Metals
#       Activation energies
#       Nies, C. L., Natarajan, S. K., & Nolan, M. (2022). 
#       Control of the Cu morphology on Ru-passivated and Ru-doped TaN surfaces-promoting growth of 2D conducting copper for CMOS interconnects. 
#       Chemical Science, 13(3), 713–725. https://doi.org/10.1039/d1sc04708f
#           - Migrating upward/downward one layer - It seems is promoted by other atoms surrounding
#           - Migrating upward/downward two layers in one jump
# 
#       Jamnig, A., Sangiovanni, D. G., Abadias, G., & Sarakinos, K. (2019). 
#       Atomic-scale diffusion rates during growth of thin metal films on weakly-interacting substrates. 
#       Scientific Reports, 9(1). https://doi.org/10.1038/s41598-019-43107-8
#           - Migration of Cu on graphite - 0.05-0.13 eV
# 
#       Kondati Natarajan, S., Nies, C. L., & Nolan, M. (2019). 
#       Ru passivated and Ru doped ϵ-TaN surfaces as a combined barrier and liner material for copper interconnects: A first principles study. 
#       Journal of Materials Chemistry C, 7(26), 7959–7973. https://doi.org/10.1039/c8tc06118a
#           - TaN (111) - Activation energy for Cu migration - [0.85 - 1.26] (ev)
#           - Ru(0 0 1) - Activation energy for Cu migration - [0.07 - 0.11] (ev)
#           - 1ML Ru - Activation energy for Cu migration - [0.01, 0.21, 0.45, 0.37] (ev)
#           - 2ML Ru - Activation energy for Cu migration - [0.46, 0.44] (ev)
#           - Information about clustering two Cu atoms on TaN and Ru surfaces
# 
#       ACTIVATION ENERGIES - Cu
#       Kim, Sung Youb, In-Ho Lee, and Sukky Jun. 
#       "Transition-pathway models of atomic diffusion on fcc metal surfaces. I. Flat surfaces." 
#       Physical Review B 76, no. 24 (2007): 245407.
# 
#       Kim, Sung Youb, In-Ho Lee, and Sukky Jun. 
#       "Transition-pathway models of atomic diffusion on fcc metal surfaces. II. Stepped surfaces." 
#       Physical Review B 76, no. 24 (2007): 245408.
# =============================================================================
        select_dataset = 4   
        Act_E_dataset = ['TaN','Ru25','Ru50','homoepitaxial','template_upward']  
        
        
        # Retrieve the activation energies
        with open('activation_energies_set.json', 'r') as file:
            data = json.load(file)
            
        E_dataset = []
        for element in data['elements']:
            # Search the selected element we retrieved from Materials Project
            if element['name'] == formula:
                
                #Search the activation energies
                for key,activation_energies in element.items():
                    if 'activation_energies' in key and Act_E_dataset[select_dataset] in key:
                        # Select the dataset
                        for act_energy in activation_energies.values():
                            if isinstance(act_energy, (int, float)):
                                E_dataset.append(act_energy)
                        
        E_mig_sub = E_dataset[0] # (eV)
        E_mig_upward_subs_layer111 = E_dataset[1]
        E_mig_downward_layer111_subs = E_dataset[2]
        E_mig_upward_layer1_layer2_111 = E_dataset[3] + 0.1 * n_sim
        E_mig_downward_layer2_layer1_111 = E_dataset[4]
        E_mig_upward_subs_layer100 = E_dataset[5] 
        E_mig_downward_layer100_subs = E_dataset[6]
        E_mig_111_terrace_Cu = E_dataset[7]
        E_mig_100_terrace_Cu = E_dataset[8] + 0.1 * n_sim
        E_mig_edge_100 = E_dataset[9]
        E_mig_edge_111 = E_dataset[10]

        # =============================================================================
        #     Papanicolaou, N. 1, & Evangelakis, G. A. (n.d.). 
        #     COMPARISON OF DIFFUSION PROCESSES OF Cu AND Au ADA TOMS ON THE Cu(1l1) SURFACE BY MOLECULAR DYNAMICS.
        #     
        #     Mińkowski, Marcin, and Magdalena A. Załuska-Kotur. 
        #     "Diffusion of Cu adatoms and dimers on Cu (111) and Ag (111) surfaces." 
        #     Surface Science 642 (2015): 22-32. 10.1016/j.susc.2015.07.026
        # =============================================================================

        # Binding energy | Desorption energy: https://doi.org/10.1039/D1SC04708F
        binding_energy = E_dataset[-2] - 0.1 * n_sim

             
# =============================================================================
#     Böyükata, M., & Belchior, J. C. (2008). 
#     Structural and Energetic Analysis of Copper Clusters: MD Study of Cu n (n = 2-45). 
#     In J. Braz. Chem. Soc (Vol. 19, Issue 5).
#      - Clustering energy
# 
#     Kondati Natarajan, S., Nies, C. L., & Nolan, M. (2020). 
#     The role of Ru passivation and doping on the barrier and seed layer properties of Ru-modified TaN for copper interconnects. 
#     Journal of Chemical Physics, 152(14). https://doi.org/10.1063/5.0003852
# =============================================================================    
    # clustering_energy = -0.252
    #clustering_energy = -0.21
        clustering_energy = E_dataset[-1]
        E_clustering = [0,0,clustering_energy * 2,clustering_energy * 3,clustering_energy * 4,clustering_energy * 5,clustering_energy * 6,clustering_energy * 7,clustering_energy * 8,clustering_energy * 9,clustering_energy * 10,clustering_energy * 11,clustering_energy * 12,clustering_energy * 13] 


        Act_E_list = [E_mig_sub,
                      E_mig_upward_subs_layer111,E_mig_downward_layer111_subs,
                      E_mig_upward_layer1_layer2_111,E_mig_downward_layer2_layer1_111,
                      E_mig_upward_subs_layer100,E_mig_downward_layer100_subs,
                      E_mig_111_terrace_Cu,E_mig_100_terrace_Cu,
                      E_mig_edge_100,E_mig_edge_111,
                      binding_energy,E_clustering]
        


        filename = 'grid_crystal'
        System_state = initialize_grid_crystal(filename,crystal_features,experimental_conditions,Act_E_list, 
              ovito_file,superbasin_parameters,save_data)  
        

        # The minimum energy to select transition pathways to create a superbasin should be smaller
        # than the adsorption energy
        if superbasin_parameters[2] > System_state.Act_E_ad:  # Replace with your actual range
            raise ValueError("Minimum energy for superbasin is greater than adsorption energy.")
            import sys
            sys.exit(1)
            
        # Maximum probability per site for deposition to establish a timestep limits
        # The maximum timestep is that one that occupy X% of the site during the deposition process
        P_limits = 0.02
        System_state.limit_kmc_timestep(P_limits)
    
# =============================================================================
#     - test[0] - Normal deposition
#     - test[1] - Introduce a single particle in a determined site
#     - test[2] - Introduce and remove a single particle in a determined site 
#     - test[3] - Introduce two adjacent particles
#     - test[4] - Hexagonal seed - 7 particles in plane + 1 particle in plane
#     - test[5] - Hexagonal seed - 7 particles in plane and 1 on the top of the layer
#     - test[6] - 2 hexagonal seeds - 2 layers and one particle on the top 
#     - test[7] - 2 hexagonal seeds - 2 layers and one particle attach to the lateral
#     - test[8] - cluster
#     - test[9] - 3 Cu layers

# =============================================================================
        test_selected = 0
        test = [0,1,2,3,4,5,6,7,8,9]

        # Deposition process of chemical species
        if System_state.timestep_limits < float('inf'):
            System_state.deposition_specie(System_state.timestep_limits,rng,test[test_selected])
            System_state.track_time(System_state.timestep_limits) 
            System_state.add_time()
        else:
            System_state.deposition_specie(0,rng,test[test_selected])
            System_state.track_time(0) 
            System_state.add_time()
            
    elif experiment == 'annealing':
        
        path = r'/sfihome/samuel.delgado/Copper_deposition/Varying_substrate/annealing/TaN/T500/'
        filename = path + 'variables.pkl'
        
        # Open the file in binary mode
        with open(filename, 'rb') as file:
          
            # Call load method to deserialze
            myvar = pickle.load(file)
            
        System_state = myvar['System_state']
        
        temp = [300,500,800] #(K)
        
        System_state.temperature = temp[n_sim]
        System_state.experiment = experiment
        P_limits = 1
        System_state.limit_kmc_timestep(P_limits)
        System_state.time = 0
        System_state.list_time = []

    return System_state,rng,paths,Results

    # =============================================================================
    #     Initialize the crystal grid structure - nodes with empty spaces
    # =============================================================================    
def initialize_grid_crystal(filename,crystal_features,experimental_conditions,Act_E_list, 
    ovito_file,superbasin_parameters,save_data):
      
        # If grid_crystal exists: we loaded
        # Otherwise: we create it (very expensive for larger systems ~100 anstrongs)
        current_directory = Path(__file__).parent
        # Check for .dat and .pkl extensions       
        # Dynamically append extensions for checks
        dat_file = current_directory / filename
        dat_file_with_ext = dat_file.with_suffix('.dat')
        pkl_file_with_ext = dat_file.with_suffix('.pkl')
        
        if dat_file_with_ext.exists():
            print('Loading grid_crystal.dat')
            # Load from .dat
            dat_file = current_directory / f"{filename}"
            with shelve.open(dat_file) as my_shelf:
                grid_crystal = my_shelf.get(filename)
            
            System_state = Crystal_Lattice(crystal_features,experimental_conditions,Act_E_list,ovito_file,superbasin_parameters,grid_crystal)

        elif pkl_file_with_ext.exists():
            print('Loading grid_crystal.pkl')
            # Load from .pkl
            with open(pkl_file_with_ext, 'rb') as file:
                # Call load method to deserialze
                data = pickle.load(file)
            grid_crystal = data.get(filename)
            
            System_state = Crystal_Lattice(crystal_features,experimental_conditions,Act_E_list,ovito_file,superbasin_parameters,grid_crystal)

            
        else:
            # Create new grid_crystal
            System_state = Crystal_Lattice(crystal_features,experimental_conditions,Act_E_list,ovito_file,superbasin_parameters)
            
            # Save the newly created data
            if save_data: 
                save_variables(current_directory, {filename : System_state.grid_crystal}, filename)

        return System_state
        
        
def search_superbasin(System_state):
          
    # We need a deepcopy? System_state.sites_occupied will be modified on site
    # when calling Superbasin() and it will change the order of sites_occupied
    # sites_occupied = copy.deepcopy(System_state.sites_occupied)
    
    # This approach should be more efficient and memory-friendly
    sites_occupied = System_state.sites_occupied[:] 
    
    for idx in sites_occupied:
        for event in System_state.grid_crystal[idx].site_events:
            if (idx not in System_state.superbasin_dict) and (event[3] <= System_state.E_min):
                System_state.superbasin_dict.update({idx: Superbasin(idx, System_state, System_state.E_min,sites_occupied)})
                


def save_simulation(files_copy,dst,n_sim):
    
    # Create the simulation directory
    parent_dir = f'Sim_{n_sim}'
    sim_dir = dst / parent_dir
    sim_dir.mkdir(parents=True, exist_ok=True)  # Create parent directories if they don't exist
    
    # Define subdirectories
    program_directory = sim_dir / 'Program'
    data_directory = sim_dir / 'Crystal evolution'
    
    # Create directories
    program_directory.mkdir(parents=True, exist_ok=True)
    data_directory.mkdir(parents=True, exist_ok=True)
    
    # Return paths as a dictionary
    paths = {
        'data': data_directory,
        'program': program_directory,
        'results': sim_dir
    }
    
    # Copy the files
    current_directory = Path(__file__).parent  # Get the current directory of the script
    for file in files_copy:
        source_file = current_directory / file  # Path of the source file
        destination_file = paths['program'] / file  # Path for the destination file
        shutil.copyfile(source_file, destination_file)  # Copy the file
    
    # Create and return results object
    excel_filename = paths['results'] / 'Results.csv'  # Define the path to the results CSV file
    Results = SimulationResults(excel_filename)
        
    return paths, Results


def save_variables(paths,variables,filename):
    
    
    # Convert paths to Path object if it's a string (if it's not already)
    paths = Path(paths)  # Ensure paths is a Path object
    
    # Full file path
    file_path = paths / filename

    if platform.system() == 'Windows':  # When running on Windows
        with shelve.open(str(file_path), 'n') as my_shelf:
            for key, value in variables.items():
                my_shelf[key] = value

    elif platform.system() == 'Linux':  # When running on Linux
        filename += '.pkl'
        file_path = file_path.with_name(filename)  # Ensure the filename ends with .pkl

        # Open the file and use pickle.dump()
        with open(file_path, 'wb') as file:
            pickle.dump(variables, file)
    

class SimulationResults:
    def __init__(self, excel_filename):
        self.excel_filename = excel_filename
        # Initialize a CSV file with headers
        with open(excel_filename, 'w') as f:
            f.write('Time,Mass,Sites Occupation,Average Thickness,Terrace Area,std_terrace,max_terrace,RMS Roughness,Performance time\n')
    
    def measurements_crystal(self, time, mass_gained, sites_occupation, thickness, avg_terrace,std_terrace,max_terrace, surf_roughness_RMS,performance_time):
            # Append measurements to the CSV file
            with open(self.excel_filename, 'a') as f:
                f.write(f'{time},{mass_gained},{sites_occupation},{thickness},{avg_terrace},{std_terrace},{max_terrace},{surf_roughness_RMS},{performance_time}\n')