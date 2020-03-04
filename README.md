# cli-spectrogram
## Command Line Interface Spectrogram
Simple python module that creates spectrograms in the command line.

### Purpose
Our group needed a lightweight, command line tool to look at spectrogram data coming from multi channel hydrophone arrays. 
This was designed for text or binary files created using the uldaq library. _Link to their source code [here](https://github.com/mccdaq/uldaq)._ 

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
$ cli-spectrogram --sample-rate 38400 --file-length 1 --source ./examples
$ cli-spectrogram --help

usage: cli-spectrogram [-h] --sample-rate SAMPLE_RATE --file-length FILE_LENGTH
                       [-d] [--source SOURCE] [--threshold-steps THRESHOLD_STEPS]
                       [-c {1,2,3,4,5,6,7,8}] [-t THRESHOLD_DB] [-m MARKFREQ_HZ]
                       [--nfft NFFT]

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
`$ cli-spectrogram --sample-rate 38400 --file-length 1 --source ./examples `
![](/images/default.png?raw=true "Default view")

`$ cli-spectrogram --sample-rate 38400 --file-length 1 --source ./examples --markfreq-hz 2000 --threshold-db 80`
![](/images/basic.png?raw=true "With threshold passed and mark frequency passed")

`$ cli-spectrogram --sample-rate 38400 --file-length 1 --source ./examples --markfreq-hz 2000 --threshold-db 80 --threshold-steps 20 `
![](/images/thresh_tolerance.png?raw=true "With threshold passed and mark frequency passed and threshold steps")


### Navigating the user interface
__Adjust the Threshold (dB)__
* press the __'up arrow'__ to increase the threshold dB value by `THRESHOLD_STEPS`.
* press the __'down arrow'__ to decrease the threshold dB value by `THRESHOLD_STEPS`.

![](/images/low_threshold.png?raw=true "Low threshold")
![](/images/medium_threshold.png?raw=true "Medium threshold")
![](/images/high_threshold.png?raw=true "High threshold")

__Adjust the Mark Frequency__
* press the __'right arrow'__ to increase the mark frequency value by 200Hz.
* press the __'left arrow'__ to decrease the mark frequency value by 200Hz.

__Toggle Full Screen__ 
* press 'F' or 'f' to toggle full screen mode. In full screen mode there are more rows to the spectrogram but the menu and legend are hidden.

![](/images/full_screen.png?raw=true "Full screen toggled on")

__Navigation Mode__ 
* press __'pg up'__ to display the _next_ file. (if you're at the most current file, __'pg up'__ won't do anything).
* press __'pg down'__ to display the _previous_ file. (if you're at the oldest file, __'pg down'__ won't do anything).
* press __'escape'__ to exit Navigation mode and return to streaming mode.
_Note: in Navigation mode, the spectrogram will be displayed for the current file and wait indefinitely. When Streaming mode is resumed, the spectrogram will be of the latest file, NOT where it left off._

![](/images/navigation_mode.png?raw=true "Navigation mode")

__Ui Indicators__

Left column info | Center column legend | Right column help
------------ | ------------- | -------------
![](/images/left_column.png?raw=true "Left column info") | ![](/images/center_column.png?raw=true "Center column legend") | ![](/images/right_column.png?raw=true "Right column help")
Threshold (dB): Current threshold. | Mode: Streaming OR Navigation | up / down Keys to adjust the threshold
Sample Rate (Hz): Sample rate of collected data. | Color bar for spectrogram | left / right Keys to adjust the frequency marker
Viewing same file: if True, the spectrogram is being re-rendered from the same file. if False, then the spectrogram on display is a new render. | lower bound dB - upper bount dB | pg up/pg down view next file/view prev file
file: name of the file that is being rendered. | | ESC Exit navigation mode
time: time the file was created/last modified converted to local time | | F/f toggle full screen
refresh count: The heartbeat of the app. | |

__Errors and fail states__

* The console window has a minimum size. If you shrink the window too small, you'll be prompted to resize until the minimum dimensions are met.

![](/images/too_small.png?raw=true "Terminal too small")

* If there aren't any files in the log directory, you'll need to restart the cli-spectrogram and provide a directory to `--source` that has the text/binary files generated by the uldaq library.

![](/images/no_files.png?raw=true "No log files")



