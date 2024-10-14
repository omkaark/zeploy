#!/bin/bash

python3 fuse_client.py /mnt/fuse phw &

sleep 5

python3 api.py