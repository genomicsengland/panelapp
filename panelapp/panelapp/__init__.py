import os


def get_package_version():
    version = ''

    init_path = os.path.normpath(
        os.path.join(
            os.path.join(
                os.path.join(
                    os.path.abspath(__file__),
                    os.pardir
                ),
                os.pardir
            ),
            '__init__.py'
        )
    )

    with open(init_path, 'r') as f:
        for line in f:
            if line.find('__version__') == 0:
                version = line.replace('__version__ = ', '').strip().strip("'").strip('"')

    return version


__version__ = get_package_version()
