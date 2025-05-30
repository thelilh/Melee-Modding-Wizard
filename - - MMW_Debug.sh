#!/bin/bash

python "$(dirname "$0")/main.py" "$@"

# Exit if no problems, otherwise pause to see what happened
if [[ $? -ne 0 ]]; then
    tput setaf 1  # Red
    echo "Press any key to exit . . ."
    read -n 1 -s
fi
