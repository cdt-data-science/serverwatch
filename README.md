# CDT ServerWatch Stuff

A small Flask-Bootstrap app that uses `ssh` and regex to query the cluster nodes whilst we have no scheduler.

At present, `PATH_DATA` is hardcoded, so it'll need changing if you want to run it locally. It also looks for your matriculation number in an environment variable `$DICE_USER`, these could do with going in a config file.

If you're running on DICE, just execute the following before running, or add to your shell's profile file (`.bash_profile`, `.zshrc` etc.):

~~~
export DICE_USER=USER
~~~

If not DICE:

~~~
export DICE_USER=<your_matric_number>
~~~

## Quick-start:

Clone the repo, make a virtualenv and install the required packages:

~~~bash
virtualenv venv-serverwatch
source venv-serverwatch/bin/activate
pip install -r src/requirements.txt
~~~

This makes use of Kerberos tickets, so make sure this is up to date, if DICE:

~~~bash
renc
~~~

Else:

~~~bash
kinit -l 5d $DICE_USER
aklog
~~~

Then to run locally:

~~~bash
flask --app=src
~~~

Or, to run over the network, make sure you're in the `src` folder:

~~~bash
python run.py
~~~

To kill either, just press `Ctrl+C` twice in the terminal window.