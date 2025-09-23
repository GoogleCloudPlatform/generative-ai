#!/bin/bash

echo "Starting the Tau2 server..."
uvicorn src.tau2.api_service.simulation_service:app --host 127.0.0.1 --port 8001