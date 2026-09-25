"""Render the two-minute, 120 BPM deep breakbeat score for the bridge demo.

Recorded acoustic drum one-shots provide the break. The bass, pads, and musical
parts are synthesized here. Sixteenth-note breaks give it a 90s jungle feel at
the project's required 120 BPM. One continuous WAV avoids source reloads.
"""

from __future__ import annotations

import json
import math
import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "audio" / "breakdance_nightclub_120bpm.wav"
CUES = ROOT / "audio" / "breakdance_nightclub_120bpm.cues.json"
DRUMS = ROOT / "audio" / "drums"
SAMPLE_RATE = 44100
DURATION = 120
BPM = 120
BEAT = 60 / BPM
STEP = BEAT / 4
SEED = 1201996

# These boundaries are the ten Blender source-clip boundaries, in seconds.
SECTIONS = [
    (0, 13, "Upright opening", 0.48),
    (13, 28, "Fancy footwork", 0.72),
    (28, 40, "Helicopter", 0.83),
    (40, 50, "Handstand kicks", 0.79),
    (50, 60, "Kick flip", 0.94),
    (60, 64, "Motorcycle freeze", 0.18),
    (64, 78, "Upright variation", 0.84),
    (78, 96, "Long break combo", 0.98),
    (96, 114, "Break sequence with flips", 1.0),
    (114, 120, "Finale", 0.90),
]

N = SAMPLE_RATE * DURATION
mix = np.zeros((N, 2), dtype=np.float32)
bass_bus = np.zeros_like(mix)
echo_send = np.zeros_like(mix)
rng = np.random.default_rng(SEED)
kick_times: list[float] = []
samples: dict[str, np.ndarray] = {}


