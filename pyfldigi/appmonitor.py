'''TBD
'''

import os
import sys
import time
import subprocess
import xmlrpc.client


class ApplicationMonitor(object):

    '''Responsible for launching and terminating the FLDIGI application process, using subprocess.Popen()

    .. note:: Commandline arguments can be found on the following links:

        * `Official Documentation page <http://www.w1hkj.com/FldigiHelp-3.21/html/command_line_switches_page.html/>`_
        * `Man page for FLDIGI <https://www.dragonflybsd.org/cgi/web-man?command=fldigi&section=1/>`_
    '''

    def __init__(self, hostname='127.0.0.1', port=7362):
        self.platform = sys.platform
        self.hostname = hostname
        self.port = int(port)
        if self.platform not in ['linux', 'win32']:
            raise Exception('You\'re probably using an OS that is unsupported.  Sorry about that.  I take pull requests.')
        self.client = xmlrpc.client.ServerProxy('http://{}:{}/'.format(self.hostname, self.port))
        self.process = None

    def start(self, headless=False, wfall_only=False):
        '''Start fldigi in the background

        :type: float

        :Example:

        >>> import pyfldigi
        >>> fldigi = pyfldigi.Client()
        >>> fldigi.rig.frequency  # read to demonstrate its initial value
        7070200.0
        >>> fldigi.rig.frequency = 7000000.0  # Set to 7 MHz
        >>> fldigi.rig.frequency  # read back to demonstrate that it changed
        7000000.0
        '''

        args = [self._get_path()]
        if self.platform == 'win32':
            # Currently, the app crashes if I pass in any params from the windows commandline.
            # For now just ignore all of the params if running this under windows.
            pass
        else:
            args.extend(['--arq-server-address', self.hostname])
            args.extend(['--arq-server-port', str(self.port)])
            if headless is True:
                if self.platform == 'win32':
                    raise Exception('cannot run headless with win32.  Headless mode is only supported on Linux.')
                else:  # Assumes cygwin, linux, and darwin can utilize xvfb to create a fake x server
                    args.insert(0, 'xvfb-run')  # http://manpages.ubuntu.com/manpages/zesty/man1/xvfb-run.1.html
                    args.append('-display')
                    args.append(':99')
            else:
                if wfall_only is True:  # consider this modal with 'headless'
                    args.append('--wfall-only')
            # args.extend(['-title', 'fldigi'])  # Set the title to something predictable.
        self.process = subprocess.Popen(args)
        start = time.time()
        while(1):
            try:
                if self.client.fldigi.name() == 'fldigi':
                    break
            except ConnectionRefusedError:
                pass
            if time.time() - start >= 10:
                break
            time.sleep(0.5)

    def stop(self, save_options=True, save_log=True, save_macros=True, force=True):
        '''Attempts to gracefully shut down fldigi.  Returns the error code.'''
        bitmask = int('0b{}{}{}'.format(int(save_macros), int(save_log), int(save_options)), 0)
        self.client.fldigi.terminate(bitmask)
        if self.process is not None:
            error_code = self.process.wait(timeout=2)
            if force is True:
                if error_code is None:
                    self.process.terminate()  # attempt to terminate
                    error_code = self.process.wait(timeout=2)
                    if error_code is None:
                        error_code = self.process.kill()
            self.process = None
            return error_code

    def kill(self):
        '''Kills fldigi.  NOTE: Please try and use stop() before doing this to shut down fldigi gracefully.
        Consider kill() the last resort.'''
        if self.process is not None:
            self.process.kill()
            self.process = None
        # TODO: Interpret error codes and raise custom exceptions

    def _get_path(self):
        if self.platform == 'win32':
            #  Below is a clever way to return a list of fldigi versions.  This would fail if the user
            #     did not install fldigi into Program Files.
            fldigi_versions = [d for d in os.listdir(os.environ["ProgramFiles(x86)"]) if 'fldigi' in d.lower()]
            if len(fldigi_versions) == 0:
                raise FileNotFoundError('Cannot find the path to fldigi.  Is it installed?')
            elif len(fldigi_versions) == 1:
                path = os.path.join(os.environ["ProgramFiles(x86)"], fldigi_versions[0])
                # Check to see if fldigi.exe is in the folder
                if 'fldigi.exe' in os.listdir(path):
                    return os.path.join(path, 'fldigi.exe')
            else:
                raise Exception('Found more than one version of fldigi.  Uninstall one.')
        else:  # Assume all other OS's are smart enough to place fldigi in PATH
            return 'fldigi'

    def is_running(self):
        '''Get the process ID from the operating system'''
        if self.process is None:
            return False
        else:
            p = self.process.poll()  # will return None if not yet finished.  Will return the exit code if it has finished.
            if p is None:
                return False
            else:
                self.returncode = p


if __name__ == '__main__':
    a = ApplicationMonitor()
    a.start()
    for i in range(0, 5):
        print(a.is_running())
        time.sleep(1)
    errorCode = a.stop()
    print(errorCode)