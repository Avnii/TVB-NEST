#  Copyright 2020 Forschungszentrum Jülich GmbH and Aix-Marseille Université
# "Licensed to the Apache Software Foundation (ASF) under one or more contributor license agreements; and to You under the Apache License, Version 2.0. "

import numpy as np
from mpi4py import MPI

def simulate_nest_generator(path):
    '''
    simulate the spike generator of the translator for tvb to nest
    :param path: the path to the file for the connections
    :return:
    '''
    # Init connection
    print(path)
    print("Nest_Input :Waiting for port details");sys.stdout.flush()
    fport = open(path, "r")
    port=fport.readline()
    fport.close()
    print("Nest_Input :wait connection "+port);sys.stdout.flush()
    comm = MPI.COMM_WORLD.Connect(port)
    print('Nest_Input :connect to '+port);sys.stdout.flush()

    status_ = MPI.Status()
    ids=np.arange(0,10,1) # random id of spike detector
    print(ids);sys.stdout.flush()
    while(True):
        # Send start simulation
        comm.Send([np.array([True], dtype='b'), MPI.CXX_BOOL], dest=0, tag=0)
        for id in ids:
            # send ID of spike generator
            comm.Send([np.array(id,dtype='i'), MPI.INT], dest=0, tag=0)
            # receive the number of spikes for updating the spike detector
            size=np.empty(1,dtype='i')
            comm.Recv([size,1, MPI.INT], source=0, tag=id,status=status_)
            print("Nest_Input :receive size : " + str(size));sys.stdout.flush()
            # receive the spikes for updating the spike detector
            data = np.empty(size, dtype='d')
            comm.Recv([data,size, MPI.DOUBLE],source=0,tag=id,status=status_)
            print("Nest_Input :receive data : " + str(np.sum(data)));sys.stdout.flush()
            # printing value and exist
            if id == 0:
                print(id, data,np.sum(data));sys.stdout.flush()
        if np.any(data > 10000):
            break
        #send ending the the run of the simulation
        comm.Send([np.array([True], dtype='b'), MPI.CXX_BOOL], dest=0, tag=1)
    # closing the connection at this end
    print('Nest_Input : Disconnect');
    comm.Send([np.array([True], dtype='b'), MPI.CXX_BOOL], dest=0, tag=2)
    comm.Disconnect()
    MPI.Close_port(port)
    print('Nest_Input :exit');
    MPI.Finalize()

if __name__ == "__main__":
    import sys
    if len(sys.argv)==2:
        simulate_nest_generator(sys.argv[1])
    else:
        print('missing argument')

