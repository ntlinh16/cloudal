import sys

from argparse import ArgumentParser

from parsers import PARSERS
from controller import ParsingController
from helpers import get_logger

logger = get_logger("ParsingResults")


def main(options):
    parser = ArgumentParser(prog='parse_result')

    parser.add_argument('-i', '--input', dest='input', type=str, required=True,
                        help='The path to the result directory.')
    parser.add_argument('-o', '--output', dest='output', type=str, required=True,
                        help='The path to the output result file.')
    parser.add_argument('-p',
                        dest='parsers',
                        required=True,
                        nargs="+",
                        choices=[parser_name for parser_name in PARSERS],
                        help='Parser to use')
    parser.add_argument('-f',
                        dest='output_format',
                        choices=['csv', 'xlsx'],
                        help='Output format')

    args = parser.parse_args()
    if args.output_format is None:
        args.output_format = 'csv'
    logger.info('')
    logger.info('-' * 20)
    logger.info('Running with the following parameters: %s' % args)

    parsing_controller = ParsingController(args.input, args.output, args.parsers)
    parsed_df = parsing_controller.parse()
    parsing_controller.write_result(parsed_df, args.output_format)


if __name__ == "__main__":
    main(sys.argv[1:])
