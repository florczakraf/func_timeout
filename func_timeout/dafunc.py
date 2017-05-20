
# vim: set ts=4 sw=4 expandtab :

'''
    Copyright (c) 2016, 2017 Tim Savannah All Rights Reserved.

    Licensed under the Lesser GNU Public License Version 3, LGPLv3. You should have recieved a copy of this with the source distribution as
    LICENSE, otherwise it is available at https://github.com/kata198/func_timeout/LICENSE
'''

import inspect
import threading
import time
import types

from .exceptions import FunctionTimedOut
from .StoppableThread import StoppableThread

__all__ = ('func_timeout', 'func_set_timeout')


def func_timeout(timeout, func, args=(), kwargs=None):
    '''
        func_timeout - Runs the given function for up to #timeout# seconds.

        Raises any exceptions #func# would raise, returns what #func# would return (unless timeout is exceeded), in which case it raises FunctionTimedOut

        @param timeout <float> - Maximum number of seconds to run #func# before terminating
        @param func <function> - The function to call
        @param args    <tuple> - Any ordered arguments to pass to the function
        @param kwargs  <dict/None> - Keyword arguments to pass to the function.

        @raises - FunctionTimedOut if #timeout# is exceeded, otherwise anything #func# could raise will be raised

        If the timeout is exceeded, FunctionTimedOut will be raised within the context of the called function every two seconds until it terminates,
        but will not block the calling thread (a new thread will be created to perform the join). If possible, you should try/except FunctionTimedOut
        to return cleanly, but in most cases it will 'just work'.

        Be careful of code like:
        def myfunc():
            while True:
                try:
                    dosomething()
                except Exception:
                    continue

        because it will never terminate.

        @return - The return value that #func# gives
    '''

    if not kwargs:
        kwargs = {}
    if not args:
        args = ()

    ret = []
    exception = []
    isStopped = False

    def funcwrap(args2, kwargs2):
        try:
            ret.append( func(*args2, **kwargs2) )
        except FunctionTimedOut:
            # Don't print traceback to stderr if we time out
            pass
        except Exception as e:
            if isStopped is False:
                # Don't capture stopping exception
                exception.append(e)

    thread = StoppableThread(target=funcwrap, args=(args, kwargs))
    thread.daemon = True

    thread.start()
    thread.join(timeout)

    stopException = None
    if thread.isAlive():
        isStopped = True
        stopException = FunctionTimedOut 
        thread._stopThread(stopException)
        thread.join(.1)
        raise FunctionTimedOut('Function %s (args=%s) (kwargs=%s) timed out after %f seconds.\n' %(func.__name__, str(args), str(kwargs), timeout))

    if exception:
        raise exception[0]

    if ret:
        return ret[0]


def func_set_timeout(timeout, allowOverride=False):
    '''
        set_timeout - Wrapper to run a function with a given/calculated timeout (max execution time).
            Optionally (if #allowOverride is True), adds a paramater, "forceTimeout", to the
            function which, if provided, will override the default timeout for that invocation.

            If #timeout is provided as a lambda/function, it will be called
              prior to each invocation of the decorated function to calculate the timeout to be used
              for that call, based on the arguments passed to the decorated function.
              
              For example, you may have a "processData" function whose execution time
              depends on the number of "data" elements, so you may want a million elements to have a 
              much higher timeout than seven elements.)

            If #allowOverride is True AND a kwarg of "forceTimeout" is passed to the wrapped function, that timeout
             will be used for that single call.

        @param timeout <float OR lambda/function> - 
        
            **If float:**
                Default number of seconds max to allow function to execute
                  before throwing FunctionTimedOut
            
            **If lambda/function:

                 If a function/lambda is provided, it will be called for every
                  invocation of the decorated function (unless #allowOverride=True and "forceTimeout" was passed) 
                  to determine the timeout to use based on the arguments to the decorated function.

                    The arguments as passed into the decorated function will be passed to this function.
                     They either must match exactly to what the decorated function has, OR
                      if you prefer to get the *args (list of ordered args) and **kwargs ( key : value  keyword args form),
                      define your calculate function like:
                        
                        def calculateTimeout(*args, **kwargs):
                            ...
                    
                      or lambda like:

                        calculateTimeout = lambda *args, **kwargs : ...

                    otherwise the args to your calculate function should match exactly the decorated function.


        @param allowOverride <bool> Default False, if True adds a keyword argument to the decorated function,
            "forceTimeout" which, if provided, will override the #timeout. If #timeout was provided as a lambda / function, it
             will not be called.

        @throws FunctionTimedOut If time alloted passes without function returning naturally

        @see func_timeout
    '''
    # Try to be as efficent as possible... don't compare the args more than once

    #  Helps closure issue on some versions of python
    defaultTimeout = copy.copy(timeout)

    isTimeoutAFunction = bool( issubclass(timeout.__class__, (types.FunctionType, types.MethodType, types.LambdaType, types.BuiltinFunctionType, types.BuiltinMethodType) ) )

    if not isTimeoutAFunction:
        if not issubclass(timeout.__class__, (float, int)):
            try:
                timeout = float(timeout)
            except:
                raise ValueError('timeout argument must be a float/int for number of seconds, or a function/lambda which gets passed the function arguments and returns a calculated timeout (as float or int). Passed type: < %s > is not of any of these, and cannot be converted to a float.' %( timeout.__class__.__name__, ))


    if not allowOverride and not isTimeoutAFunction:
        # Only defaultTimeout provided. Simple function wrapper
        def _function_decorator(func):

            return lambda *args, **kwargs : func_timeout(defaultTimeout, func, args=args, kwargs=kwargs)

#            def _function_wrapper(*args, **kwargs):
#                return func_timeout(defaultTimeout, func, args=args, kwargs=kwargs)
#            return _function_wrapper
        return _function_decorator

    if not isTimeoutAFunction:
        # allowOverride is True and timeout is not a function. Simple conditional on every call
        def _function_decorator(func):
            def _function_wrapper(*args, **kwargs):
                if 'forceTimeout' in kwargs:
                    useTimeout = kwargs.pop('forceTimeout')
                else:
                    useTimeout = defaultTimeout

                return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

            return _function_wrapper
        return _function_decorator


    # At this point, timeout IS known to be a function.
    timeoutFunction = timeout

    if allowOverride:
        # Could use a lambda here... but want traceback to highlight the calculate function,
        #  and not the invoked function
        def _function_decorator(func):
            def _function_wrapper(*args, **kwargs):
                if 'forceTimeout' in kwargs:
                    useTimeout = kwargs.pop('forceTimeout')
                else:
                    useTimeout = timeoutFunction(*args, **kwargs)

                return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

            return _function_wrapper
        return _function_decorator

    # Cannot override, and calculate timeout function
    def _function_decorator(func):
        def _function_wrapper(*args, **kwargs):
            useTimeout = timeoutFunction(*args, **kwargs)

            return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

        return _function_wrapper
    return _function_decorator


# vim: set ts=4 sw=4 expandtab :
