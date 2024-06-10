#!/bin/bash

#target county must be 5 digit fips code
#fips code is combination of 2 digits representing the state, and 3 digits representing the county
#CA state code is 06

# set target year and county as mandatory option flags
while getopts "y:c:" flag;
do
    case "${flag}" in
        y) TARGET_YEAR=${OPTARG};;
        c) TARGET_COUNTY=${OPTARG};;
        *) echo "Usage: $0 -y <year> -c <county>"; exit 1;;
    esac
done

# throw error if target year is not included

if [ -z "$TARGET_YEAR" ]; then
    echo "Error: TARGET_YEAR is not set. Use the -y option to set the year."
    exit 1
fi

if [ -z "$TARGET_COUNTY" ]; then
    echo "Error: TARGET_COUNTY is not set. Use the -c option to set the county by FIPS code."
    exit 1
fi

echo "Pulling Strawberry Data - County: $TARGET_COUNTY Year: $TARGET_YEAR"



#set target crop variable - Strawberries: 221
TARGET_CROP=221

# initial call to get CDL file
CDL_URL=$(curl -s "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile?year=$TARGET_YEAR&fips=$TARGET_COUNTY" | xmllint --xpath 'string(//*[local-name()="returnURL"])' -)


#generate TIF URL
TIF_URL=$(curl -s "https://nassgeodata.gmu.edu/axis2/services/CDLService/ExtractCDLByValues?file=$CDL_URL&values=$TARGET_CROP" | xmllint --xpath 'string(//*[local-name()="returnURL"])' -)



#one last curl using TIF URL to output to file in local directory


curl "$TIF_URL" --output "cropscape-strawberries-$TARGET_COUNTY-$TARGET_YEAR.tif"