#!/bin/bash

# you can uncomment the second line to run in debug mode instead

python "$(dirname "$0")/main.py" test --boot "$@"
# python "$(dirname "$0")/main.py" test --debug --boot "$@"

# Exit if no problems, otherwise pause to see what happened
if [[ $? -ne 0 ]]; then
    tput setaf 1  # Red
    echo "Press any key to exit . . ."
    read -n 1 -s
fi
