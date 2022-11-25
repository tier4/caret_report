# cspell:ignore geckodriver, xzvf, libdbus, dfsg
FROM osrf/ros:humble-desktop

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        locales=2.35-0ubuntu3.1 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

# Install requirements for CARET_report (Flask, selenium, firefox, geckodriver, Helvetica alternative font)
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        unzip=6.0-26ubuntu3 \
        wget=1.21.2-2ubuntu1 \
        nano=6.2-1 \
        libdbus-glib-1-2=0.112-2build1 \
        python3-pip=22.0.2+dfsg-1 \
        fonts-urw-base35=20200910-1 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Firefox is not installed by apt in Ubuntu 22.04. installed libdbus-glib by apt above
RUN wget -nv "https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US" -O firefox.tar.bz2 && \
    tar jxf firefox.tar.bz2 && \
    mv firefox /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox

RUN pip3 install --no-cache-dir Flask==2.1.0 selenium==4.4.3 pandas==1.5.0

RUN wget -nv https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz && \
    tar xzvf geckodriver-v0.31.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/.

ADD "https://www.random.org/sequences/?min=1&max=52&col=1&format=plain&rnd=new" /dev/null
# Build CARET (Humble)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3003
RUN git clone https://github.com/tier4/caret.git ros2_caret_ws && \
    cd ros2_caret_ws && \
    git checkout v0.3.2 && \
    mkdir src && \
    vcs import src < caret.repos && \
    . /opt/ros/"$ROS_DISTRO"/setup.sh && \
    ./setup_caret.sh -c && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
