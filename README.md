[![Test with Autoware](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml/badge.svg)](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml)

# Report creation scripts for CARET

- [./report](./report)
  - create general analysis report
- [./validation](./validation)
  - create validation report

## Sample

- [sample report page](https://tier4.github.io/CARET_report/)
- Please refer to [sample_autoware](./sample_autoware) to find sample settings and a full explanation of how to analyze Autoware with CARET

## Requirements

- Ubuntu
  - Ubuntu 20.04
    - ROS2 Galactic
    - [CARET](https://github.com/tier4/caret) ( Use [this branch](https://github.com/tier4/caret/tree/galactic) )
  - Ubuntu 22.04
    - ROS2 Humble
    - [CARET](https://github.com/tier4/caret) ( Use main/latest )
- The following software is also needed

```sh
# Flask 2.1.0 (need to specify version) is required to create html report pages
pip3 install Flask==2.1.0

# Firefox, selenium and geckodriver are required to generate graph image files
# sudo apt install -y firefox    # Ubuntu 20.04 only
pip3 install selenium
wget https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz
tar xzvf geckodriver-v0.31.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
```

## FAQ and Troubleshooting

### Process is stuck or PC freezes/crashes

- It uses lots of memory
  - 64GB or more is recommended
  - In case crash happens due to memory shortage, increase swap space

### Graph files (png files) are not created or Report creation script is stuck

- Please make sure Firefox is installed properly
- In Ubuntu 22.04, please consider to install Firefox from tar rather than Firefox installed by snap

  ```sh
  wget --content-disposition "https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US"
  tar jxf `ls firefox*`
  sudo mv firefox /opt
  sudo ln -s /opt/firefox/firefox /usr/local/bin/firefox
  sudo apt install -y libdbus-glib-1-2
  ```

  - Also, try the following commands before running the report creation script

  ```sh
  mkdir $HOME/tmp
  export TMPDIR=$HOME/tmp
  chmod 777 $TMPDIR
  ```

- Or, please consider to use Chromium rather than Firefox to create graph image files using either of the following commands. If using `pip` command to install, you may need to specify the version which is the same as your chrome browser (e.g. Google Chrome)

  ```sh
  sudo apt install chromium-chromedriver
  pip3 install chromedriver-binary
  ```

### How to run regression test

```sh
# cd to this repo cloned
sh ./report/compare/makereport_and_compare.sh
```
