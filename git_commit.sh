#!/bin/bash

pushd ~/pnt/drivers
git add .
git commit -m "update"
git push
cd ..
git submodule update --recursive --remote
git add .
popd
