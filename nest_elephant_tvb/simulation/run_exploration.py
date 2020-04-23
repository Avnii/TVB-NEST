import datetime
import os
import nest
from nest_elephant_tvb.simulation.parameters_manager import generate_parameter,save_parameter
from nest_elephant_tvb.simulation.simulation_nest import simulate,config_mpi_record,simulate_mpi_co_simulation
from nest_elephant_tvb.simulation.simulation_zerlaut import simulate_tvb
import subprocess
import numpy as np

def run(results_path,parameter_default,dict_variable,begin,end):
    """
    Run one simulation, analyse the simulation and save this result in the database
    :param results_path: the folder where to save spikes
    :param parameter_default: parameters by default of the exploration
    :param dict_variable : dictionary with the variable change
    :param begin:  when start the recording simulation ( not take in count for tvb (start always to zeros )
    :param end: when end the recording simulation and the simulation
    :return: nothing
    """
    print('time: '+str(datetime.datetime.now())+' BEGIN SIMULATION \n')
    #create the folder for result is not exist
    newpath = os.path.join(os.getcwd(),results_path)
    # start to create the repertory for the simulation
    if nest.Rank() == 0:
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        if not os.path.exists(newpath+"/log"):
            os.makedirs(newpath+"/log")
        if not os.path.exists(newpath + '/tvb'):
            os.makedirs(newpath + '/tvb')
        else:
            try:
                os.remove(newpath + '/tvb/step_init.npy') # use it for synchronise all mpi the beginning
            except OSError:
                pass
    else:
        while not os.path.exists(newpath+'/tvb'): # use it for synchronise all nest thread
            pass

    # generate parameter for the  simulation
    parameters = generate_parameter(parameter_default,results_path,dict_variable)

    # parameter for the cosimulation and more
    param_co_simulation = parameters['param_co_simulation']

    save_parameter(parameters,results_path,begin,end)

    if param_co_simulation['co-simulation']:
        # First case : co-simulation
        id_proxy =  param_co_simulation['id_region_nest']
        time_synch =  param_co_simulation['synchronization']

        #initialise Nest and take information for the connection between all the mpi process
        spike_detector,spike_generator = config_mpi_record(results_path=results_path,begin=begin,end=end,
                                                           param_nest=parameters['param_nest'],param_topology=parameters['param_topology'],
                                                           param_connection=parameters['param_connection'],param_background=parameters['param_background'],
                                                           cosimulation=param_co_simulation)
        if nest.Rank() == 0:
            # create translator between Nest to TVB :
            # one by proxy/spikedetector

            # create all the repertory for the translation file (communication files of MPI)
            if not os.path.exists(newpath+"/spike_detector/"):
                        os.makedirs(newpath+"/spike_detector/")
            if not os.path.exists(newpath+"/send_to_tvb/"):
                os.makedirs(newpath+"/send_to_tvb/")


            for index,id_spike_detector in enumerate(spike_detector):
                dir_path = os.path.dirname(os.path.realpath(__file__))+"/file_translation/run_mpi_nest_to_tvb.sh"
                argv=[ dir_path,
                       results_path,
                       "/spike_detector/"+str(id_spike_detector.tolist()[0])+".txt",
                       "/send_to_tvb/"+str(id_proxy[index])+".txt",
                       ]
                subprocess.Popen(argv,
                                 #need to check if it's needed or not (doesn't work for me)
                                 stdin=None,stdout=None,stderr=None,close_fds=True, #close the link with parent process
                                 )

            # create translator between TVB to Nest:
            # one by proxy/id_region

            # create all the repertory for the translation file (communication files of MPI)
            if not os.path.exists(results_path+"/spike_generator/"):
                os.makedirs(newpath+"/spike_generator/")
            if not os.path.exists(results_path+"/receive_from_tvb/"):
                os.makedirs(newpath+"/receive_from_tvb/")

            for index,ids_spike_generator in enumerate(spike_generator):
                dir_path = os.path.dirname(os.path.realpath(__file__))+"/file_translation/run_mpi_tvb_to_nest.sh"
                argv=[ dir_path,
                       results_path+"/spike_generator/",
                       str(ids_spike_generator.tolist()[0]),
                       str(len(ids_spike_generator.tolist())),
                       "/../receive_from_tvb/"+str(id_proxy[index])+".txt",
                       ]
                subprocess.Popen(argv,
                                 #need to check if it's needed or not (doesn't work for me)
                                 stdin=None,stdout=None,stderr=None,close_fds=True, #close the link with parent process
                                 )
            #TODO correct synchronization : waiting until create most all file of config

            # Run TVB in co-simulation
            dir_path = os.path.dirname(os.path.realpath(__file__))+"/file_tvb/run_mpi_tvb.sh"
            argv=[
                dir_path,
                results_path
            ]
            subprocess.Popen(argv,
                             # need to check if it's needed or not (doesn't work for me)
                             stdin=None,stdout=None,stderr=None,close_fds=True, #close the link with parent process
                             )
        # Use the init file of TVB for waiting the configuration file for MPI communication are ready to use
        # and start the simulation at the same time
        while not os.path.exists(newpath+'/tvb/step_init.npy'):
             pass
        simulate_mpi_co_simulation(time_synch,end,newpath,param_co_simulation['level_log'])

    else:
        if param_co_simulation['nb_MPI_nest'] != 0:
            # Second case : Only nest simulation
            if param_co_simulation['record_MPI']:
                time_synch =  param_co_simulation['synchronization']
                #initialise Nest before the communication
                spike_detector, spike_generator = config_mpi_record(results_path=results_path, begin=begin, end=end,
                                                                    param_nest=parameters['param_nest'],
                                                                    param_topology=parameters['param_topology'],
                                                                    param_connection=parameters['param_connection'],
                                                                    param_background=parameters['param_background'],
                                                                    cosimulation=param_co_simulation)

                #create file for the foldder for the communication part
                if nest.Rank() == 0:
                    if not os.path.exists(results_path+'/spike_detector/'):
                        os.makedirs(results_path+'/spike_detector/')
                    if not os.path.exists(results_path + '/save/'):
                        os.makedirs(results_path + '/save/')
                else:
                    while not os.path.exists(results_path+'/save/'):
                        pass

                #TODO need to test and to finish this part
                for index,id_spike_detector in enumerate(spike_detector):
                    dir_path = os.path.dirname(os.path.realpath(__file__))+"/file_translation/run_mpi_nest_save.sh"
                    argv=[ dir_path,
                           results_path,
                           "/spike_detector/"+str(id_spike_detector.tolist()[0])+".txt",
                           results_path+"/save/"+str(id_spike_detector.tolist()[0]),
                           str(end)
                           ]
                    subprocess.Popen(argv,
                                 #need to check if it's needed or not (doesn't work for me)
                                 stdin=None,stdout=None,stderr=None,close_fds=True, #close the link with parent process
                                 )
                simulate_mpi_co_simulation(time_synch, end, newpath, param_co_simulation['level_log'])
            else:
                # just run nest with the configuration
                simulate(results_path=results_path, begin=begin, end=end,
                         param_nest=parameters['param_nest'], param_topology=parameters['param_topology'],
                         param_connection=parameters['param_connection'], param_background=parameters['param_background'])
        else:
            # Third case : Only tvb simulation
            simulate_tvb(results_path=results_path, begin=begin, end=end,
                 param_tvb=parameters['param_tvb'], param_zerlaut=parameters['param_zerlaut'],
                 param_nest=parameters['param_nest'], param_topology=parameters['param_topology'],
                 param_connection=parameters['param_connection'], param_background=parameters['param_background'])
    print('time: '+str(datetime.datetime.now())+' END SIMULATION \n')

def run_exploration_2D(path,parameter_default,dict_variables,begin,end):
    """

    :param path: for the result of the simulations
    :param parameter_default: the parameters by defaults of the simulations
    :param dict_variables: the variables and there range of value for the simulations
    :param begin: when start the recording simulation ( not take in count for tvb (start always to zeros )
    :param end: when end the recording simulation and the simulation
    :return:
    """
    name_variable_1,name_variable_2 = dict_variables.keys()
    print(path)
    for variable_1 in  dict_variables[name_variable_1]:
        for variable_2 in  dict_variables[name_variable_2]:
            # try:
            print('SIMULATION : '+name_variable_1+': '+str(variable_1)+' '+name_variable_2+': '+str(variable_2))
            results_path=path+'_'+name_variable_1+'_'+str(variable_1)+'_'+name_variable_2+'_'+str(variable_2)
            run(results_path,parameter_default,{name_variable_1:variable_1,name_variable_2:variable_2},begin,end)
            # except:
            #     sys.stderr.write('time: '+str(datetime.datetime.now())+' error: ERROR in simulation \n')
