# Build notes

Problems we hit during the build and what we changed.

## SD card corruption

The Pi stopped booting: a solid red light, a few green flickers, then nothing. Windows reported errors on the card and repaired them. The likely cause was repeated unclean power-offs, which are routine on a battery-powered robot. We reflashed the card and restored the code from a backup. We now shut down with `sudo poweroff` and wait for the green LED to stay dark before cutting power. A physical shutdown button (`dtoverlay=gpio-shutdown`) and a better-quality card are planned.

## Interrupted system update

An update was interrupted partway, which left dpkg half-configured. Each repair attempt restarted the remote-access service and killed our shell mid-command. Running the repair as a detached systemd unit (`systemd-run dpkg --configure -a`) let it finish.

## Lost model weights

The original `best.pt` was deleted, and the only surviving notebook held just the download cell. Colab's revision history still contained the training script, so we retrained with the same settings (60 epochs, 640 px, batch 16). The script's label lookup assumed labels sat next to their images, which was wrong for this dataset, so we matched images and labels by filename. The weights are now stored on a GitHub release and in Drive.

## Ultrasonic crosstalk and noise

Reading three sensors back to back produced false readings. We poll them one at a time with a 40 ms gap, take the median of three samples per reading, and report the median of the last six readings. A sensor shows "clear" until at least four of them are valid.

## Detection speed

YOLOv8n on the Pi 4B's CPU runs at about 2.4 FPS at 416 px. We moved detection into its own thread so driving and obstacle avoidance do not wait for the model, and the robot acts on the last detection for up to 1.4 seconds.

## Left and right labeling

Our hand-drawn pin map is labeled as seen facing the robot, so its left and right are mirrored relative to the robot's own sides. The code uses the robot's own sides. Pins 32 and 33 drive the robot's left wheels, which the drawing calls the right-side driver. We kept both conventions and documented the mapping in `wiring.md` rather than renaming pins in working code.
