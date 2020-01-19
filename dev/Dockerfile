ARG PY_VERSION

FROM $PY_VERSION

ENV GITHUB_USERNAME=qmbot

WORKDIR /workspace

COPY ./dev/requirements-dev.txt ./dev/requirements-dev.txt
COPY ./dev/requirements.txt ./dev/requirements.txt
COPY ./dev/install.sh ./dev/install.sh
RUN ./dev/install.sh
COPY . .
