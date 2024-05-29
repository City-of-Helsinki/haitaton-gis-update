#!/bin/sh

for o in $*
do
    echo "Fetching $o ..."
    sh /haitaton-gis/fetch_data.sh $o
done
