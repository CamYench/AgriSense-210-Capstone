#!/bin/bash

for i in $(seq 2010 2023);
do
    sh pull_cs_tif.sh -y $i
done