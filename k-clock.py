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

import argparse
import datetime
import logging
import os
import struct
import wave
from argparse import Namespace
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

import pvporcupine
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

def listen_and_process(args: Namespace, keyword_paths: list[Any] | Any):
    try:
        porcupine = pvporcupine.create(
            access_key=args.access_key,
            library_path=args.library_path,
            model_path=args.model_path,
            device=args.device,
            keyword_paths=keyword_paths,
            sensitivities=args.sensitivities)
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

    wav_file = None
    if args.output_path is not None:
        wav_file = wave.open(args.output_path, "w")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)

    pixelblazes = list(Pixelblaze.EnumerateAddresses(timeout=5000))
    pattern_list = None
    clock_ipaddress = None
    pb = None
    for ipAddress in pixelblazes:
        with Pixelblaze(ipAddress) as pb:
            try:
                logger.info(f"Checking to see if '{ipAddress}' is the correct one...")
                config = pb.getConfigSettings()
                if config["name"] == "testBed":
                    clock_ipaddress = ipAddress
                    logger.info(f"Found testBed at '{clock_ipaddress}'")
                    pb = Pixelblaze(clock_ipaddress)
                    pattern_list = {v: k for k, v in pb.getPatternList().items()}
                    break
            except:
                continue
    if clock_ipaddress is None:
        logger.info("Rebooting due to testBed not found on the network")
        os.system("sudo reboot")

    logger.info('Listening ... (press Ctrl+C to exit)')

    try:
        while True:
            pcm = recorder.read()
            result = porcupine.process(pcm)

            if wav_file is not None:
                wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))

            if result >= 0:
                active_pattern = pb.getActivePattern()
                if active_pattern == pattern_list['Clock honeycomb']:
                    pb.setActivePatternByName('Clock')
                else:
                    pb.setActivePatternByName('Clock honeycomb')
                logger.info("Complete")

                logger.info('Detected %s' % (keywords[result]))
    except KeyboardInterrupt:
        logger.info('Stopping ...')
    finally:
        recorder.delete()
        porcupine.delete()
        if wav_file is not None:
            wav_file.close()

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

    parser.add_argument('--audio_device_index', help='Index of input audio device.', type=int, default=-1)

    parser.add_argument('--output_path', help='Absolute path to recorded audio for debugging.', default=None)

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

    listen_and_process(args, keyword_paths)


if __name__ == '__main__':
    main()