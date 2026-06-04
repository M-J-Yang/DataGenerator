#!/usr/bin/env python3
"""Generate clean TTS wavs from cleaned_transcripts.csv and refs/."""

import argparse
import csv
import os
import re
import sys
import wave
from pathlib import Path

for env_name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    if os.environ.get(env_name) in {"0", ""}:
        os.environ[env_name] = "1"

import torch


DEFAULT_MODEL_DIR = "pretrained_models/Fun-CosyVoice3-0.5B-2512"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant.<|endofprompt|>"
DEFAULT_ACCENT_INSTRUCT = ""
SUPPORTED_DIALECTS = (
    "广东话", "东北话", "甘肃话", "贵州话", "河南话", "湖北话",
    "湖南话", "江西话", "闽南话", "宁夏话", "山西话", "陕西话",
    "山东话", "上海话", "四川话", "天津话", "云南话",
)
DIALECT_BY_SPEAKER = {
    "spk001": "陕西话",
    "spk002": "陕西话",
    "spk003": "河南话",
    "spk004": "陕西话",
    "spk005": "陕西话",
}
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
DIGIT_READINGS = {
    "0": "洞",
    "1": "幺",
    "2": "两",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "拐",
    "8": "八",
    "9": "九",
}


def add_cosyvoice_paths(cosyvoice_dir: Path) -> None:
    sys.path.insert(0, str(cosyvoice_dir.resolve()))
    sys.path.insert(0, str((cosyvoice_dir / "third_party" / "Matcha-TTS").resolve()))


