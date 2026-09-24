#!/usr/bin/env bash

for ((attempt=0; attempt<60; attempt++)); do
    if [[ "$(timedatectl show --property=NTPSynchronized --value 2>/dev/null)" == yes ]]; then
        exit 0
    fi
    sleep 1
done
