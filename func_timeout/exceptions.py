'''
    Copyright (c) 2016 Tim Savannah All Rights Reserved.

    Licensed under the Lesser GNU Public License Version 3, LGPLv3. You should have recieved a copy of this with the source distribution as
    LICENSE, otherwise it is available at https://github.com/kata198/func_timeout/LICENSE
'''

__all__ = ('FunctionTimedOut', 'RETRY_SAME_TIMEOUT')

RETRY_SAME_TIMEOUT = 'RETRY_SAME_TIMEOUT'

class FunctionTimedOut(BaseException):
    '''
        FunctionTimedOut - Exception raised when a function times out

        @property timedOutAfter - Number of seconds before timeout was triggered

        @property timedOutFunction - Function called which timed out
        @property timedOutArgs - Ordered args to function
        @property timedOutKwargs - Keyword args to function

        @method retry - Retries the function with same arguments, with option to run with original timeout, no timeout, or a different
          explicit timeout. @see FunctionTimedOut.retry
    '''


    def __init__(self, msg='', timedOutAfter=None, timedOutFunction=None, timedOutArgs=None, timedOutKwargs=None):

        self.timedOutAfter = timedOutAfter

        self.timedOutFunction = timedOutFunction
        self.timedOutArgs = timedOutArgs
        self.timedOutKwargs = timedOutKwargs

        if not msg:
            msg = self.getMsg()

        BaseException.__init__(self, msg)

        self.msg = msg


    def getMsg(self):
        '''
            getMsg - Generate a default message based on parameters to FunctionTimedOut exception'

            @return <str> - Message
        '''
        return 'Function %s (args=%s) (kwargs=%s) timed out after %f seconds.\n' %(self.timedOutFunction.__name__, repr(self.timedOutArgs), repr(self.timedOutKwargs), self.timedOutAfter)

    def retry(self, timeout=RETRY_SAME_TIMEOUT):
        '''
            retry - Retry the timed-out function with same arguments.

            @param timeout <float/RETRY_SAME_TIMEOUT/None> Default RETRY_SAME_TIMEOUT

                If RETRY_SAME_TIMEOUT : Will retry the function same args, same timeout
                If a float/int : Will retry the function same args with provided timeout
                If None : Will retry function same args no timeout

            @return - Returnval from function
        '''
        if timeout is None:
            return self.timedOutFunction(*(self.timedOutArgs), **self.timedOutKwargs)

        from .dafunc import func_timeout

        if timeout == RETRY_SAME_TIMEOUT:
            timeout = self.timedOutAfter

        return func_timeout(timeout, self.timedOutFunction, args=self.timedOutArgs, kwargs=self.timedOutKwargs)
