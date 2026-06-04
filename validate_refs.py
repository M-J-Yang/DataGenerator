import argparse
import wave
from pathlib import Path


MIN_REFS = 10
MAX_REFS = 10
MIN_DURATION_SECONDS = 3.0
MAX_DURATION_SECONDS = 30.0


def read_wav_info(path: Path) -> tuple[float, int, int]:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        if sample_rate <= 0:
            raise ValueError("invalid sample rate")
        return frames / sample_rate, sample_rate, channels


def validate_refs(refs_dir: Path) -> list[tuple[Path, float, int, int]]:
    if not refs_dir.exists():
        raise FileNotFoundError(f"refs directory not found: {refs_dir}")
    if not refs_dir.is_dir():
        raise ValueError(f"refs path is not a directory: {refs_dir}")

    wav_paths = sorted(refs_dir.glob("*.wav"))
    if not (MIN_REFS <= len(wav_paths) <= MAX_REFS):
        raise ValueError(f"expected {MIN_REFS} wav files in {refs_dir}, found {len(wav_paths)}")

    results = []
    problems = []
    for path in wav_paths:
        if not path.stem.startswith("spk"):
            problems.append(f"{path.name}: filename should start with spk, for example spk001_male_standard.wav or spk001_male_light_accent.wav")
            continue

        try:
            duration, sample_rate, channels = read_wav_info(path)
        except Exception as exc:
            problems.append(f"{path.name}: cannot read wav ({exc})")
            continue

        if not (MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS):
            problems.append(
                f"{path.name}: duration {duration:.2f}s outside recommended "
                f"{MIN_DURATION_SECONDS:.0f}-{MAX_DURATION_SECONDS:.0f}s"
            )
            continue

        results.append((path, duration, sample_rate, channels))

    if problems:
        raise ValueError("\n".join(problems))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate reference speaker wav files in refs/.")
    parser.add_argument("refs_dir", nargs="?", default="refs", help="Reference wav directory, default: refs")
    args = parser.parse_args()

    results = validate_refs(Path(args.refs_dir))
    print(f"OK: found {len(results)} valid reference wav files in {args.refs_dir}.")
    for path, duration, sample_rate, channels in results:
        print(f"{path.name}: {duration:.2f}s, {sample_rate} Hz, {channels} channel(s)")


if __name__ == "__main__":
    main()
