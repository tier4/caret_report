FROM osrf/ros:galactic-desktop

# hadolint ignore=DL3008,DL3009
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        locales \
        && \
    apt-get clean
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

# Install requirements for CARET_report (Flask, selenium, firefox, geckodriver)
# hadolint ignore=DL3008,DL3009
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        unzip \
        wget \
        nano \
        firefox \
        python3-pip \
        && \
    apt-get clean

# hadolint ignore=DL3013,DL3042
RUN pip3 install Flask==2.1.0 selenium

# hadolint ignore=DL3047
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz && \
    tar xzvf geckodriver-v0.31.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/.

# Build CARET
# hadolint ignore=DL3003,SC2086
RUN git clone https://github.com/tier4/caret.git ros2_caret_ws && \
    cd ros2_caret_ws && \
    mkdir src && \
    vcs import src < caret.repos && \
    . /opt/ros/$ROS_DISTRO/setup.sh && \
    ./setup_caret.sh -c && \
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
