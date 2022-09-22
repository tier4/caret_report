# cspell:ignore geckodriver, xzvf
FROM osrf/ros:galactic-desktop

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        locales=2.31-0ubuntu9.9 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

# Install requirements for CARET_report (Flask, selenium, firefox, geckodriver, Helvetica alternative font)
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        unzip=6.0-25ubuntu1 \
        wget=1.20.3-1ubuntu2 \
        nano=4.8-1ubuntu1 \
        firefox=104.0+build3-0ubuntu0.20.04.1 \
        python3-pip=20.0.2-5ubuntu1.6 \
        fonts-urw-base35=20170801.1-3 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir Flask==2.1.0 selenium==4.4.3 pandas==1.4.4

RUN wget -nv https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz && \
    tar xzvf geckodriver-v0.31.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/.

ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" /dev/null
# Build CARET (Galactic)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3003
RUN git clone https://github.com/tier4/caret.git ros2_caret_ws && \
    cd ros2_caret_ws && \
    git checkout d4b410ee4ee9c6a14d3a01fc178020b0e8d6020f && \
    grep -v lttng-modules-dkms < ansible/roles/lttng/tasks/main.yml > ansible/roles/lttng/tasks/main_.yml && \
    mv ansible/roles/lttng/tasks/main_.yml ansible/roles/lttng/tasks/main.yml && \
    mkdir src && \
    vcs import src < caret.repos && \
    . /opt/ros/"$ROS_DISTRO"/setup.sh && \
    ./setup_caret.sh -c && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Downgrade pandas
RUN pip3 install --no-cache-dir pandas==1.4.4

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
