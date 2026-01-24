#!/bin/bash

for item in $(seq 2801 3001); do
    wget "https://www.gutenberg.org/cache/epub/${item}/pg${item}.txt"
done
