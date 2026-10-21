#!/bin/sh

failed=""
for o in $*
do
    /opt/venv/bin/python /haitaton-gis/process_data.py $o || failed="${failed} $o"
done

if [ -n "$failed" ]; then
    echo "FAILED to process:${failed}"
    exit 1
fi
