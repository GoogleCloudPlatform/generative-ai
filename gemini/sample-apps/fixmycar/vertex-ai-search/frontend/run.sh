#!/bin/bash

APP_PID=
stopRunningProcess() {
    # Based on https://linuxconfig.org/how-to-propagate-a-signal-to-child-processes-from-a-bash-script
    if test ! "${APP_PID}" = '' && ps -p ${APP_PID} >/dev/null; then
        echo >/proc/1/fd/1 "Stopping ${COMMAND_PATH} which is running with process ID ${APP_PID}"

        kill -TERM ${APP_PID}
        echo >/proc/1/fd/1 "Waiting for ${COMMAND_PATH} to process SIGTERM signal"

        wait ${APP_PID}
        echo >/proc/1/fd/1 "All processes have stopped running"
    else
        echo >/proc/1/fd/1 "${COMMAND_PATH} was not started when the signal was sent or it has already been stopped"
    fi
}

trap stopRunningProcess EXIT TERM

source ${VIRTUAL_ENV}/bin/activate

streamlit run ${HOME}/streamlit-backend.py &
APP_ID=${!}

wait ${APP_ID}
