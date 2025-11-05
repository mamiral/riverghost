# Environment Setup Guide: Riverghost Phase 1

**Target OS:** Ubuntu 24.04 LTS (fresh install, desktop or VM)
**Estimated Time:** 30 minutes

---

## 1. Install System Dependencies

Open a terminal and run:

```bash
sudo apt update
sudo apt install -y wine winetricks python3-pip pipenv libevdev2 uinput-modules-dkms x11-utils
```
> If you prefer the latest pipenv, use:
> `pip install --user pipenv`

**Note:** If you are using a non-Ubuntu or older Ubuntu version, package names or availability may differ. Consult your distribution's documentation or use Ubuntu 24.04 LTS for guaranteed compatibility.

---

## 2. Set Up Dedicated WINEPREFIX

Set up a dedicated Wine prefix for Riverghost to avoid conflicts with other Wine applications:

```bash
export WINEPREFIX=~/matija/riverghost/.wine-riverghost
wineboot
```
You must export `WINEPREFIX` in every terminal session before running Wine commands for Riverghost.

---

## 3. Set Up Wine and .NET

```bash
winetricks dotnet48 vcrun2022
```
*(Ensure `WINEPREFIX` is exported as above before running this command.)*

---

## 4. Install WPT Client

1. Download `WPTClient.exe` from the official source.
2. Run the installer:

```bash
wine ~/Downloads/WPTClient.exe
```
*(Ensure `WINEPREFIX` is exported as above before running this command.)*

---

## 5. Create Project Directory

```bash
mkdir -p ~/matija/riverghost
cd ~/matija/riverghost
```

---

## 6. Initialize Python Environment with pipenv

```bash
pipenv install --python 3.12
pipenv install ultralytics mss opencv-python easyocr evdev pypoker-eval ollama numpy asyncio schedule humanize noise label-studio
pipenv shell
```
*Pipenv is the required virtual environment manager for this project.*

---

## 7. Verify Installation

- **WPT Client:**
  Run `wine WPTClient.exe` (should launch the client).

- **Python Stack:**
  Run:
  ```bash
  pipenv run python -c "import mss; print('OK')"
  ```
  Output should be `OK`.

---

## 8. Troubleshooting

- If a package fails to install, rerun the command or check your internet connection.
- For Wine errors, ensure all dependencies are installed and try `winetricks` again.
- For permission errors with `uinput`, you may need to reboot or add your user to the `input` group:
  ```bash
  sudo usermod -aG input $USER
  sudo reboot
  ```
- For other issues, consult Ubuntu and Wine documentation.

---

## 9. Next Steps

Proceed to data acquisition and labeling as described in the project documentation.
