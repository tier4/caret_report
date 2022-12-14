# Use in Docker

## General setup process for Docker

- <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker>

```sh
# Retrieved from the above document
curl https://get.docker.com | sh && sudo systemctl --now enable docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
sudo docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi

# Permission setting
sudo usermod -aG docker $USER
sudo chgrp docker /var/run/docker.sock
sudo reboot yes
```

## Create CARET_report Docker image

```sh
cd CARET_report
docker image build -t caret/caret_report ./docker
```

## Run scripts to create report in Docker

```sh
cd CARET_report
# Settings: modify for your usage and environment
export script_path=`pwd`/report
export trace_data=~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss
export work_dir=`pwd`/sample_autoware
export component_list_json=component_list.json
export target_path_json=target_path.json

export start_time=20
export duration_time=9999
export max_node_depth=2
export draw_all_message_flow=false

# Run script
docker run -it --rm \
    -v ${script_path}:/CARET_report \
    -v ${trace_data}:/trace_data \
    -v ${work_dir}:/work \
    -e start_time \
    -e duration_time \
    -e max_node_depth \
    -e draw_all_message_flow \
    -e component_list_json \
    -e target_path_json \
    -v /etc/localtime:/etc/localtime:ro caret/caret_report
```
