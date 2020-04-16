import numpy as np
import os
from mpi4py import MPI
from threading import Thread, Lock
from nest_elephant_tvb.simulation.file_translation.science_tvb_to_nest import generate_data
import logging

lock_status=Lock() # locker for manage the transfer of data from thread

def send(path,level_log,first_id_spike_generator,nb_spike_generator,status_data,buffer_spike):
    '''
    the sending part of the translator
    :param path: folder which will contain the configuration fil
    :param first_id_spike_generator: the relative path which contains the txt file
    :param nb_spike_generator: the number of spike generator
    :param status_data: the status of the buffer (SHARED between thread)
    :param buffer_spike: the bufffer which contains the data (SHARED between thread)
    :return:
    '''
    # Configuration logger
    logger = logging.getLogger('tvb_to_nest_send')
    fh = logging.FileHandler(path+'/../log/tvb_to_nest_send.log')
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

    # Open the MPI port connection
    logger.info("Send : Waiting for port details")
    info = MPI.INFO_NULL
    root = 0
    port = MPI.Open_port(info)
    # Write file configuration of the port
    for i in range(nb_spike_generator):
        path_to_files = path + str(first_id_spike_generator+i) + ".txt"
        fport = open(path_to_files, "w+")
        fport.write(port)
        fport.close()
    # Wait until connection
    logger.info('Send : wait connection '+port)
    comm = MPI.COMM_WORLD.Accept(port, info, root)
    logger.info('Send : connect to '+port)

    status_ = MPI.Status()
    end=False
    source_sending = np.arange(0,comm.Get_remote_size(),1) # list of all the process for the communication
    while True:
        list_id=np.ones(nb_spike_generator) * -1 # list to link the spike train to the spike detector
        count_ending=0
        logger.info(" TVB to Nest: start to send " )
        while count_ending != len(source_sending) or list_id[-1] == -1:
            # Waiting for some processus ask for receive the spikes
            ids = np.empty(2, dtype='i')
            comm.Recv([ids,2, MPI.INT],source=MPI.ANY_SOURCE,tag=MPI.ANY_TAG,status=status_)
            if status_.Get_tag() == 0:
                # create or find the index of the spike generator
                if ids[0] in list_id:
                    index = np.where(ids[0]==list_id)[0][0]
                else:
                    index = np.where(list_id==-1)[0][0]
                    list_id[index]=ids[0]
                # wait until the data are ready to use
                while (not status_data[0]):
                    pass
                # Select the good spike train and send it
                data = buffer_spike[0][index]
                if index == 0:
                    logger.info(" TVB to Nest:"+str(data)+" " +str(index))
                shape = np.array(data.shape[0], dtype='i')
                # firstly send the size of the spikes train
                comm.Send([shape,MPI.INT],dest=status_.Get_source(),tag=ids[1])
                # secondly send the spikes train
                comm.Send([data, MPI.DOUBLE], dest=status_.Get_source(), tag=ids[1])
            elif  status_.Get_tag() == 1:
                # ending the update of the all the spike train from one processus
                count_ending += 1
            else:
                end = True
                break
        # Set lock back to False
        with lock_status:
            status_data[0] = False
        if end:
            break
    #TODO need to take in count the end of the simulation (add shared variable for close the simulation)
    logger.info("Send : ending" )
    comm.Disconnect()
    MPI.Close_port(port)
    for i in range(nb_spike_generator):
        path_to_files = path + str(first_id_spike_generator+i) + ".txt"
        os.remove(path_to_files)
    logger.info('Send : exit')

def receive(path,level_log,TVB_config,analyse,status_data,buffer_spike):
    '''
    the receiving part of the translator
    :param path: folder which will contain the configuration file
    :param TVB_config:
    :param nb_spike_generator:
    :param percentage_shared:
    :param status_data:
    :param buffer_spike:
    :return:
    '''
    # Configuration logger
    logger = logging.getLogger('tvb_to_nest_receive')
    fh = logging.FileHandler(path+'/../log/tvb_to_nest_receive.log')
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

    # Open the MPI port connection
    logger.info("Receive : Waiting for port details")
    info = MPI.INFO_NULL
    root = 0
    port = MPI.Open_port(info)
    # Write file configuration of the port
    path_to_files = path + TVB_config
    fport = open(path_to_files, "w+")
    fport.write(port)
    fport.close()
    logger.info('Receive : wait connection ' + port)
    comm = MPI.COMM_WORLD.Accept(port, info, root)
    logger.info('Receive : connect to ' + port)

    status_ = MPI.Status()
    source_sending = np.arange(0,comm.Get_remote_size(),1)# list of all the process for the commmunication
    while True:
        # Send to all the confirmation of the processus can send data
        requests=[]
        logger.info(" TVB to Nest: wait receive ")
        for source in source_sending:
            requests.append(comm.isend(True,dest=source,tag=0))
        MPI.Request.Waitall(requests)
        logger.info(" TVB to Nest: receive all")
        # get the starting and ending time of the simulation to translate
        time_step = np.empty(2, dtype='d')
        comm.Recv([time_step, 2, MPI.DOUBLE], source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status_)
        if status_.Get_tag() == 0:
            #  Get the size of the data
            size = np.empty(1, dtype='i')
            comm.Recv([size, 1, MPI.INT], source=status_.Get_source(), tag=0, status=status_)
            #  Get the rate
            rate = np.empty(size[0], dtype='d')
            comm.Recv([rate, size[0], MPI.DOUBLE], source=status_.Get_source(), tag=0, status=status_)
            spike_generate = analyse.generate_spike(0,time_step,rate)
            # Wait for lock to be set to False
            while (status_data[0]):
                pass
            # Set lock to true and put the data in the shared buffer
            buffer_spike[0] = spike_generate
            with lock_status:
                status_data[0] = True
        elif status_.Get_tag() == 1:
            with lock_status:
                status_data[0] = True
            break
    logger.info('Receive : ending')
    comm.Disconnect()
    MPI.Close_port(port)
    os.remove(path_to_files)
    logger.info('Receive : exit')

if __name__ == "__main__":
    import sys
    if len(sys.argv)==7:
        path_config = sys.argv[1]
        id_first_spike_detector = int(sys.argv[2])
        nb_spike_generator = int(sys.argv[3])
        TVB_config = sys.argv[4]
        percentage_shared = float(sys.argv[5])
        level_log = int(sys.argv[6])

        # variable for communication between thread
        status_data=[False]
        buffer_spike=[[]]

        # object for analysing data
        analyse = generate_data(percentage_shared,nb_spike_generator)

        # create the thread for receive and send data
        th_send = Thread(target=send, args=(path_config,level_log,id_first_spike_detector,nb_spike_generator,status_data,buffer_spike))
        th_receive = Thread(target=receive, args=(path_config,level_log,TVB_config,analyse,status_data,buffer_spike ))

        # start the threads
        th_receive.start()
        th_send.start()
        th_receive.join()
        th_send.join()
        MPI.Finalize()
    else:
        print('missing argument')

