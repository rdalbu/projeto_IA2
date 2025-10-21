import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import tempfile
from typing import Optional

import numpy as np
import librosa
import soundfile as sf


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _ffmpeg_webm_to_wav_bytes(webm_bytes: bytes, sr: int = 16000) -> Optional[bytes]:
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            in_path = f_in.name
            f_in.write(webm_bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            out_path = f_out.name
        try:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", in_path, "-ac", "1", "-ar", str(sr), out_path]
            subprocess.run(cmd, check=True)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            for p in (in_path, out_path):
                try:
                    os.remove(p)
                except Exception:
                    pass
    except FileNotFoundError:
        return None
    except Exception:
        return None


def decode_audio_b64_to_wav(audio_b64: str, target_sr: int = 16000) -> Optional[np.ndarray]:
    try:
        s = (audio_b64 or "").strip()
        if "," in s:
            s = s.split(",", 1)[1]
        data = base64.b64decode(s)
        if len(data) >= 4 and data[:4] == b"\x1A\x45\xDF\xA3":
            wav = _ffmpeg_webm_to_wav_bytes(data, sr=target_sr)
            if not wav:
                return None
            buf = io.BytesIO(wav)
            y, sr = sf.read(buf, dtype='float32', always_2d=False)
        else:
            buf = io.BytesIO(data)
            try:
                y, sr = sf.read(buf, dtype='float32', always_2d=False)
                if isinstance(y, np.ndarray) and y.ndim == 2:
                    y = y.mean(axis=0)
            except Exception:
                y, sr = librosa.load(buf, sr=None, mono=True)
        if sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        return y
    except Exception:
        return None


def compute_mfcc_spectrogram(y: np.ndarray, sr: int = 16000, duration: float = 1.0, n_mfcc: int = 40) -> np.ndarray:
    L = int(sr * duration)
    if len(y) < L:
        y = np.pad(y, (0, L - len(y)), mode='constant')
    else:
        y = y[:L]
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    return mfcc.astype(float)


def convert_file(input_path: str, output_path: str, sr: int = 16000, n_mfcc: int = 40, duration: float = 1.0) -> int:
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    samples = data.get('samples') or []
    total = 0
    for s in samples:
        if 'audioBase64' not in s:
            continue
        y = decode_audio_b64_to_wav(s.get('audioBase64', ''), target_sr=sr)
        if y is None:
            continue
        spec = compute_mfcc_spectrogram(y, sr=sr, duration=duration, n_mfcc=n_mfcc)
        s['spectrogram'] = spec.tolist()
        s.pop('audioBase64', None)
        total += 1
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return total


def main():
    ap = argparse.ArgumentParser(description='Convert KWS audioBase64 samples to spectrogram matrices')
    ap.add_argument('-i', '--input', required=True, help='Input JSON (kws-samples.json with audioBase64)')
    ap.add_argument('-o', '--output', required=True, help='Output JSON (kws-samples-spectrogram.json)')
    ap.add_argument('--sr', type=int, default=16000, help='Target sample rate')
    ap.add_argument('--n_mfcc', type=int, default=40, help='Number of MFCC coefficients')
    ap.add_argument('--duration', type=float, default=1.0, help='Clip length in seconds')
    args = ap.parse_args()
    if not has_ffmpeg():
        print('Aviso: ffmpeg não encontrado no PATH; WebM/Opus não será convertido.')
    total = convert_file(args.input, args.output, sr=args.sr, n_mfcc=args.n_mfcc, duration=args.duration)
    print(f'Convertidas {total} amostras para spectrogram.')


if __name__ == '__main__':
    main()
