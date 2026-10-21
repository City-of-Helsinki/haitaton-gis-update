#!/bin/sh

failed=""
for o in $*
do
    /opt/venv/bin/python /haitaton-gis-validate-deploy/validate_deploy_data.py $o || failed="${failed} $o"
done

if [ -n "$failed" ]; then
    echo "FAILED to validate or deploy:${failed}"
    exit 1
fi
