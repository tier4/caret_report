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
docker image build -t caret/caret_report --build-arg CARET_VERSION="main" ./docker
```

## Run scripts to create report in Docker

```sh
cd CARET_report
# Settings: modify for your usage and environment
script_path=`pwd`
trace_data=~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss
work_dir=`pwd`/sample_autoware
report_store_dir="${work_dir}"/output
export trace_data_name=`basename ${trace_data}`
export start_strip=25
export end_strip=0
export component_list_json=component_list.json
export target_path_json=target_path.json
export max_node_depth=20
export timeout=120
export draw_all_message_flow=false
export report_store_mount_name=report_store_dir

# Run script
docker run -it --rm \
    --user $(id -u):$(id -g) \
    -v /etc/localtime:/etc/localtime:ro \
    -v ${script_path}:/CARET_report \
    -v ${trace_data}:/${trace_data_name} \
    -v ${work_dir}:/work \
    -v ${report_store_dir}:/report_store_dir \
    -e trace_data_name \
    -e start_strip \
    -e end_strip \
    -e component_list_json \
    -e target_path_json \
    -e max_node_depth \
    -e timeout \
    -e draw_all_message_flow \
    -e report_store_mount_name \
    caret/caret_report
```
