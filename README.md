# spinalSynth_MIDI_SW

A lightweight, real-time Python bridge that connects a physical USB MIDI controller or virtual DAW MIDI port to the `spinalSynth` hardware synthesizer over UART.

It captures MIDI note and control change (CC) events, converts them to cycle-accurate synth parameters, and streams them atomically over serial.

---

## Key Features

* **Glitch-Free Frequency Sweeps**: Implements the multi-byte atomic staging protocol (`FREQ_LOW` -> `FREQ_MID` -> `FREQ_HIGH` trigger) to ensure smooth frequency sweeps.
* **Parameter Modulation**: Maps MIDI CC knobs directly to hardware parameters (e.g., volume adjustments, PWM duty cycle).

---

## Hardware UART Protocol

Commands are structured as 3-byte packets: `[0x01] [Address] [Data]`.

| Address | Parameter | Description | Staging Type |
|---|---|---|---|
| `0x00` | `FREQ_LOW` | Frequency Tuning Word Bits [7:0] | Staged (Shadow) |
| `0x01` | `FREQ_MID` | Frequency Tuning Word Bits [15:8] | Staged (Shadow) |
| `0x02` | `FREQ_HIGH` | Frequency Tuning Word Bits [23:16] | Active (Atomic Trigger) |
| `0x03` | `WAVE_SEL` | 0:Saw, 1:Square, 2:PWM, 3:Tri, 4:Noise | Direct Update |
| `0x04` | `PWM_WIDTH` | Duty cycle for PWM Waveform (`0x00` - `0xFF`) | Direct Update |
| `0x05` | `VOLUME` | Output audio attenuation scale | Direct Update |

---

## MIDI to Register Mapping

To achieve simple and reliable hardware testing, the bridge translates incoming MIDI events as follows:

### 1. MIDI Notes $\rightarrow$ DDS Frequency
When a **Note ON** event (Note $d$) is received:
* Convert note to frequency: $f = 440 \times 2^{\frac{d - 69}{12}}\text{ Hz}$
* Calculate 24-bit tuning word: $\text{freqWord} = \text{round}\left(f \times \frac{2^{24}}{480\,000}\right)$
* Stream in strict atomic order: Write low byte to `0x00`, middle byte to `0x01`, and high byte to `0x02` to trigger the atomic frequency update in the synthesizer.

### 2. Note Gate $\rightarrow$ Volume Control
* **Note ON** (velocity > 0): Sets Volume (`0x05`) directly to maximum (`0xFF` / 255) as a Gate ON.
* **Note OFF** (or velocity = 0): Sets Volume (`0x05`) directly to zero (`0x00`) as a Gate OFF.

### 3. Control Change (CC) $\rightarrow$ Synth Parameters
* **PWM Width (`0x04`)**: Modulated by **MIDI CC 1** (Modulation Wheel). Scales input value `0-127` to 8-bit range `0-255`.
* **Waveform Select (`0x03`)**: Modulated by **MIDI CC 2**. Maps input range `0-127` onto states `0` to `5`, capping at **`5`** (the synthesizer's first silence value defined in `Mux.scala` for safety).

---

## Repository Structure

```text
spinalSynth_MIDI_SW/
├── README.md            # Project specification
├── requirements.txt     # Dependencies
└── src/
    ├── controller.py    # Serial communication layer & DDS math
    └── bridge.py        # MIDI input event listener & main event loop
```

---

## Installation & Setup

It is highly recommended to run this project inside a dedicated Python virtual environment to avoid installing packages directly into your host system.

### 1. Set Up a Virtual Environment
Navigate to the project root and create a virtual environment:
```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Or activate it (Windows)
# .venv\Scripts\activate
```

Might be good to upgrade setuptools and wheel:
```bash
pip install --upgrade pip setuptools wheel
```

### 2. Install Dependencies
Ensure your virtual environment is active, then install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Run the Bridge
Start the event bridge with your active serial port and MIDI device:
```bash
python src/bridge.py --port /dev/ttyUSB0 --midi "Your MIDI Device Name"
```

*Note: If you do not specify the `--midi` flag, the script automatically prints a numbered list of all active connected MIDI input devices to the console.*
