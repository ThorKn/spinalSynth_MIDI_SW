import math
import serial

class SpinalSynthController:
    # Synthesizer Constants
    UPDATE_RATE_HZ = 480000.0  # 480 kHz DDS Update Rate
    PHASE_ACC_BITS = 24
    MAX_FREQ_WORD = (1 << PHASE_ACC_BITS) - 1

    # Register Addresses
    REG_FREQ_LOW = 0x00
    REG_FREQ_MID = 0x01
    REG_FREQ_HIGH = 0x02
    REG_WAVE_SEL = 0x03
    REG_PWM_WIDTH = 0x04
    REG_VOLUME = 0x05

    # UART Protocol Header
    CMD_WRITE = 0x01

    def __init__(self, port: str, baudrate: int = 115200):
        self.ser = serial.Serial(port, baudrate, timeout=1.0)
        print(f"Connected to spinalSynth on {port} at {baudrate} baud.")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _write_register(self, address: int, data: int):
        """Sends a structured 3-byte UART frame: [0x01] [Address] [Data]"""
        packet = bytes([self.CMD_WRITE, address & 0xFF, data & 0xFF])
        self.ser.write(packet)
        self.ser.flush()

    def set_frequency(self, frequency_hz: float):
        """Converts a frequency in Hz to a 24-bit DDS tuning word and writes atomically."""
        # DDS math: freqWord = round(f * 2^24 / updateRate)
        freq_word = round((frequency_hz * (1 << self.PHASE_ACC_BITS)) / self.UPDATE_RATE_HZ)
        freq_word = max(0, min(freq_word, self.MAX_FREQ_WORD))

        # Split into Low, Mid, and High bytes
        low_byte = freq_word & 0xFF
        mid_byte = (freq_word >> 8) & 0xFF
        high_byte = (freq_word >> 16) & 0xFF

        # Atomic Staging Sequence: Write Low and Mid first (shadows), then High (commits)
        self._write_register(self.REG_FREQ_LOW, low_byte)
        self._write_register(self.REG_FREQ_MID, mid_byte)
        self._write_register(self.REG_FREQ_HIGH, high_byte)

    def set_midi_note(self, note_number: int):
        """Converts a standard MIDI note number to Frequency and sets it."""
        # Equal temperament: f = 440 * 2^((d - 69) / 12)
        freq_hz = 440.0 * math.pow(2.0, (note_number - 69) / 12.0)
        self.set_frequency(freq_hz)

    def set_wave_select(self, wave_sel: int):
        """Sets the active waveform. Capped at 5 (first silence value)."""
        wave_sel = max(0, min(wave_sel, 5))
        self._write_register(self.REG_WAVE_SEL, wave_sel)

    def set_volume(self, volume: int):
        """Sets master output attenuation (0 to 255)."""
        volume = max(0, min(volume, 255))
        self._write_register(self.REG_VOLUME, volume)

    def set_pwm_width(self, width: int):
        """Sets the pulse-width duty cycle (0 to 255)."""
        width = max(0, min(width, 255))
        self._write_register(self.REG_PWM_WIDTH, width)
