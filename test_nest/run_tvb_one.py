from nest_elephant_tvb.simulation.run_exploration import run_exploration_2D
from nest_elephant_tvb.parameter import test_nest as parameter_test

# File for simulate with TVB only 1 region

def run_exploration(path,begin,end):
    parameter_test.param_co_simulation['nb_MPI_nest']=0
    parameter_test.param_nest_topology['nb_region']=1
    parameter_test.param_tvb_monitor['Raw']=True
    run_exploration_2D(path, parameter_test, {'b':[10.0,7.0,1.0], 'mean_I_ext': [0.0]}, begin, end)

if __name__ == "__main__":
    import sys
    if len(sys.argv)==4:
        run_exploration(sys.argv[1],float(sys.argv[2]),float(sys.argv[3]))
    elif len(sys.argv)==1:
        run_exploration( './test_file/test_3/', 0.0, 10000.0)
    else:
        print('missing argument')