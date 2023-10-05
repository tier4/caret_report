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
        libdbus-glib-1-2 \
        python3-pip \
        fonts-urw-base35=20200910-1 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Firefox is not installed by apt in Ubuntu 22.04. installed libdbus-glib by apt above
RUN wget -nv "https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US" -O firefox.tar.bz2 && \
    tar jxf firefox.tar.bz2 && \
    mv firefox /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox

RUN pip3 install --no-cache-dir Flask==2.1.0 selenium==4.4.3 pandas==1.5.0 bokeh==2.4.1 pandas-bokeh==0.5.5
RUN pip3 install --no-cache-dir werkzeug==2.3.7  # workaround (https://github.com/Azure-Samples/azure-search-openai-demo/issues/694)

RUN wget -nv https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz && \
    tar xzvf geckodriver-v0.31.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/.

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
