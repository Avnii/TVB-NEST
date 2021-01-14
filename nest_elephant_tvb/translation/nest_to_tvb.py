#  Copyright 2020 Forschungszentrum Jülich GmbH and Aix-Marseille Université
# "Licensed to the Apache Software Foundation (ASF) under one or more contributor license agreements; and to You under the Apache License, Version 2.0. "

import numpy as np
import os
import json
import time
from mpi4py import MPI
from threading import Thread, Lock
import logging
from nest_elephant_tvb.translation.science_nest_to_tvb import store_data,analyse_data


lock_status=Lock() # locker for manage the transfer of data from thread

def receive(logger,store,status_data,buffer, comm):
    '''
    the receive part of the translator
    :param logger : logger fro the thread
    :param store : object for store the data before analysis
    :param status_data: the status of the buffer (SHARED between thread)
    :param buffer: the buffer which contains the data (SHARED between thread)
    :return:
    '''
    # initialise variables for the loop
    status_ = MPI.Status() # status of the different message
    source_sending = np.arange(0,comm.Get_remote_size(),1) # list of all the process for the commmunication
    check = np.empty(1,dtype='b')
    count=0
    while True: # FAT END POINT
        # send the confirmation of the process can send data
        logger.info(" Nest to TVB : wait all")
        for source in source_sending:
            comm.Recv([check, 1, MPI.CXX_BOOL], source=source, tag=MPI.ANY_TAG, status=status_)

        if status_.Get_tag() == 0:
            logger.info(" Nest to TVB : start to receive")
            #  Get the data/ spike
            for source in source_sending:
                comm.Send([np.array(True,dtype='b'),MPI.BOOL],dest=source,tag=0)
                shape = np.empty(1, dtype='i')
                comm.Recv([shape, 1, MPI.INT], source=source, tag=0, status=status_)
                data = np.empty(shape[0], dtype='d')
                comm.Recv([data, shape[0], MPI.DOUBLE], source=source, tag=0, status=status_)
                store.add_spikes(count,data)
            while status_data[0] != 1 and status_data[0] != 2: # FAT END POINT
                time.sleep(0.001)
                pass
            # wait until the data can be send to the sender thread
            # Set lock to true and put the data in the shared buffer
            buffer[0] = store.return_data()
            with lock_status: # FAT END POINT
                if status_data[0] != 2:
                    status_data[0] = 0
        elif status_.Get_tag() == 1:
            logger.info("Nest to TVB : receive end " + str(count))
            count += 1
        elif status_.Get_tag() == 2:
            with lock_status:
                status_data[0] = 2
            logger.info("end simulation")
            break
        else:
            raise Exception("bad mpi tag"+str(status_.Get_tag()))
    logger.info('communication disconnect')
    comm.Disconnect()
    logger.info('end thread')
    return


def send(logger,analyse,status_data,buffer, comm):
    '''
    the sending part of the translator
    :param logger: logger fro the thread
    :param analyse ; analyse object to transform spikes to state variable
    :param status_data: the status of the buffer (SHARED between thread)
    :param buffer: the buffer which contains the data (SHARED between thread)
    :return:
    '''
    count=0
    status_ = MPI.Status()
    while True: # FAT END POINT
        # wait until the translator accept the connections
        accept = False
        logger.info("Nest to TVB : wait to send " )
        while not accept:
            req = comm.irecv(source=MPI.ANY_SOURCE,tag=MPI.ANY_TAG)
            accept = req.wait(status_)
        logger.info(" Nest to TVB : send data status : " +str(status_.Get_tag()))
        if status_.Get_tag() == 0:
            # send the rate when there ready
            while status_data[0] != 0: # FAT END POINT
                time.sleep(0.001)
                pass
            times,data=analyse.analyse(count,buffer[0])
            with lock_status:
                if status_data[0] != 2:
                    status_data[0] = 1
            logger.info("Nest to TVB : send data :"+str(np.sum(data)) )
            # time of stating and ending step
            comm.Send([times, MPI.DOUBLE], dest=status_.Get_source(), tag=0)
            # send the size of the rate
            size = np.array(int(data.shape[0]),dtype='i')
            comm.Send([size,MPI.INT], dest=status_.Get_source(), tag=0)
            # send the rates
            comm.Send([data,MPI.DOUBLE], dest=status_.Get_source(), tag=0)
        elif status_.Get_tag() == 1:
            # disconnect when everything is ending
            with lock_status:
                status_data[0] = 2
            break
        else:
            raise Exception("bad mpi tag"+str(status_.Get_tag()))
        count+=1
    logger.info('communication disconnect')
    comm.Disconnect()
    logger.info('end thread')
    return


