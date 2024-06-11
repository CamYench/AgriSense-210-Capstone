#!/bin/bash

for i in $(seq 2010 2023);
do
    sh pull_cs_tif_by_fips.sh -y $i -c 06053
done