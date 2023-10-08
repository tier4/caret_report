# cspell:ignore geckodriver, xzvf, libdbus, dfsg
FROM osrf/ros:humble-desktop

ARG CARET_VERSION="main"

# Add user and group: start
ENV USER_NAME=user
RUN echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/${USER_NAME}
RUN chmod u+s /usr/sbin/useradd \
    && chmod u+s /usr/sbin/groupadd
# Add user and group: end

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        locales \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

# Install requirements for CARET_report (Flask, selenium, firefox, geckodriver, Helvetica alternative font)
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        unzip \
        wget \
        nano \
        python3-pip \
        fonts-urw-base35=20200910-1 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir Flask==2.1.0 bokeh==2.4.1 pandas-bokeh bottleneck anytree
RUN pip3 install --no-cache-dir werkzeug==2.3.7  # workaround (https://github.com/Azure-Samples/azure-search-openai-demo/issues/694)

# Build CARET (Humble)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3003
RUN git clone https://github.com/tier4/caret.git ros2_caret_ws && \
    cd ros2_caret_ws && \
    git checkout $CARET_VERSION && \
    mkdir src && \
    vcs import src < caret.repos && \
    . /opt/ros/"$ROS_DISTRO"/setup.sh && \
    ./setup_caret.sh -c && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
