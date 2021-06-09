try:
    try:
        from src.manage import Manage
        manage = Manage()
    except:
        from manage import Manage
        manage = Manage()
    manage.checkForToolUpdates()
    manage.checkForHazPyUpdates() # TODO: Remove or refactor this part - no longer needed (since env & tool will be together) - BC
except Exception as e:
    print(e)
    import ctypes
    import sys
    messageBox = ctypes.windll.user32.MessageBoxW
    messageBox(0, u"Unexpected error:" + str(sys.exc_info()[0]) + u" | If this problem persists, contact hazus-support@riskmapcds.com.", u"HazPy", 0x1000)