"""Regression signal for a silently black/constant generated background."""
import argparse
from PIL import Image, ImageStat


def check(path):
    with Image.open(path) as image:
        rgb = image.convert('RGB')
        extrema = rgb.getextrema()
        spread = max(high-low for low, high in extrema)
        if spread <= 1:
            raise ValueError(f'Invalid generated background: constant/black image {extrema}')
        return {'extrema': extrema, 'stddev': ImageStat.Stat(rgb).stddev}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    print(check(parser.parse_args().path))
