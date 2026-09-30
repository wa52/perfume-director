"""Render one explicit Spec for a Codex-guided review; never fabricate a critique."""
import argparse
from pathlib import Path
import poster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--product', default='assets/products/dior-jadore-retailer.png')
    parser.add_argument('--config', default='config.local.json')
    parser.add_argument('--background', help='Reuse a background image without AI regeneration')
    args = parser.parse_args()
    config = poster.read(args.config)
    spec = poster.validate(poster.read(args.spec))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.background:
        config['background_workflow'] = None
    poster.comfy_render(config, spec, args.product, output, args.background)
    print(output.resolve(), flush=True)


if __name__ == '__main__':
    main()
