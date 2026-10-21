#!/bin/sh

failed=""
for o in $*
do
    echo "Fetching $o ..."
    sh /haitaton-gis/fetch_data.sh $o || failed="${failed} $o"
done

if [ -n "$failed" ]; then
    echo "FAILED to fetch:${failed}"
    exit 1
fi