def read_text_rows(csv_path: Path, limit: int | None, start: int) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")
        required = {"key", "target"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        for index, row in enumerate(reader):
            if index < start:
                continue
            key = (row.get("key") or "").strip()
            target = (row.get("target") or "").strip()
            if not key or not target:
                continue
            rows.append({"key": key, "target": target})
            if limit is not None and len(rows) >= limit:
                break

    if not rows:
        raise ValueError("No valid rows selected from CSV")
    return rows


def list_ref_wavs(refs_dir: Path, ref_limit: int | None, ref_name: str | None) -> list[Path]:
    if not refs_dir.exists():
        raise FileNotFoundError(f"refs directory not found: {refs_dir}")

    refs = sorted(refs_dir.glob("*.wav"))
    if ref_name:
        refs = [p for p in refs if p.name == ref_name or p.stem == ref_name]
    if ref_limit is not None:
        refs = refs[:ref_limit]
    if not refs:
        raise ValueError(f"No reference wavs selected from {refs_dir}")
    return refs


def safe_name(value: str) -> str:
    value = value.strip().replace(" ", "_")
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", value)


def normalize_digits_for_tts(text: str) -> str:
    """Step 8 minimal aviation digit reading: replace each Arabic digit."""
    return "".join(DIGIT_READINGS.get(char, char) for char in text)


def parse_ref_metadata(ref_wav: Path) -> tuple[str, str, str]:
    stem = ref_wav.stem
    parts = stem.split("_", 1)
    speaker_id = parts[0]
    accent = parts[1] if len(parts) > 1 else "unknown"
    gender = "unknown"
    return speaker_id, accent, gender


def save_tensor_wav(path: Path, speech: torch.Tensor, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = speech.detach().cpu().squeeze()
    if audio.ndim != 1:
        audio = audio.reshape(-1)
    pcm = audio.clamp(-1.0, 1.0).mul(32767.0).to(torch.int16).numpy().tobytes()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def existing_utt_ids(metadata_path: Path) -> set[str]:
    if not metadata_path.exists() or metadata_path.stat().st_size == 0:
        return set()
    with metadata_path.open("r", encoding="utf-8", newline="") as f:
        return {row.get("utt_id", "") for row in csv.DictReader(f)}


def write_metadata_rows(metadata_path: Path, rows: list[dict[str, str]], append: bool) -> None:
    if not rows:
        return
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    seen = existing_utt_ids(metadata_path) if append else set()
    filtered = [row for row in rows if row["utt_id"] not in seen]
    if not filtered:
        print(f"metadata already up to date: {metadata_path}")
        return
    write_header = not append or not metadata_path.exists() or metadata_path.stat().st_size == 0
    mode = "a" if append else "w"
    with metadata_path.open(mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
        if write_header:
            writer.writeheader()
        for row in filtered:
            writer.writerow(row)


def resolve_generation_mode(mode: str, ref_wav: Path) -> str:
    if mode != "auto":
        return mode
    _, accent, _ = parse_ref_metadata(ref_wav)
    return "instruct2" if accent != "standard" else "cross_lingual"


def build_instruct_text(args, ref_wav: Path) -> str:
    speaker_id, _, _ = parse_ref_metadata(ref_wav)
    dialect = args.dialect or DIALECT_BY_SPEAKER.get(speaker_id, "")
    if dialect:
        if dialect not in SUPPORTED_DIALECTS:
            supported = ", ".join(SUPPORTED_DIALECTS)
            raise ValueError(f"Unsupported dialect: {dialect}. Choose one of: {supported}")
        return f"You are a helpful assistant. 请用{dialect}表达。<|endofprompt|>"
    if args.instruct_text:
        return args.instruct_text
    supported = ", ".join(SUPPORTED_DIALECTS)
    raise ValueError(
        "Dialect/accent generation needs --dialect, --instruct-text, or a speaker in DIALECT_BY_SPEAKER. "
        f"CosyVoice-supported dialects: {supported}"
    )


def synthesize_one(cosyvoice, mode: str, tts_text: str, ref_wav: Path, args) -> torch.Tensor:
    effective_mode = resolve_generation_mode(mode, ref_wav)
    if effective_mode == "cross_lingual":
        model_text = f"{args.system_prompt}{tts_text}"
        generator = cosyvoice.inference_cross_lingual(
            model_text,
            str(ref_wav),
            stream=False,
            speed=args.speed,
            text_frontend=not args.no_text_frontend,
        )
    elif effective_mode == "zero_shot":
        if not args.prompt_text:
            raise ValueError("--prompt-text is required when --mode zero_shot")
        generator = cosyvoice.inference_zero_shot(
            tts_text,
            args.prompt_text,
            str(ref_wav),
            stream=False,
            speed=args.speed,
            text_frontend=not args.no_text_frontend,
        )
    elif effective_mode == "instruct2":
        generator = cosyvoice.inference_instruct2(
            tts_text,
            build_instruct_text(args, ref_wav),
            str(ref_wav),
            stream=False,
            speed=args.speed,
            text_frontend=not args.no_text_frontend,
        )
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    chunks = [item["tts_speech"] for item in generator]
    if not chunks:
        raise RuntimeError("CosyVoice returned no audio chunks")
    return torch.cat(chunks, dim=-1) if len(chunks) > 1 else chunks[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate clean wavs with CosyVoice3.")
    parser.add_argument("--csv", default="cleaned_transcripts.csv", help="Input CSV path")
    parser.add_argument("--refs-dir", default="refs", help="Reference wav directory")
    parser.add_argument("--output-dir", default="outputs/clean", help="Clean wav output directory")
    parser.add_argument("--metadata", default="outputs/metadata.csv", help="Metadata CSV path")
    parser.add_argument("--cosyvoice-dir", default="CosyVoice", help="CosyVoice source directory")
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR, help="CosyVoice model directory")
    parser.add_argument("--limit", type=int, default=1, help="Number of CSV rows to generate")
    parser.add_argument("--start", type=int, default=0, help="Zero-based CSV row offset")
    parser.add_argument("--ref-limit", type=int, default=1, help="Number of reference wavs to use")
    parser.add_argument("--ref", default=None, help="Specific reference wav name or stem")
    parser.add_argument("--mode", choices=["auto", "cross_lingual", "zero_shot", "instruct2"], default="auto", help="Generation mode; auto uses instruct2 for light_accent refs and cross_lingual for standard refs")
    parser.add_argument("--prompt-text", default="", help="Reference transcript for zero_shot mode")
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT, help="Prefix for cross_lingual mode")
    parser.add_argument("--instruct-text", default=DEFAULT_ACCENT_INSTRUCT, help="Explicit CosyVoice instruct2 text; must include <|endofprompt|>")
    parser.add_argument("--dialect", choices=SUPPORTED_DIALECTS, default="", help="Override the speaker dialect mapping for instruct2, e.g. 陕西话 or 河南话")
    parser.add_argument("--speed", type=float, default=1.0, help="CosyVoice speed parameter")
    parser.add_argument("--split", default="train", help="Metadata split value")
    parser.add_argument("--fp16", action="store_true", help="Load model with fp16")
    parser.add_argument("--load-vllm", action="store_true", help="Load vLLM backend when supported")
    parser.add_argument("--no-text-frontend", action="store_true", help="Disable CosyVoice text frontend")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print planned outputs without loading model")
    parser.add_argument("--skip-existing", action="store_true", help="Skip wavs that already exist")
    parser.add_argument("--append-metadata", action="store_true", help="Append metadata instead of replacing it")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = read_text_rows(Path(args.csv), args.limit, args.start)
    refs = list_ref_wavs(Path(args.refs_dir), args.ref_limit, args.ref)
    output_dir = Path(args.output_dir)

    planned = []
    for row in rows:
        text = row["target"]
        tts_text = normalize_digits_for_tts(text)
        for ref_wav in refs:
            out_name = f"{safe_name(row['key'])}_{safe_name(ref_wav.stem)}.wav"
            planned.append((row, tts_text, ref_wav, output_dir / out_name))

    print(f"Selected {len(rows)} text row(s), {len(refs)} reference wav(s), {len(planned)} output wav(s).")
    if args.dry_run:
        for row, tts_text, ref_wav, out_path in planned[:20]:
            effective_mode = resolve_generation_mode(args.mode, ref_wav)
            instruct_text = build_instruct_text(args, ref_wav) if effective_mode == "instruct2" else ""
            print(f"DRY RUN: {row['key']} + {ref_wav.name} -> {out_path}; mode={effective_mode}; tts_text={tts_text}; instruct_text={instruct_text}")
        return

    cosyvoice_dir = Path(args.cosyvoice_dir)
    if not cosyvoice_dir.exists():
        raise FileNotFoundError(f"CosyVoice directory not found: {cosyvoice_dir}")
    add_cosyvoice_paths(cosyvoice_dir)

    from cosyvoice.cli.cosyvoice import AutoModel

    cosyvoice = AutoModel(model_dir=args.model_dir, fp16=args.fp16, load_vllm=args.load_vllm)
    metadata_rows = []
    for index, (row, tts_text, ref_wav, out_path) in enumerate(planned, start=1):
        if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
            print(f"[{index}/{len(planned)}] skip existing {out_path}")
        else:
            effective_mode = resolve_generation_mode(args.mode, ref_wav)
            instruct_text = build_instruct_text(args, ref_wav) if effective_mode == "instruct2" else ""
            print(f"[{index}/{len(planned)}] synthesize {row['key']} with {ref_wav.name} via {effective_mode}; instruct_text={instruct_text}")
            speech = synthesize_one(cosyvoice, args.mode, tts_text, ref_wav, args)
            save_tensor_wav(out_path, speech, cosyvoice.sample_rate)
            print(f"wrote {out_path} ({wav_duration(out_path):.2f}s)")

        speaker_id, accent, gender = parse_ref_metadata(ref_wav)
        metadata_rows.append(
            {
                "utt_id": f"{row['key']}_{safe_name(ref_wav.stem)}_clean",
                "text": row["target"],
                "tts_text": tts_text,
                "speaker_id": speaker_id,
                "accent": accent,
                "gender": gender,
                "speed": str(args.speed),
                "snr": "clean",
                "noise_type": "none",
                "radio_effect": "false",
                "wav_path": str(out_path),
                "split": args.split,
            }
        )

    write_metadata_rows(Path(args.metadata), metadata_rows, append=args.append_metadata)
    print(f"wrote metadata rows: {len(metadata_rows)} -> {args.metadata}")


if __name__ == "__main__":
    main()
