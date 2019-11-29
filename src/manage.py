from subprocess import check_output, check_call, call, Popen
import os
import ctypes
import sys

def setProxyEnv():
    newEnv = os.environ.copy()
    newEnv["HTTP_PROXY"] = 'http://proxy.apps.dhs.gov:80'
    newEnv["HTTPS_PROXY"] = 'http://proxy.apps.dhs.gov:80'
    return newEnv

def condaInstallHazus():
    messageBox = ctypes.windll.user32.MessageBoxW
    try:
        check_call('echo y | conda install -c nhrap hazus', shell=True)
        messageBox(None,"The Hazus Python package was successfully installed. Please reopen the utility.","Hazus", 0)
    except:
        print('Adding proxies and retrying...')
        proxyEnv = setProxyEnv()
        check_call('echo y | conda install -c nhrap hazus', shell=True, env=proxyEnv)
        messageBox(None,"The Hazus Python package was successfully installed. Please reopen the utility.","Hazus", 0)

def installHazus():
    messageBox = ctypes.windll.user32.MessageBoxW
    returnValue = messageBox(None,"The Hazus Python package is required to run this tool. Would you like to install it now?","Hazus",0x40 | 0x1)
    if returnValue == 1:
        import os
        output = check_output('conda config --show channels')
        channels = list(map(lambda x: x.strip(), str(output).replace('\\r\\n', '').split('-')))[1:]
        if not 'anaconda' in channels:
            call('conda config --add channels anaconda')
            print('anaconda channel added')
        if not 'conda' in channels and not 'forge' in channels:
            call('conda config --add channels conda-forge')
            print('conda-forge channel added')
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
        print('Installing the Hazus Python package, please wait...')
        try:
            condaInstallHazus()
        except:
            messageBox(None,"An error occured. The Hazus Python package was not installed. Please check your network settings and try again.","Hazus", 0)

def update():
    messageBox = ctypes.windll.user32.MessageBoxW
    returnValue = messageBox(None,"A newer version of the Hazus Python package was found. Would you like to install it now?","Hazus",0x40 | 0x1)
    if returnValue == 1:
        condaInstallHazus()

def checkForHazusUpdates():
    import requests
    import pkg_resources
    try:
        installedVersion = pkg_resources.get_distribution('hazus').version
        url = 'https://raw.githubusercontent.com/nhrap-dev/hazus/master/hazus/__init__.py'
        try:
            req = requests.get(url, timeout=0.5)
        except:
            os.environ["HTTP_PROXY"] = 'http://proxy.apps.dhs.gov:80'
            os.environ["HTTPS_PROXY"] = 'http://proxy.apps.dhs.gov:80'
            req = requests.get(url, timeout=0.5)
        reqList = req.text.split('\n')
        newestVersion = list(filter(lambda x: '__version__' in x, reqList))[0]
        replaceList = ['__version__', '=', "'", '"']
        for i in replaceList:
            newestVersion = newestVersion.replace(i, '')
        newestVersion = newestVersion.strip()
        if newestVersion != installedVersion:
            update()
        else:
            print('Hazus is up to date')
    except:
        installHazus()





"""
conda config --remove channels anaconda
conda config --remove channels conda-forge
"""
