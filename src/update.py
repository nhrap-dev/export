try:
    try:
        from src.manage_new import Manage
        manage = Manage()
    except:
        from manage import Manage
        manage = Manage()
    try:
        manage.checkForUpdates()
    except Exception as e:
        print(e)
except:
    import ctypes
    import sys
    messageBox = ctypes.windll.user32.MessageBoxW
    messageBox(0, u"Unexpected error:" + str(sys.exc_info()[0]) + u" | If this problem persists, contact hazus-support@riskmapcds.com.", u"HazPy", 0x1000)