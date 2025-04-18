#!/bin/sh

echo "Started with targets $* ..."

# Collect the sources needed for all targets:
sources=""
org_sources=""
for tormays_source in $*
do
    case $tormays_source in
    hsl)
        sources="${sources} hsl hki ylre_katuosat"
        ;;
    tram_infra)
        sources="${sources} hki osm helsinki_osm_lines ylre_katualueet"
        ;;
    tram_lines)
        sources="${sources} hki hsl ylre_katualueet"
        ;;
    liikennevaylat)
        sources="${sources} liikennevaylat central_business_area ylre_katuosat ylre_katualueet"
        ;;
    cycle_infra)
        sources="${sources} cycle_infra ylre_katualueet"
        ;;
    special_transport_routes)
        sources="${sources} special_transport_routes ylre_katualueet"
        ;;
    *)
        sources="${sources} $tormays_source"
        ;;
    esac
    org_sources="${org_sources} $tormays_source"
done
# De-duplicate the sources
sources=$(echo "$sources" | xargs -n1 | cat -n | sort -k2 | uniq -f1 | sort -k1 | cut -f2- |  xargs)

# Fetch the sources
echo "Fetching $sources ..."
sh /haitaton-gis/fetch_all.sh ${sources}
RESULT1="$?"
if [ "$RESULT1" != "0" ]; then
    echo -e "Fetching exit Code:" $RESULT1"\nFAILED to fetch data."
    exit 0
else
    sources=""
    for tormays_source in $*
    do
        # Process data
        case $tormays_source in
        liikennevaylat)
            sources="${sources} central_business_area ylre_katuosat ylre_katualueet $tormays_source"
            ;;
        cycle_infra)
            sources="${sources} ylre_katualueet $tormays_source"
            ;;
        hsl)
            sources="${sources} ylre_katuosat $tormays_source"
            ;;
        tram_infra)
            sources="${sources} ylre_katualueet $tormays_source"
            ;;
        tram_lines)
            sources="${sources} ylre_katualueet $tormays_source"
            ;;
        special_transport_routes)
            sources="${sources} ylre_katualueet $tormays_source"
            ;;
        *)
            sources="${sources} $tormays_source"
            ;;
        esac
    done
    sources=$(echo "$sources" | xargs -n1 | cat -n | sort -k2 | uniq -f1 | sort -k1 | cut -f2- |  xargs)
    echo "Processing ${sources} ..."
    /opt/venv/bin/python /haitaton-gis/process_data.py ${sources}
    RESULT2="$?"
    if [ "$RESULT2" != "0" ]; then
        echo -e "Processing exit Code:" $RESULT2"\nFAILED to process data."
    else
        # Validate and deploy data
        echo "Validating and deploying ${org_sources} ..."
        /opt/venv/bin/python /haitaton-gis-validate-deploy/validate_deploy_data.py ${org_sources}
        echo "Deployed ${org_sources}."
    fi
fi

echo "All targets deployed."
