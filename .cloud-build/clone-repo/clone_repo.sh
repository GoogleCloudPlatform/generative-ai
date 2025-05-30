#!/bin/bash

# Clones the generative-ai repository from GitHub.
git clone --depth 1 -b main https://github.com/GoogleCloudPlatform/generative-ai.git

# Changes the current directory to the cloned repository.
cd generative-ai || exit 1
