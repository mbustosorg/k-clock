"""
 Copyright (C) 2026 Mauricio Bustos (m@bustos.org)
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio
import argparse
import datetime
from datetime import timedelta
import json
import logging
import math
import os
import re
import random
from argparse import Namespace
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

import python_weather
import pvporcupine
import pvrhino
from pixelblaze import Pixelblaze
from pvrecorder import PvRecorder

FORMAT = "[%(asctime)s][%(module)s][%(lineno)d] %(message)s"
logging.basicConfig(level=logging.INFO,
                    format=FORMAT,
                    handlers=[
                        RotatingFileHandler("k-clock.log", maxBytes=40000, backupCount=5),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger("k-clock")

moonIndex = 2
MOON_PHASES = {"NEW_MOON" : 0,
    "WAXING_CRESCENT": 1,
    "FIRST_QUARTER": 2,
    "WAXING_GIBBOUS": 3,
    "FULL_MOON": 4,
    "WANING_GIBBOUS": 5,
    "LAST_QUARTER": 6,
    "WANING_CRESCENT": 7}

def save_pattern_code(pb: Pixelblaze, pattern_name: str, dest_path: str = '.') -> bool:
    pattern_list = pb.getPatternList(True)
    pattern_id = next((pid for pid, name in pattern_list.items() if name == pattern_name), None)
    if pattern_id is None:
        logger.info(f"Pattern '{pattern_name}' not found on device")
        return False
    try:
        source = json.loads(pb.getPatternSourceCode(pattern_id)).get('main', '')
        out_path = os.path.join(dest_path, f'{pattern_name}.js')
        with open(out_path, 'w') as f:
            f.write(source)
        logger.info(f"Saved '{pattern_name}' to {out_path}")
        return True
    except Exception as e:
        logger.info(f"Failed to save '{pattern_name}': {e}")
        return False


def migrate_clock_patterns(pb: Pixelblaze, dest_path: str = 'migration'):
    os.makedirs(dest_path, exist_ok=True)
    pattern_list = pb.getPatternList(True)
    clock_patterns = {pid: name for pid, name in pattern_list.items() if name.startswith('Clock')}

    scroll_out_id = next((pid for pid, name in clock_patterns.items() if name == 'Clock Scroll Out'), None)
    if scroll_out_id is None:
        logger.info("Clock Scroll Out not found — cannot migrate")
        return
    scroll_out_source = json.loads(pb.getPatternSourceCode(scroll_out_id)).get('main', '')

    # Clock scaffold = everything from 'var color = 0.0' onwards (wakeMode, scroll state machine, digit rendering)
    scaffold_match = re.search(r'^var color\s*=\s*0\.0\s*$', scroll_out_source, re.MULTILINE)
    if scaffold_match is None:
        logger.info("Could not identify clock scaffold boundary in Clock Scroll Out")
        return
    clock_scaffold = scroll_out_source[scaffold_match.start():]

    for pattern_id, pattern_name in sorted(clock_patterns.items(), key=lambda x: x[1]):
        if pattern_name == 'Clock Scroll Out':
            source = scroll_out_source
            logger.info(f"'{pattern_name}': kept as-is (template)")
        else:
            try:
                source = json.loads(pb.getPatternSourceCode(pattern_id)).get('main', '')
            except Exception as e:
                logger.info(f"Skipping '{pattern_name}': {e}")
                continue

            # Background section = everything before the clock section marker
            split_match = re.search(r'^var color\s*=\s*0\.0\s*$', source, re.MULTILINE)
            background = source[:split_match.start()].rstrip() + '\n' if split_match else source.rstrip() + '\n'

            # Ensure background section has both background aliases
            if not re.search(r'\bbeforeRenderBackground\b', background):
                background += '\nvar beforeRenderBackground = (delta) => {}\n'
                logger.info(f"'{pattern_name}': added beforeRenderBackground stub")
            if not re.search(r'\brenderBackground\b', background):
                background += 'var renderBackground = (index, x, y) => {}\n'
                logger.info(f"'{pattern_name}': added renderBackground stub")

            source = background + '\n' + clock_scaffold
            logger.info(f"'{pattern_name}': background preserved, clock scaffold applied")

        safe_name = re.sub(r'[/\\:*?"<>|]', '_', pattern_name)
        out_path = os.path.join(dest_path, f'{safe_name}.js')
        with open(out_path, 'w') as f:
            f.write(source)
        logger.info(f"  → {out_path}")


def upload_patterns_from_directory(pb: Pixelblaze, src_path: str = 'migration'):
    # Minimal 1x1 white JPEG fallback for patterns with no preview image
    BLANK_JPEG = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e\xfe'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00'
        b'\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00'
        b'\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00'
        b'\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81'
        b'\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19'
        b'\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86'
        b'\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4'
        b'\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2'
        b'\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9'
        b'\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5'
        b'\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4'
        b'P\x00\x00\x00\x00\x1f\xff\xd9'
    )

    pattern_list = pb.getPatternList(True)
    name_to_id = {name: pid for pid, name in pattern_list.items()}

    js_files = [f for f in os.listdir(src_path) if f.endswith('.js')]
    for file_name in sorted(js_files):
        pattern_name = file_name[:-3]  # strip .js
        src_file = os.path.join(src_path, file_name)
        with open(src_file, 'r') as f:
            source = f.read()

        pattern_id = name_to_id.get(pattern_name)
        if pattern_id is None:
            logger.info(f"'{pattern_name}' not found on device — skipping")
            continue

        try:
            preview = pb.getPreviewImage(pattern_id)
            if preview is None:
                preview = BLANK_JPEG
            pb.savePattern(previewImage=preview, sourceCode=source, name=pattern_name, id=pattern_id)
            logger.info(f"Uploaded '{pattern_name}' ({pattern_id})")
        except Exception as e:
            logger.info(f"Failed to upload '{pattern_name}': {e}")


def build_pattern_file_cache(pb: Pixelblaze) -> dict:
    cache = {}
    pattern_list = pb.getPatternList(True)
    for file_name in pb.getFileList():
        if not file_name.endswith('.c'):
            continue
        pattern_id = os.path.basename(file_name).replace('.c', '')
        pattern_name = pattern_list.get(pattern_id, '')
        if not pattern_name.startswith('C '):
            continue
        try:
            logger.info(f"Reading {pattern_name} file {file_name}")
            data = json.loads(pb.getFile(file_name))
            cache[file_name] = (pattern_name, data)
        except Exception as e:
            logger.info(f"Skipping {file_name}: {e}")
    return cache


def on_and_off_playlists(pb: Pixelblaze) -> dict:
    play_list = pb.getSequencerPlaylist()
    pattern_list = pb.getPatternList(True)
    pattern_list_inv = {v: k for k, v in pattern_list.items()}
    result = {'off_list': [], 'on_list': []}
    for playlist_item in play_list['playlist']['items']:
        if pattern_list[playlist_item['id']].startswith('C '):
            result['on_list'].append(playlist_item)
            off_item = playlist_item.copy()
            off_item['id'] = pattern_list_inv[pattern_list[playlist_item['id']].replace('C ', 'C- ', 1)]
            result['off_list'].append(off_item)
        elif pattern_list[playlist_item['id']].startswith('C- '):
            result['off_list'].append(playlist_item)
            off_item = playlist_item.copy()
            off_item['id'] = pattern_list_inv[pattern_list[playlist_item['id']].replace('C- ', 'C ', 1)]
            result['on_list'].append(off_item)
        else:
            result['on_list'].append(playlist_item)
            result['off_list'].append(playlist_item)
    return result


async def listen_and_process(args: Namespace, keyword_paths: list[Any] | Any):
    try:
        porcupine = pvporcupine.create(
            access_key=args.access_key,
            library_path=args.library_path,
            model_path=args.model_path,
            device=args.device,
            keyword_paths=keyword_paths,
            sensitivities=args.sensitivities)
        rhino = pvrhino.create(
            access_key=args.access_key,
            library_path=args.library_path,
            model_path=args.model_path,
            context_path=args.context_path,)
    except pvporcupine.PorcupineInvalidArgumentError as e:
        print("One or more arguments provided to Porcupine is invalid: ", args)
        print(e)
        raise e
    except pvporcupine.PorcupineActivationError as e:
        print("AccessKey activation error")
        raise e
    except pvporcupine.PorcupineActivationLimitError as e:
        print("AccessKey '%s' has reached it's temporary device limit" % args.access_key)
        raise e
    except pvporcupine.PorcupineActivationRefusedError as e:
        print("AccessKey '%s' refused" % args.access_key)
        raise e
    except pvporcupine.PorcupineActivationThrottledError as e:
        print("AccessKey '%s' has been throttled" % args.access_key)
        raise e
    except pvporcupine.PorcupineError as e:
        print("Failed to initialize Porcupine")
        raise e

    keywords = list()
    for x in keyword_paths:
        keyword_phrase_part = os.path.basename(x).replace('.ppn', '').split('_')
        if len(keyword_phrase_part) > 6:
            keywords.append(' '.join(keyword_phrase_part[0:-6]))
        else:
            keywords.append(keyword_phrase_part[0])

    logger.info('Porcupine version: %s' % porcupine.version)

    recorder = PvRecorder(
        frame_length=porcupine.frame_length,
        device_index=args.audio_device_index)
    recorder.start()

    pixelblazes = list(Pixelblaze.EnumerateAddresses(timeout=5000))
    clock_ipaddress = None
    for ipAddress in pixelblazes:
        logger.info(f"Checking to see if '{ipAddress}' is the correct one...")
        try:
            with Pixelblaze(ipAddress) as pb:
                config = pb.getConfigSettings()
                if config["name"] == "k-clock":
                    clock_ipaddress = ipAddress
                    logger.info(f"Found k-clock at '{clock_ipaddress}'")
                    play_list = on_and_off_playlists(pb)
                    current_list = pb.getSequencerPlaylist()
                    current_list['playlist']['items'] = play_list['on_list']
                    pb.setSequencerPlaylist(current_list)
                    pb.playSequencer()
                    break
        except:
            continue
    if clock_ipaddress is None:
        logger.info("Rebooting due to k-clock not found on the network")
        #os.system("sudo reboot")

    logger.info('Listening...')

    try:
        last_brightness = datetime.now()
        while True:
            pcm = recorder.read()
            result = porcupine.process(pcm)
            now = datetime.now()
            if now - last_brightness > timedelta(minutes=15):
                last_brightness = now
                async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
                    try:
                        now = datetime.now()
                        brightness = (-math.cos(
                            (now.hour + (now.minute / 60.0)) / 24.0 * 2.0 * math.pi) + 1.0) / 2.0 * 0.45 + 0.2
                        logger.info(f"\tBrightness: {brightness:.2f}")
                        with Pixelblaze(clock_ipaddress) as pb:
                            pb.setBrightnessSlider(brightness)
                            pb.playSequencer()
                    except Exception as e:
                        logger.info(f"Exception during setting brightness {e}")
            if result >= 0:
                with Pixelblaze(clock_ipaddress) as pb:
                    logger.info('Detected %s' % (keywords[result]))
                    pattern_before_wake = pb.getActivePattern()
                    pb.setActivePatternByName("C wake word")
                    woken = datetime.now()
                    while True:
                        if (datetime.now() - woken).seconds > 5:
                            logger.info("Timeout, going back to listening")
                            pb.setActivePattern(pattern_before_wake)
                            pb.playSequencer()
                            break
                        pcm = recorder.read()
                        is_finalized = rhino.process(pcm)
                        if is_finalized:
                            inference = rhino.get_inference()
                            if inference.is_understood:
                                intent = inference.intent
                                slots = inference.slots
                                if intent == "setPattern":
                                    active_pattern = pb.getActivePattern()
                                    if slots['pattern'] == 'time' and active_pattern != 'time':
                                        logger.info("Set pattern to time")
                                        pb.setActivePatternByName('Clock')
                                    elif slots['pattern'] == 'moon phase' and active_pattern != 'moon_phase':
                                        logger.info("Set pattern to moon phase")
                                        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
                                            try:
                                                weather = await client.get('Oakland')
                                                moon_phase_index = MOON_PHASES[weather.daily_forecasts[0].moon_phase.name]
                                                logger.info(f"\tMoon phase: {weather.daily_forecasts[0].moon_phase.name} ({moon_phase_index})")
                                                pattern_list = pb.getPatternList(True)
                                                moon_id = next((pid for pid, name in pattern_list.items() if name == 'moon phase'), None)
                                                if moon_id:
                                                    pb.setActivePatternByName('moon phase')
                                                    controls = pb.getActiveControls()
                                                    controls['sliderMoonIndex'] = moon_phase_index / 8.0
                                                    pb.setActiveControls(controls)
                                                    await asyncio.sleep(5)
                                                    controls['sliderMoonIndex'] = 0
                                                    pb.setActiveControls(controls)
                                                    pb.setActivePattern(pattern_before_wake)
                                                    pb.playSequencer()
                                            except Exception as e:
                                                logger.info(f"Exception during setting pattern {e}")
                                    elif slots['pattern'] == 'clock on':
                                        logger.info(f"Turn on clock")
                                        current_list = pb.getSequencerPlaylist()
                                        current_list['playlist']['items'] = play_list['on_list']
                                        pb.setSequencerPlaylist(current_list)
                                        pb.setSequencerPlaylist(play_list['on_list'])
                                        pb.playSequencer()
                                    elif slots['pattern'] == 'clock off':
                                        logger.info(f"Turn off clock")
                                        current_list = pb.getSequencerPlaylist()
                                        current_list['playlist']['items'] = play_list['off_list']
                                        pb.setSequencerPlaylist(current_list)
                                        pb.playSequencer()
                                    logger.info("Complete")
                                    break
    except KeyboardInterrupt:
        logger.info('Stopping ...')
    finally:
        recorder.delete()
        porcupine.delete()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--access_key',
        help='AccessKey obtained from Picovoice Console (https://console.picovoice.ai/)')
    parser.add_argument(
        '--keywords',
        nargs='+',
        help='List of default keywords for detection. Available keywords: %s' % ', '.join(
            '%s' % w for w in sorted(pvporcupine.KEYWORDS)),
        choices=sorted(pvporcupine.KEYWORDS),
        metavar='')
    parser.add_argument(
        '--keyword_paths',
        nargs='+',
        help="Absolute paths to keyword model files. If not set it will be populated from `--keywords` argument")
    parser.add_argument(
        '--library_path',
        help='Absolute path to dynamic library. Default: using the library provided by `pvporcupine`')
    parser.add_argument(
        '--model_path',
        help='Absolute path to the file containing model parameters. '
             'Default: using the library provided by `pvporcupine`')
    parser.add_argument(
        '--device',
        help='Device to run inference on (`best`, `cpu:{num_threads}` or `gpu:{gpu_index}`). '
             'Default: automatically selects best device')
    parser.add_argument(
        '--sensitivities',
        nargs='+',
        help="Sensitivities for detecting keywords. Each value should be a number within [0, 1]. A higher "
             "sensitivity results in fewer misses at the cost of increasing the false alarm rate. If not set 0.5 "
             "will be used.",
        type=float,
        default=None)
    parser.add_argument(
        '--context_path',
        help="Absolute path to context file.")
    parser.add_argument('--audio_device_index', help='Index of input audio device.', type=int, default=-1)
    parser.add_argument('--show_audio_devices', action='store_true')
    parser.add_argument(
        '--show_inference_devices',
        action='store_true',
        help='Print devices that are available to run Porcupine inference')

    args = parser.parse_args()

    if args.show_inference_devices:
        print('\n'.join(pvporcupine.available_devices(library_path=args.library_path)))
        return

    if args.show_audio_devices:
        for i, device in enumerate(PvRecorder.get_available_devices()):
            print('Device %d: %s' % (i, device))
        return

    if args.access_key is None:
        raise ValueError("Argument --access_key is required.")

    if args.keyword_paths is None:
        if args.keywords is None:
            raise ValueError("Either `--keywords` or `--keyword_paths` must be set.")

        keyword_paths = [pvporcupine.KEYWORD_PATHS[x] for x in args.keywords]
    else:
        keyword_paths = args.keyword_paths

    if args.sensitivities is None:
        args.sensitivities = [0.5] * len(keyword_paths)

    if len(keyword_paths) != len(args.sensitivities):
        raise ValueError('Number of keywords does not match the number of sensitivities.')

    asyncio.run(listen_and_process(args, keyword_paths))


if __name__ == '__main__':
    main()