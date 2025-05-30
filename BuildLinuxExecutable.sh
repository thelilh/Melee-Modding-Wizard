#!/bin/bash

clear

echo
echo "Are you sure you'd like to compile? (y/n)"
read -r confirmation
if [[ "$confirmation" != "y" ]]; then
    tput setaf 3  # Yellow
    echo
    echo "     Operation aborted. Press any key to exit."
    read -n 1 -s
    exit 1
fi

echo
echo "Preserve console display? (y/n)"
read -r useConsole

echo
python setup.py build "$useConsole"

exit_code=$?

echo
echo "Exit Code: $exit_code"
if [[ $exit_code -ne 0 ]]; then
    tput setaf 1  # Red
    echo
    echo "     An error has occurred. Press any key to exit."
    read -n 1 -s
    exit 1
fi

tput setaf 2  # Green
echo
echo "     Build complete! Press any key to exit."
read -n 1 -s
exit 0