def note(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def timebase(length: float) -> np.ndarray:
    return np.arange(round(length * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE


def envelope(t: np.ndarray, attack: float, release: float) -> np.ndarray:
    return np.minimum(1, t / max(attack, 1e-5)) * np.minimum(
        1, (t[-1] - t) / max(release, 1e-5)
    ).clip(0, 1)


def add(start: float, sound: np.ndarray, pan: float = 0.0,
        send: float = 0.0, bass: bool = False) -> None:
    offset = round(start * SAMPLE_RATE)
    if offset >= N or offset + len(sound) <= 0:
        return
    first = max(0, -offset)
    last = min(len(sound), N - offset)
    target = slice(max(0, offset), max(0, offset) + last - first)
    left = math.sqrt((1 - pan) / 2)
    right = math.sqrt((1 + pan) / 2)
    part = sound[first:last].astype(np.float32, copy=False)
    destination = bass_bus if bass else mix
    destination[target, 0] += part * left
    destination[target, 1] += part * right
    if send:
        echo_send[target, 0] += part * right * send
        echo_send[target, 1] += part * left * send


def load_samples() -> None:
    """Load and tail-gate the bundled Pearl acoustic drum recordings once."""
    limit = {"kick-01": .36, "snare-01": .39, "snare-02": .36,
             "snare-03": .36, "hihat-closed": .19, "hihat-open": .48,
             "ride-01": .95, "crash-01": 1.15, "tom-01": .72,
             "tom-02": .72, "tom-03": .72}
    samples.clear()
    for name, seconds in limit.items():
        path = DRUMS / f"{name}.wav"
        with wave.open(str(path), "rb") as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 2, 2):
                raise ValueError(f"Expected 44.1 kHz stereo 16-bit drum sample: {path}")
            frame_count = min(wav.getnframes(), round(seconds * SAMPLE_RATE))
            audio = np.frombuffer(wav.readframes(frame_count), dtype="<i2").reshape(-1, 2)
        sound = audio.astype(np.float32) / 32768
        attack = min(len(sound), round(.002 * SAMPLE_RATE))
        release = min(len(sound), round((.07 if "hat" in name or name == "ride-01" else .045)
                                       * SAMPLE_RATE))
        sound[:attack] *= np.linspace(0, 1, attack, dtype=np.float32)[:, None]
        sound[-release:] *= np.linspace(1, 0, release, dtype=np.float32)[:, None]
        samples[name] = sound


def play_sample(name: str, start: float, gain: float, pan: float = 0.0,
                send: float = 0.0) -> None:
    sound = samples[name]
    offset = round(start * SAMPLE_RATE)
    if offset >= N or offset + len(sound) <= 0:
        return
    first = max(0, -offset)
    last = min(len(sound), N - offset)
    target = slice(max(0, offset), max(0, offset) + last - first)
    part = sound[first:last]
    left = math.sqrt(1 - pan) * gain
    right = math.sqrt(1 + pan) * gain
    mix[target, 0] += part[:, 0] * left
    mix[target, 1] += part[:, 1] * right
    if send:
        echo_send[target, 0] += part[:, 1] * right * send
        echo_send[target, 1] += part[:, 0] * left * send


def energy_at(sec: float) -> float:
    for start, end, _, energy in SECTIONS:
        if start <= sec < end:
            return energy
    return SECTIONS[-1][3]


# Four-second changes (two bars) make the score darker and progressive.
CHORDS = [
    (38, (62, 65, 69, 72)),  # Dm9
    (34, (58, 62, 65, 69)),  # Bbmaj7
    (31, (58, 62, 67, 69)),  # Gm9
    (33, (57, 61, 64, 67)),  # A7
    (38, (62, 65, 69, 72)),
    (29, (53, 57, 60, 64)),  # Fmaj7
    (36, (60, 64, 67, 74)),  # Cadd9
    (33, (57, 61, 64, 67)),
]


def chord_at(sec: float) -> tuple[int, tuple[int, ...]]:
    return CHORDS[int(sec // 4) % len(CHORDS)]


def pad(start: float, notes: tuple[int, ...], amount: float) -> None:
    t = timebase(4.8)
    env = envelope(t, 0.65, 1.2)
    wobble = 0.84 + 0.16 * np.sin(2 * np.pi * 0.19 * t)
    for index, midi in enumerate(notes):
        f = note(midi - 12)
        phase = 2 * np.pi * f * (t + 0.0013 * np.sin(2 * np.pi * 0.09 * t))
        tone = (np.sin(phase) + 0.38 * np.sin(2.003 * phase)
                + 0.17 * np.sin(3.007 * phase))
        add(start, (tone * env * wobble * amount * 0.076).astype(np.float32),
            -0.68 + index * 0.44, 0.18)


def rhodes(start: float, midi: int, amount: float, pan: float) -> None:
    t = timebase(0.9)
    f = note(midi)
    strike = (1 - np.exp(-t * 220)) * np.exp(-t * 4.3)
    tremolo = 0.83 + 0.17 * np.cos(2 * np.pi * 5.6 * t)
    tone = (np.sin(2 * np.pi * f * t)
            + 0.28 * np.sin(2 * np.pi * f * 2.002 * t)
            + 0.17 * np.sin(2 * np.pi * f * 3.01 * t)
            + 0.11 * np.sin(2 * np.pi * f * 6.98 * t))
    add(start, (tone * strike * tremolo * amount * 0.12).astype(np.float32),
        pan, 0.48)


def reese(start: float, root: int, amount: float, length: float = 0.58) -> None:
    """Detuned saw-like bass with a separate true sub fundamental."""
    t = timebase(length)
    f = note(root)
    attack = 1 - np.exp(-t * 80)
    env = attack * np.exp(-t * (3.4 if length > 0.7 else 4.8))
    phase1 = 2 * np.pi * f * 0.994 * t
    phase2 = 2 * np.pi * f * 1.006 * t
    brightness = 0.63 + 0.37 * np.sin(2 * np.pi * (1.45 * t + 0.14))
    body = np.zeros_like(t)
    for harmonic in range(1, 7):
        body += (np.sin(harmonic * phase1) + np.sin(harmonic * phase2)) / harmonic
    body = np.tanh(body * 0.75) * brightness
    sub = np.sin(2 * np.pi * (f / 2) * t) * np.exp(-t * 2.3)
    add(start, ((0.17 * body + 0.36 * sub) * env * amount).astype(np.float32),
        bass=True)


def kick(start: float, amount: float) -> None:
    play_sample("kick-01", start, amount * .72)
    kick_times.append(start)


def snare(start: float, amount: float, ghost: bool = False) -> None:
    name = "snare-01" if ghost else ("snare-02" if rng.integers(2) else "snare-03")
    play_sample(name, start, amount * (.34 if ghost else .68),
                -.10 if ghost else .04, .05 if ghost else .14)


def hat(start: float, amount: float, pan: float, open_hat: bool = False) -> None:
    play_sample("hihat-open" if open_hat else "hihat-closed",
                start, amount * (.22 if open_hat else .19), pan, .04)


def ride(start: float, amount: float, pan: float) -> None:
    play_sample("ride-01", start, amount * .17, pan, .04)


def impact(start: float, amount: float) -> None:
    t = timebase(1.4)
    freq = 43 + 45 * np.exp(-t * 18)
    phase = 2 * np.pi * np.cumsum(freq, dtype=np.float64) / SAMPLE_RATE
    boom = np.sin(phase) * np.exp(-t * 3.4)
    add(start, (boom * 0.37 * amount).astype(np.float32), 0, .12)
    play_sample("crash-01", start, amount * .31, send=.08)


def riser(end: float, length: float, amount: float) -> None:
    source = samples["crash-01"][::-1]
    positions = np.linspace(0, len(source) - 1, round(length * SAMPLE_RATE))
    t = timebase(length)
    reverse = (t / length) ** 1.7
    swell = np.column_stack([np.interp(positions, np.arange(len(source)), source[:, side])
                             for side in range(2)]).astype(np.float32)
    swell *= reverse[:, None] * amount * .24
    edge = min(len(swell), round(.004 * SAMPLE_RATE))
    swell[-edge:] *= np.linspace(1, 0, edge, dtype=np.float32)[:, None]
    play_stereo(end - length, swell)


def play_stereo(start: float, sound: np.ndarray) -> None:
    offset = round(start * SAMPLE_RATE)
    first = max(0, -offset)
    last = min(len(sound), N - offset)
    if last > first:
        mix[max(0, offset):max(0, offset) + last - first] += sound[first:last]


def drums() -> None:
    # 16-step bars with a two-bar chopped break; ghost snares and swing provide
    # the push/pull missing from a plain four-on-the-floor pattern.
    kicks = [
        {0: 1.0, 7: 0.42, 10: 0.78, 14: 0.34},
        {0: 0.86, 3: 0.36, 8: 0.67, 11: 0.80, 15: 0.30},
    ]
    ghosts = [
        {2: 0.37, 6: 0.52, 11: 0.32, 14: 0.52},
        {1: 0.30, 6: 0.58, 10: 0.36, 14: 0.72},
    ]
    cuts = {s for s, _, _, _ in SECTIONS[1:]}
    for bar in range(DURATION // 2):
        bar_start = bar * 2.0
        pattern = bar % 2
        for step in range(16):
            t = bar_start + step * STEP + (0.014 if step % 2 else 0)
            if t >= DURATION:
                continue
            energy = energy_at(t)
            freeze = 60 <= t < 64
            intro = t < 8
            if freeze:
                continue

            if step in kicks[pattern] and (not intro or step in (0, 10)):
                kick(t, kicks[pattern][step] * (0.54 + energy * 0.62))
            if step in (4, 12) and not intro:
                snare(t, 0.63 + energy * 0.53)
            elif step in ghosts[pattern] and energy > 0.6:
                snare(t, ghosts[pattern][step] * energy, ghost=True)

            if step % 2 == 0:
                hat(t, (0.36 if intro else 0.55) + 0.25 * energy,
                    -0.4 if step % 4 else 0.38, open_hat=step == 14 and energy > 0.8)
            elif energy > 0.74 and not intro:
                hat(t, 0.24 + energy * 0.23, 0.44 if step % 4 else -0.44)
            if step in (2, 10) and energy > 0.88 and bar % 4 in (2, 3):
                ride(t, energy * 0.62, -0.5 if step == 2 else 0.5)

        # Snare rolls announce the next physical phrase, without losing the
        # underlying two-beats-per-second clock.
        if bar_start + 2 in cuts:
            for i in range(4):
                snare(bar_start + 1.5 + i * STEP, 0.35 + i * 0.17, ghost=i < 2)


def harmony_and_bass() -> None:
    for start in np.arange(0, DURATION, 4.0):
        root, chord = chord_at(float(start))
        energy = energy_at(float(start) + 0.2)
        pad(float(start), chord, 0.66 + energy * 0.48)
        if not (60 <= start < 64):
            for i, pitch in enumerate((chord[1], chord[3], chord[2])):
                rhodes(float(start) + i * 0.25, pitch,
                       0.43 + energy * 0.32, -0.48 + i * 0.48)

    # Syncopated two-bar bass riff. Repeated root and fifth tones make the
    # rhythm legible while chords progress every two bars.
    riff = [(0, 0, 0.56), (3, 0, 0.35), (6, 7, 0.33),
            (9, 0, 0.52), (12, -2, 0.40), (15, 7, 0.29),
            (19, 0, 0.45), (22, 7, 0.38), (25, 0, 0.55),
            (28, -2, 0.36)]
    for phrase in range(DURATION // 4):
        start = phrase * 4.0
        root, chord = chord_at(start)
        for step, interval, length in riff:
            t = start + step * STEP
            energy = energy_at(t)
            if 60 <= t < 64 or (t < 8 and step not in (0, 9, 25)):
                continue
            reese(t, root + interval, 0.43 + energy * 0.77, length)

        # Offbeat Rhodes answers and small arpeggio accents; the later acts
        # add denser, brighter calls as the dance becomes more physical.
        if start >= 12 and not (60 <= start < 64):
            for i, offset in enumerate((1.25, 2.75, 3.5)):
                rhodes(start + offset, chord[(phrase + i) % 4] + (12 if start >= 78 else 0),
                       0.32 + energy_at(start + offset) * 0.31,
                       -0.52 if i % 2 else 0.52)

    # During the freeze, a held sub note and distant chord replace the break.
    reese(60.0, 38, 0.65, 2.4)
    rhodes(61.0, 74, 0.50, -0.48)
    rhodes(62.5, 69, 0.39, 0.48)


def transitions() -> None:
    for sec, _, _, energy in SECTIONS[1:]:
        riser(float(sec), min(1.5, float(sec)), 0.53 + 0.62 * energy)
        if sec != 60:
            impact(float(sec), 0.48 + 0.50 * energy)
            for i, name in enumerate(("tom-01", "tom-02", "tom-03")):
                play_sample(name, float(sec) - .375 + i * STEP,
                            .19 + .10 * i, -.45 + .45 * i, .07)
    impact(0.0, 0.63)
    impact(60.0, 0.49)
    impact(114.0, 0.85)
    impact(118.0, 0.70)
    # Additional rotor-like chops under the helicopter and snare bustle in
    # the final long combination tie sound to those movements.
    for sec in np.arange(28, 40, 0.5):
        hat(float(sec) + 0.375, 0.53, -0.72 if int(sec * 2) % 2 else 0.72)
    for sec in np.arange(96, 114, 2):
        for i in range(4):
            snare(float(sec) + 1.5 + i * STEP, 0.20 + 0.12 * i, ghost=True)


def render() -> None:
    global mix, rng
    mix.fill(0)
    bass_bus.fill(0)
    echo_send.fill(0)
    kick_times.clear()
    rng = np.random.default_rng(SEED)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    load_samples()
    harmony_and_bass()
    drums()
    transitions()

    # Sidechain the bass for the first 130 ms after each kick. This keeps the
    # low end forceful and uncluttered without pumping the atmospheric pads.
    for sec in kick_times:
        i = round(sec * SAMPLE_RATE)
        j = min(N, i + round(0.14 * SAMPLE_RATE))
        if i < N:
            t = np.arange(j - i, dtype=np.float32) / SAMPLE_RATE
            bass_bus[i:j] *= (0.39 + 0.61 * (1 - np.exp(-t * 19)))[:, None]
    mix[:] += bass_bus

    # Dub-style cross-channel repeats add width after the dry drums and bass.
    for delay_sec, gain in ((0.25, 0.22), (0.5, 0.13), (1.0, 0.075)):
        d = round(delay_sec * SAMPLE_RATE)
        mix[d:] += echo_send[:-d] * gain

    # Mild analog-style drive and a safe true-sample peak ceiling.
    mix[:] = np.tanh(mix * 1.45)
    mix -= mix.mean(axis=0)
    fade_in = round(0.06 * SAMPLE_RATE)
    fade_out = round(1.5 * SAMPLE_RATE)
    mix[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
    mix[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]
    peak = float(np.max(np.abs(mix)))
    mix *= 0.91 / peak
    pcm = np.round(mix * 32767).astype("<i2")
    with wave.open(str(OUT), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    CUES.write_text(json.dumps({
        "title": "Nightclub / deep breakbeat / ten movements",
        "style": "1990s deep drum-and-bass and breakbeat at the project's 120 BPM",
        "bpm": BPM,
        "duration_seconds": DURATION,
        "sample_rate": SAMPLE_RATE,
        "source": "Original arrangement and synths with Pearl Master Studio acoustic drums; deterministic seed 1201996",
        "drum_samples": "Pearl Master Studio Pack 1 by enoe, CC BY 3.0; https://oramics.github.io/sampled/DRUMS/pearl-master-studio/",
        "sections": [{"start": s, "end": e, "movement": name, "energy": energy}
                     for s, e, name, energy in SECTIONS],
        "peak_dbfs": round(20 * math.log10(float(np.max(np.abs(pcm))) / 32767), 2),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1_000_000:.1f} MB, {DURATION}s, {BPM} BPM)")


if __name__ == "__main__":
    render()
