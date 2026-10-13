import configparser
import os
from pathlib import Path
import re
from string import Template
import subprocess


def load_config():
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', os.environ['DB_NAME']):
        raise ValueError('DB_NAME must contain only letters, digits and underscores.')
    for name in ('DB_PASSWORD', 'MASTER_PASSWORD', 'ADMIN_PASSWORD'):
        value = os.environ[name]
        if not value or '\n' in value or '\r' in value:
            raise ValueError(name + ' must be nonempty and contain no line breaks.')
    template = Path('/workspace/config/odoo.conf').read_text()
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(Template(template).substitute(os.environ))
    return config


def main():
    config = load_config()
    path = Path('/tmp/equipment-odoo.conf')
    path.touch(mode=0o600)
    with path.open('w') as stream:
        config.write(stream)
    base = ['odoo', '--config', str(path)]
    subprocess.run(base + [
        '--init', 'equipment_assignment', '--without-demo=all', '--stop-after-init', '--no-http',
    ], check=True)
    subprocess.run(
        base[:1] + ['shell'] + base[1:] + ['--no-http'],
        input=(
            "import os\n"
            "env.ref('base.user_admin').write({'password': os.environ['ADMIN_PASSWORD']})\n"
            "env['ir.config_parameter'].set_param('report.url', 'http://127.0.0.1:8069')\n"
            "env.cr.commit()\n"
        ),
        text=True, check=True,
    )
    os.execvp('odoo', base)


if __name__ == '__main__':
    main()
