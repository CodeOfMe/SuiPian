from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .api import get_info, hide_file, reveal_file, validate_morph


def main():
    parser = argparse.ArgumentParser(
        prog="suipian",
        description="SuiPian - File disguise and restoration tool (碎片)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  suipian hide image.png readme.txt -o output.txt -p mypassword
  suipian reveal output.txt -o restored.png -p mypassword
  suipian validate output.txt
  suipian info output.txt
""",
    )

    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")

    subparsers = parser.add_subparsers(dest="command", required=True)

    hide_parser = subparsers.add_parser("hide", help="Hide a file inside a carrier file")
    hide_parser.add_argument("source", help="Source file to hide")
    hide_parser.add_argument("carrier", help="Carrier file (text file to embed into)")
    hide_parser.add_argument("-o", "--output", type=Path, required=True, help="Output file path")
    hide_parser.add_argument(
        "-p", "--password", type=str, required=True, help="Password for encryption"
    )
    hide_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output results as JSON"
    )

    reveal_parser = subparsers.add_parser("reveal", help="Reveal a hidden file")
    reveal_parser.add_argument("morphed", help="Morphed file to reveal")
    reveal_parser.add_argument("-o", "--output", type=Path, required=True, help="Output file path")
    reveal_parser.add_argument(
        "-p", "--password", type=str, required=True, help="Password for decryption"
    )
    reveal_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output results as JSON"
    )

    validate_parser = subparsers.add_parser("validate", help="Validate a morphed file")
    validate_parser.add_argument("file", help="File to validate")
    validate_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output results as JSON"
    )

    info_parser = subparsers.add_parser("info", help="Get info about a morphed file")
    info_parser.add_argument("file", help="File to inspect")
    info_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.command == "hide":
            result = hide_file(
                source=args.source,
                carrier=args.carrier,
                output=args.output,
                password=args.password,
            )
            handle_result(result, args)

        elif args.command == "reveal":
            result = reveal_file(
                morphed=args.morphed,
                output=args.output,
                password=args.password,
            )
            handle_result(result, args)

        elif args.command == "validate":
            result = validate_morph(file=args.file)
            handle_result(result, args)

        elif args.command == "info":
            result = get_info(file=args.file)
            handle_result(result, args)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        logging.error(e)
        sys.exit(1)


def handle_result(result, args):
    json_output = getattr(args, "json_output", False)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    elif result.success:
        if args.command == "validate":
            print("Valid: Yes")
            print(f"Original: {result.data['info']['original_name']}")
            print(f"Type: {result.data['info']['original_type']}")
            print(f"Checksum: {result.data['info']['checksum']}")
        elif args.command == "info":
            print(f"Version: {result.data['version']}")
            print(f"Original: {result.data['original_name']}")
            print(f"Type: {result.data['original_type']}")
            print(f"Checksum: {result.data['checksum']}")
            print(f"Payload Size: {result.data['payload_size']} bytes")
        else:
            print(f"Success: {result.data['output']}")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
