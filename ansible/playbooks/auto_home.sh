#!/bin/bash
key="$1"
if [ -d "/nfs/home/$key" ] ; then
    echo ":/nfs/home/$key"
else
    echo ":/u/$key"
fi
