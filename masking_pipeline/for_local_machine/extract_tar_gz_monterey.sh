#!/bin/bash

SOURCE_DIR="./data/landsat_monterey"
DEST_DIR="./data/landsat_monterey_extracted"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Check if destination directory exists, create if it doesn't
if [ ! -d "$DEST_DIR" ]; then
    echo "Destination directory does not exist. Creating: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# Find and extract all .tar.gz files in the source directory
for file in "$SOURCE_DIR"/*.tar.gz; do
    if [ -f "$file" ]; then
        echo "Extracting $file to $DEST_DIR"
        tar -xzf "$file" -C "$DEST_DIR"
    else
        echo "No .tar.gz files found in $SOURCE_DIR"
    fi
done

echo "Extraction complete."
