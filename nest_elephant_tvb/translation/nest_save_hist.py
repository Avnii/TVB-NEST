#  Copyright 2020 Forschungszentrum Jülich GmbH and Aix-Marseille Université
# "Licensed to the Apache Software Foundation (ASF) under one or more contributor license agreements; and to You under the Apache License, Version 2.0. "

import numpy as np
import os
from mpi4py import MPI
from threading import Thread
from nest_elephant_tvb.translation.nest_to_tvb import receive,store_data,lock_status,logging

def save(path,level_log,nb_step,step_save,status_data,buffer):
    '''
    WARNING never ending
    :param path:  folder which will contain the configuration file
    :param level_log : the level for the logger
    :param nb_step : number of time for saving data
    :param step_save : number of integration step to save in same time
    :param status_data: the status of the buffer (SHARED between thread)
    :param buffer: the buffer which contains the data (SHARED between thread)
    :return:
    '''
    # Configuration logger
    logger = logging.getLogger('nest_save')
    fh = logging.FileHandler(path+'/../../log/nest_save.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if level_log == 0:
        fh.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    elif  level_log == 1:
        fh.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
    elif  level_log == 2:
        fh.setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)
    elif  level_log == 3:
        fh.setLevel(logging.ERROR)
        logger.setLevel(logging.ERROR)
    elif  level_log == 4:
        fh.setLevel(logging.CRITICAL)
        logger.setLevel(logging.CRITICAL)

    # initialisation variable
    buffer_save = None
    count=0
    while count<nb_step:
        logger.info("Nest save : save "+str(count))
        # send the rate when there ready
        while(not status_data[0]):
            pass
        if buffer_save is None:
            logger.info("buffer initialise buffer : "+str(count))
            buffer_save = buffer[0]
        elif count % step_save == 0:
            logger.info("buffer save buffer : "+str(count))
            buffer_save = np.concatenate((buffer_save,buffer[0]))
            np.save(path+"_"+str(count)+".npy",buffer_save)
            buffer_save = None
        else:
            logger.info("fill the buffer : "+str(count))
            buffer_save = np.concatenate((buffer_save,buffer[0]))
        with lock_status:
            status_data[0]=False
        count+=1
    logger.info('Save : ending');sys.stdout.flush()
    if buffer_save is not None:
        np.save(path + str(count) + ".npy", buffer_save)
    return


if __name__ == "__main__":
    import sys
    if len(sys.argv)==5:
        path_folder_config = sys.argv[1]
        file_spike_detector = sys.argv[2]
        path_folder_save = sys.argv[3]
        end = float(sys.argv[4])

        # parameters for the module
        sys.path.append(path_folder_config)
        from parameter import param_record_MPI as param
        sys.path.remove(path_folder_config)
        time_synch = param['synch']
        nb_step = np.ceil(end/time_synch)
        step_save = param['save_step']
        level_log = param['level_log']

        # variable for communication between thread
        status_data=[False] # status of the buffer
        buffer=[np.array([])]

        # object for analysing data
        store=store_data(path_folder_config,param)

        ############
        # Open the MPI port connection for receiver
        info = MPI.INFO_NULL
        root=0

        port_receive = MPI.Open_port(info)
        # Write file configuration of the port
        path_to_files = path_folder_config + file_spike_detector
        path_to_files_temp = path_to_files + ".temp"
        fport = open(path_to_files_temp, "w+")
        fport.write(port_receive)
        fport.close()
        # rename forces that when the file is there it also contains the port
        os.rename(path_to_files_temp, path_to_files)  # Todo: fragile when temp dir is not cleared out.
        # Wait until connection
        comm_receiver = MPI.COMM_WORLD.Accept(port_receive, info, root)
        #########################

        # create the thread for receive and send data
        th_receive = Thread(target=receive,
                            args=(path_folder_config, level_log, file_spike_detector, store, status_data, buffer, comm_receiver))
        th_save = Thread(target=save, args=(path_folder_save,level_log,nb_step,step_save,status_data,buffer))

        # start the threads
        th_receive.start()
        th_save.start()
        th_receive.join()
        th_save.join()
        comm_receiver.Disconnect()
        MPI.Close_port(port_receive)
        MPI.Finalize()
    else:
        print('missing argument')