def create_logger(path,name, log_level):
    # Configure logger
    logger = logging.getLogger(name)
    fh = logging.FileHandler(path+'/log/'+name+'.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if log_level == 0:
        fh.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    elif  log_level == 1:
        fh.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
    elif  log_level == 2:
        fh.setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)
    elif  log_level == 3:
        fh.setLevel(logging.ERROR)
        logger.setLevel(logging.ERROR)
    elif  log_level == 4:
        fh.setLevel(logging.CRITICAL)
        logger.setLevel(logging.CRITICAL)

    return logger


if __name__ == "__main__":
    import sys

    if len(sys.argv)!=4:
        print('incorrect number of arguments')
        exit(1)

    path = sys.argv[1]
    file_spike_detector = sys.argv[2]
    TVB_recev_file = sys.argv[3]

    # take the parameters and instantiate objects for analysing data
    with open(path+'/parameter.json') as f:
        parameters = json.load(f)
    param = parameters['param_TR_nest_to_tvb']
    store = store_data(path+'/log/',param)
    analyse = analyse_data(path+'/log/',param)
    # variable for communication between thread
    status_data=[0] # status of the buffer
    initialisation =np.load(param['init']) # initialisation value
    buffer=[initialisation] # buffer of the rate to send it
    
    ############ NEW Code: old logging code copied here for better overview
    level_log = param['level_log']
    id_spike_detector = os.path.splitext(os.path.basename(path+file_spike_detector))[0]
    logger_master = create_logger(path, 'nest_to_tvb_master'+str(id_spike_detector), level_log)
    logger_receive = create_logger(path, 'nest_to_tvb_receive'+str(id_spike_detector), level_log)
    logger_send = create_logger(path, 'nest_to_tvb_send'+str(id_spike_detector), level_log)
    ############# NEW Code end
    
    ############ NEW Code: FAT END POINT for MPI and new connections
    ### contains all MPI connection stuff for proper encapsulation
    ### TODO: make this a proper interface
    import nest_elephant_tvb.translation.FatEndPoint as FEP
    
    path_to_files_receive = path + file_spike_detector
    path_to_files_send = path + TVB_recev_file
    comm_receiver, port_receive, comm_sender, port_send = FEP.make_connections(path_to_files_receive, path_to_files_send, logger_master)
    ############# NEW Code end
    
    
    
    ############ NEW Code: removed threads, used MPI ranks...
    # create the thread for receive and send data
    th_receive = Thread(target=receive, args=(logger_receive,store,status_data,buffer, comm_receiver))
    th_send = Thread(target=send, args=(logger_send,analyse,status_data,buffer, comm_sender))

    # start the threads
    # FAT END POINT
    logger_master.info('Start thread')
    th_receive.start()
    th_send.start()
    th_receive.join()
    th_send.join()
    logger_master.info('thread join')
    ############ NEW Code end
    
    ############ NEW Code: FAT END POINT for MPI and new connections
    ### contains all MPI connection stuff for proper encapsulation
    ### TODO: make this a proper interface
    FEP.close_and_finalize(port_send, port_receive,logger_master)
    ############# NEW Code end

    
    logger_master.info('clean file')
    os.remove(path_to_files_receive)
    os.remove(path_to_files_send)
    logger_master.info('end')
