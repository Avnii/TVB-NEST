PACKAGE=${PWD}/../   # folder of co-simulation-tvb-nest
PYTHONLIB=${PWD}/../../../co_simulation/co-simulation-tvb-nest/venv/lib/python3.6/site-packages/ # folder with python library
REPERTORY_LIB_NEST=${PWD}/../../../co_simulation/co-simulation-tvb-nest/lib/nest_run/lib/python3.6/site-packages/ # folder with py-nest
export PYTHONPATH=$PYTHONPATH:$PACKAGE:$PYTHONLIB:$REPERTORY_LIB_NEST
export PATH=$PATH:${PWD}/../../../co_simulation/co-simulation-tvb-nest/venv/

for i in $(seq 3.4 0.1 3.5)
do
  python3 ./run_co-sim_time.py './test_file/time_syn/10000/' 0.0 1000.0 $i
done