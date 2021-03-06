#!/bin/bash

group=`id -g`
user=`id -u`
image="nuxion/labdev:latest"
echo Running with permissions: ${USER}

docker run --rm -it -v ${PWD}:/app --network=host --user ${user}:${group} ${image} bash 
