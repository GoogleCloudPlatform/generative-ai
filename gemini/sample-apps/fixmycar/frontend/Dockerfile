FROM python:3.12-slim

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 -ms /bin/bash appuser

# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir --upgrade \
    pip \
    virtualenv

USER appuser
WORKDIR /home/appuser

COPY . . 

ENV VIRTUAL_ENV=/home/appuser/venv
RUN virtualenv ${VIRTUAL_ENV}
RUN . ${VIRTUAL_ENV}/bin/activate && pip install --no-cache-dir -r ./requirements.txt

EXPOSE 8501

COPY run.sh /home/appuser
ENTRYPOINT ["./run.sh"]
