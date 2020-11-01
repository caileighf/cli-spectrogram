# Command Line Interface Spectrogram
## cli-spectrogram Version 2.0
Simple python module that creates spectrograms from multi channel hydrophone array data in the command line.

![alt text](./images/version_2_default.png?raw=true)
![alt text](./images/version_2_clean.png?raw=true)
![alt text](./images/version_2_chan_1.png?raw=true)
![alt text](./images/version_2_hidden_legend.png?raw=true)
![alt text](./images/version_2_smaller.png?raw=true)![alt text](./images/version_2_smallest.png?raw=true)

### Purpose
Our group needed a lightweight, command line tool to look at spectrogram data coming from multi channel hydrophone arrays. 
This was designed for text ~~or binary~~ files created using the uldaq library. _Link to their source code [here](https://github.com/mccdaq/uldaq)._ 

### Example data file with two channels
The first column contains voltage readings from channel 1
The second column contains voltage readings from channel 2
_The data points are separated by ','_

```
0.001782, 0.002414
0.002414, 0.002414
0.001641, -0.001416
0.000060, -0.001416
-0.001416, -0.001416
-0.001908, -0.001100
-0.001100, -0.001100
```

### Installing cli-spectrogram
cli-spectrogram is meant to be a standalone tool.
```
$ pip install cli-spectrogram 
```

### Running cli-spectrogram
```
$ cli_spectrogram --sample-rate 38400 --file-length 1 --source ./examples
$ cli_spectrogram --help

usage: cli_spectrogram [-h] --sample-rate SAMPLE_RATE --file-length
                       FILE_LENGTH [-d] [--source SOURCE]
                       [--threshold-steps THRESHOLD_STEPS]
                       [-c {1,2,3,4,5,6,7,8}] [-t THRESHOLD_DB]
                       [-m MARKFREQ_HZ] [--nfft NFFT]

optional arguments:
  -h, --help            show this help message and exit
  --sample-rate SAMPLE_RATE
  --file-length FILE_LENGTH
                        in seconds
  -d, --debug           Show debugging print messsages
  --source SOURCE       Source directory with .txt files
  --threshold-steps THRESHOLD_STEPS
                        How many dB above and below threshold
  -c {1,2,3,4,5,6,7,8}, --display-channel {1,2,3,4,5,6,7,8}
  -t THRESHOLD_DB, --threshold-db THRESHOLD_DB
  -m MARKFREQ_HZ, --markfreq-hz MARKFREQ_HZ
  --nfft NFFT
```

### Different ways to launch cli-spectrogram
`$ cli_spectrogram --sample-rate 38400 --file-length 1 --source ./examples `

![alt text](./images/version_2_cmd_1.png?raw=true)

`$ cli_spectrogram --sample-rate 38400 --file-length 1 --source ./examples --markfreq-hz 2000 --threshold-db 80`

`$ cli_spectrogram --sample-rate 38400 --file-length 1 --source ./examples --markfreq-hz 2000 --threshold-db 80 --threshold-steps 20 `


### Navigating the user interface
__Adjust the Threshold (dB)__
* press the __'up arrow'__ to increase the threshold dB value by `THRESHOLD_STEPS`.
* press the __'down arrow'__ to decrease the threshold dB value by `THRESHOLD_STEPS`.

__Adjust the Mark Frequency__
* press the __'right arrow'__ to increase the mark frequency value by 200Hz.
* press the __'left arrow'__ to decrease the mark frequency value by 200Hz.

__Toggle Full Screen__ 
* press 'F' or 'f' to toggle full screen mode. In full screen mode there are more rows to the spectrogram but the menu and legend are hidden.

__Navigation Mode__ 
* press __'pg up'__ to display the _next_ file. (if you're at the most current file, __'pg up'__ won't do anything).
* press __'pg down'__ to display the _previous_ file. (if you're at the oldest file, __'pg down'__ won't do anything).
* press __'escape'__ to exit Navigation mode and return to streaming mode.
_Note: in Navigation mode, the spectrogram will be displayed for the current file and wait indefinitely. When Streaming mode is resumed, the spectrogram will be of the latest file, NOT where it left off._

__Ui Indicators__

Left column info | Center column legend | Right column help
------------ | ------------- | -------------
![](https://raw.githubusercontent.com/caileighf/cli-spectrogram/master/images/left_column.png "Left column info") | ![](https://raw.githubusercontent.com/caileighf/cli-spectrogram/master/images/center_column.png "Center column legend") | ![](https://raw.githubusercontent.com/caileighf/cli-spectrogram/master/images/right_column.png "Right column help")
Threshold (dB): Current threshold. | Mode: Streaming OR Navigation | up / down Keys to adjust the threshold
Sample Rate (Hz): Sample rate of collected data. | Color bar for spectrogram | left / right Keys to adjust the frequency marker
Viewing same file: if True, the spectrogram is being re-rendered from the same file. if False, then the spectrogram on display is a new render. | lower bound dB - upper bount dB | pg up/pg down view next file/view prev file
file: name of the file that is being rendered. | | ESC Exit navigation mode
time: time the file was created/last modified converted to local time | | F/f toggle full screen
refresh count: The heartbeat of the app. | |

__Errors and fail states__

* cli-spectrogram has a minimum console size. If you shrink the window past the minimum size, you'll be prompted to resize until the minimum dimensions are met.

![](https://raw.githubusercontent.com/caileighf/cli-spectrogram/master/images/too_small.png "Terminal too small")

* If there aren't any files in the log directory, you'll need to restart the cli-spectrogram and provide a directory to `--source` that has the text or ~~binary~~ files generated by the uldaq library; however, if files are added to the directory while in this state, cli-spectrogram will return to/start streaming.

![](https://raw.githubusercontent.com/caileighf/cli-spectrogram/master/images/no_files.png "No log files")



