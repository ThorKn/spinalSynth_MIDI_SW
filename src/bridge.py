import argparse
import sys
import mido
from controller import SpinalSynthController

def parse_args():
    parser = argparse.ArgumentParser(description="spinalSynth MIDI-to-UART Bridge")
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("--midi", help="Name of MIDI input device (optional)")
    return parser.parse_args()

def main():
    args = parse_args()

    # 1. Initialize the Hardware Synth Controller
    try:
        synth = SpinalSynthController(args.port)
    except Exception as e:
        print(f"Error opening serial port {args.port}: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Select and Open the MIDI Input Port
    input_names = mido.get_input_names()
    if not input_names:
        print("No MIDI input devices detected. Please plug in a controller.", file=sys.stderr)
        synth.close()
        sys.exit(1)

    midi_port_name = args.midi
    if not midi_port_name:
        print("Available MIDI Devices:")
        for idx, name in enumerate(input_names):
            print(f" [{idx}] {name}")
        print("\nUsing the first device by default.")
        midi_port_name = input_names[0]
    elif midi_port_name not in input_names:
        # Fallback to fuzzy match
        matched = [n for n in input_names if midi_port_name.lower() in n.lower()]
        if matched:
            midi_port_name = matched[0]
        else:
            print(f"Requested MIDI device '{midi_port_name}' not found. Defaulting to first device.", file=sys.stderr)
            midi_port_name = input_names[0]

    print(f"Opening MIDI input port: {midi_port_name}")

    # 3. Simple Single-Threaded MIDI Listening Loop
    try:
        with mido.open_input(midi_port_name) as midi_in:
            print("Listening for MIDI events... Press Ctrl+C to exit.")
            for msg in midi_in:
                # Handle Note ON
                if msg.type == 'note_on' and msg.velocity > 0:
                    synth.set_midi_note(msg.note)
                    # Gate ON: Set volume directly to maximum (0xFF)
                    synth.set_volume(0xFF)
                    print(f"Note ON: Note={msg.note} -> (Gate ON, Volume=0xFF)")

                # Handle Note OFF
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    # Gate OFF: Set volume directly to zero (0x00)
                    synth.set_volume(0x00)
                    print(f"Note OFF: Note={msg.note} -> (Gate OFF, Volume=0x00)")

                # Handle Control Change (CC)
                elif msg.type == 'control_change':
                    # CC 1 (Modulation Wheel) -> PWM Width (0 to 255)
                    if msg.control == 1:
                        pwm_width = min(255, msg.value * 2)
                        synth.set_pwm_width(pwm_width)
                        print(f"CC 1 (Modulation) -> PWM Width = {pwm_width}")

                    # CC 2 -> Waveform Select (0 to 5, capped at 5)
                    elif msg.control == 2:
                        # Map 0-127 onto 6 distinct states (0, 1, 2, 3, 4, 5)
                        wave_sel = min(5, msg.value // 22)
                        synth.set_wave_select(wave_sel)
                        
                        wave_names = {
                            0: "Saw", 
                            1: "Square", 
                            2: "PWM", 
                            3: "Tri", 
                            4: "Noise", 
                            5: "Silence (Cap)"
                        }
                        name = wave_names.get(wave_sel, "Silence")
                        print(f"CC 2 (Wave Mux) -> WaveSelect = {wave_sel} ({name})")

    except KeyboardInterrupt:
        print("\nExiting MIDI-to-UART Bridge...")
    finally:
        # Ensure volume is set to 0 before shutting down
        try:
            synth.set_volume(0)
        except Exception:
            pass
        synth.close()

if __name__ == "__main__":
    main()
