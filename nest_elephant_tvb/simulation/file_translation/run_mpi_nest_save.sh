#!/bin/bash
BASEDIR=$(dirname "$0")
mpirun -n 1 python $BASEDIR/nest_save_hist.py $1 $2 $3 $4 $5 $6 $7