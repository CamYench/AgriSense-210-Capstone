#!/bin/bash

# set target year mandatory option flag
while getopts "y:" flag;
do
    case "${flag}" in
        y) TARGET_YEAR=${OPTARG};;
        *) echo "Usage: $0 -y <year>"; exit 1;;
    esac
done

# throw error if target year is not included

if [ -z "$TARGET_YEAR" ]; then
    echo "Error: TARGET_YEAR is not set. Use the -y option to set the year."
    exit 1
fi


echo "Pulling Strawberry Data for year $TARGET_YEAR"

#Bounding Box Lower Left: -2274195.0 1785375.0
#Bounding Box Upper Right: -2196105.0 1879155.0

#set bound box variables
BBOX_LL_X=-2274195
BBOX_LL_Y=1785375
BBOX_UR_X=-2196105
BBOX_UR_Y=1879155

#set target crop variable - Strawberries: 221
TARGET_CROP=221

# initial call to get CDL file
CDL_URL=$(curl -s "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile?year=$TARGET_YEAR&bbox=$BBOX_LL_X,$BBOX_LL_Y,$BBOX_UR_X,$BBOX_UR_Y" | xmllint --xpath 'string(//*[local-name()="returnURL"])' -)


#generate TIF URL
TIF_URL=$(curl -s "https://nassgeodata.gmu.edu/axis2/services/CDLService/ExtractCDLByValues?file=$CDL_URL&values=$TARGET_CROP" | xmllint --xpath 'string(//*[local-name()="returnURL"])' -)



#one last curl using TIF URL to output to file in local directory

curl "$TIF_URL" --output "cropscape_strawberries_$TARGET_YEAR.tif"