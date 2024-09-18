import argparse
import sys
from ghostos.prototypes.console import demo_console_app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostos demo in console",
    )
    parser.add_argument(
        "--ghost-id", '-g',
        help="ghost_id in demo/configs/ghosts.yml",
        type=str,
        default="baseline",
    )
    parser.add_argument(
        "--debug", "-d",
        help="debug mode",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--username", '-u',
        help="username",
        type=str,
        default="BrightRed",
    )
    parser.add_argument(
        "--session-id", '-s',
        help="session id",
        type=str,
        default=None,
    )
    parsed = parser.parse_args(sys.argv[1:])
    demo_console_app.run_console(
        ghost_id=parsed.ghost_id,
        debug=parsed.debug,
        username=parsed.username,
        session_id=parsed.session_id,
    )


if __name__ == "__main__":
    main()
