#!/usr/bin/env python3
"""Verify checksums, stream format, duration and complete lossless audio decoding."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


def verify(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    started=time.monotonic()
    tracks=[]
    for item in manifest['tracks']:
        path=(directory/item['path']).resolve()
        path.relative_to(directory.resolve())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'Checksum mismatch: {path.name}')
        metadata=json.loads(subprocess.check_output([
            'ffprobe','-v','error','-show_entries',
            'stream=codec_name,sample_rate,channels,bits_per_raw_sample:format=duration',
            '-of','json',str(path)],text=True))
        stream=metadata['streams'][0]
        duration=float(metadata['format']['duration'])
        if int(stream['channels'])!=item['channels'] or int(stream['sample_rate'])!=item['sample_rate']:
            raise ValueError(f'Audio format mismatch: {path.name}')
        if abs(duration-item['duration_seconds'])>.02:
            raise ValueError(f'Duration mismatch: {path.name}')
        subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),
                        '-f','null','-'],check=True,capture_output=True)
        tracks.append({'file':path.name,'sha256_verified':True,'complete_decode':True,
                       'codec':stream['codec_name'],'duration_seconds':duration,
                       'sample_rate':int(stream['sample_rate']),'channels':int(stream['channels'])})
    return {'schema_version':1,'decoder':'ffmpeg','tracks_verified':len(tracks),
            'total_audio_seconds':sum(t['duration_seconds'] for t in tracks),
            'verification_seconds':round(time.monotonic()-started,3),
            'hardware_playback_tested':False,'tracks':tracks}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path(__file__).parent/'generated')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    report=json.dumps(verify(args.directory),indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(report)
    print(report,end='')


if __name__=='__main__':
    main()
