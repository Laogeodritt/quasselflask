import os
from os import path

### EDIT HERE ###

# path to the quasselflask virtualenv
virtualenv_dir = '/path/to/quasselflask/virtualenv'

# path to the 'instance' directory containing quasselflask config files
config_dir = '/path/to/quasselflask/instance'

### STOP EDITING ###

if config_dir:
    os.environ['QF_CONFIG_PATH'] = config_dir

# load the virtualenv
if virtualenv_dir:
    activate_this = path.join(virtualenv_dir, 'bin', 'activate_this.py')
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

# load the application
import quasselflask.run
from quasselflask import app as application

