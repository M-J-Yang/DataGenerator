#!/usr/bin/env python3
"""Create noisy/radio wavs from clean wav metadata."""

import argparse
import csv
import os
import random
import wave
from pathlib import Path

import numpy as np
from scipy import signal

for env_name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    if os.environ.get(env_name) in {"0", ""}:
        os.environ[env_name] = "1"

METADATA_FIELDS = [
    "utt_id",
    "text",
    "tts_text",
    "speaker_id",
    "accent",
    "gender",
    "speed",
    "snr",
    "noise_type",
    "radio_effect",
    "wav_path",
    "split",
]


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sampwidth = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if sampwidth != 2:
        raise ValueError(f"Only 16-bit PCM wav is supported: {path}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, sample_rate


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return audio.astype(np.float32, copy=False)
    gcd = np.gcd(source_rate, target_rate)
    return signal.resample_poly(audio, target_rate // gcd, source_rate // gcd).astype(np.float32)


def fit_noise(noise: np.ndarray, length: int, rng: random.Random) -> np.ndarray:
    if len(noise) == 0:
        raise ValueError("noise audio is empty")
    if len(noise) >= length:
        start = rng.randint(0, len(noise) - length) if len(noise) > length else 0
        return noise[start:start + length]
    repeats = int(np.ceil(length / len(noise)))
    return np.tile(noise, repeats)[:length]


def rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)) + 1e-12))


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    clean_rms = rms(clean)
    noise_rms = rms(noise)
    target_noise_rms = clean_rms / (10 ** (snr_db / 20.0))
    scaled_noise = noise * (target_noise_rms / max(noise_rms, 1e-8))
    return clean + scaled_noise


def radio_effect(audio: np.ndarray, sample_rate: int, rng: random.Random) -> np.ndarray:
    nyquist = sample_rate / 2.0
    low = min(300.0 / nyquist, 0.95)
    high = min(3400.0 / nyquist, 0.98)
    if low < high:
        b, a = signal.butter(4, [low, high], btype="bandpass")
        audio = signal.lfilter(b, a, audio).astype(np.float32)
    audio = np.clip(audio * 1.15, -0.92, 0.92)
    if len(audio) > sample_rate // 20:
        for _ in range(2):
            drop_len = rng.randint(max(1, sample_rate // 200), max(2, sample_rate // 50))
            start = rng.randint(0, max(0, len(audio) - drop_len))
            audio[start:start + drop_len] *= rng.uniform(0.0, 0.25)
    peak = float(np.max(np.abs(audio)) + 1e-8)
    return (audio / max(peak, 1.0)).astype(np.float32)


def read_metadata(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"metadata not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def existing_utt_ids(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        return {row.get("utt_id", "") for row in csv.DictReader(f)}


def append_metadata(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    seen = existing_utt_ids(path)
    filtered = [row for row in rows if row["utt_id"] not in seen]
    if not filtered:
        print(f"metadata already up to date: {path}")
        return
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
        if write_header:
            writer.writeheader()
        for row in filtered:
            writer.writerow(row)


def list_noise(noise_dir: Path) -> list[Path]:
    paths = sorted(noise_dir.glob("*.wav"))
    if not paths:
        raise ValueError(f"no wav noise files found in {noise_dir}")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate noisy/radio wavs from clean wav metadata.")
    parser.add_argument("--metadata", default="outputs/metadata.csv")
    parser.add_argument("--noise-dir", default="noise")
    parser.add_argument("--output-dir", default="outputs/noisy")
    parser.add_argument("--snrs", default="10", help="Comma-separated SNR dB values, e.g. 20,10,5,0")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260604)
    parser.add_argument("--target-rate", type=int, default=8000)
    parser.add_argument("--append-metadata", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rng = random.Random(args.seed)
    metadata_path = Path(args.metadata)
    noise_paths = list_noise(Path(args.noise_dir))
    snrs = [float(item.strip()) for item in args.snrs.split(",") if item.strip()]
    clean_rows = [row for row in read_metadata(metadata_path) if row.get("noise_type") == "none"]
    if args.limit is not None:
        clean_rows = clean_rows[:args.limit]
    if not clean_rows:
        raise ValueError("no clean metadata rows found")

    output_rows = []
    for clean_row in clean_rows:
        clean_path = Path(clean_row["wav_path"])
        clean_audio, clean_rate = read_wav(clean_path)
        clean_audio = resample_audio(clean_audio, clean_rate, args.target_rate)
        for snr in snrs:
            noise_path = noise_paths[0] if len(noise_paths) == 1 else rng.choice(noise_paths)
            noise_audio, noise_rate = read_wav(noise_path)
            noise_audio = resample_audio(noise_audio, noise_rate, args.target_rate)
            noise_audio = fit_noise(noise_audio, len(clean_audio), rng)
            noisy = mix_at_snr(clean_audio, noise_audio, snr)
            noisy = radio_effect(noisy, args.target_rate, rng)
            snr_label = str(int(snr)) if snr.is_integer() else str(snr).replace(".", "p")
            out_path = Path(args.output_dir) / f"{clean_path.stem}_snr{snr_label}_radio.wav"
            if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
                print(f"skip existing {out_path}")
            else:
                write_wav(out_path, noisy, args.target_rate)
                print(f"wrote {out_path}")
            row = dict(clean_row)
            row.update(
                {
                    "utt_id": f"{clean_row['utt_id']}_snr{snr_label}_radio",
                    "snr": snr_label,
                    "noise_type": noise_path.stem,
                    "radio_effect": "true",
                    "wav_path": str(out_path),
                }
            )
            output_rows.append(row)

    if args.append_metadata:
        append_metadata(metadata_path, output_rows)
        print(f"appended metadata rows: {len(output_rows)} -> {metadata_path}")
    else:
        print(f"generated noisy rows: {len(output_rows)}; metadata not changed without --append-metadata")


if __name__ == "__main__":
    main()
