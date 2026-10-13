import argparse
from pathlib import Path
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['start', 'stop'])
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
env_file = project / '.env'
if not env_file.is_file():
    raise SystemExit('Copy .env.example to .env and fill in its values first.')

command = ['docker', 'compose', '--env-file', str(env_file)]
if args.action == 'start':
    subprocess.run(command + ['up', '-d', 'web'], cwd=project, check=True)
    print('Odoo is starting. Open the port set in .env; login admin. See docker compose logs -f web.')
else:
    subprocess.run(command + ['down'], cwd=project, check=True)
