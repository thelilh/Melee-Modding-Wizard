#!/usr/bin/env python
# This file's encoding: UTF-8
# This module allows access to files given (drag-and-dropped) onto the running program GUI
# Source: https://stackoverflow.com/questions/14267900/python-drag-and-drop-explorer-files-to-tkinter-entry-widget
# Modified by DRGN of Smashboards (Daniel R. Cappel)
# Version 2.1

import tkinter
import sys
import os
import platform

def _load_tkdnd(master):
    thisModulePath = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))

    system = platform.system().lower()
    if system == "windows":
        arch_folder = "x64" if sys.maxsize > 2**32 else "x86"
    elif system == "linux":
        arch_folder = "x86_x64" if sys.maxsize > 2**32 else "i686"
    elif system == "darwin":
        # assuming modern macs are arm64, adjust if needed
        arch_folder = "arm64" if platform.machine() == "arm64" else "x86_x64"
        system = "macos"
    else:
        print(f"Unsupported OS: {system}")
        return

    tkdndlib_dir = os.path.join(thisModulePath, "tkdnd295", system, arch_folder)

    if not os.path.isdir(tkdndlib_dir):
        print(f"Invalid tkdnd library path!: {tkdndlib_dir}")
        return

    master.tk.eval(f'global auto_path; lappend auto_path {{{tkdndlib_dir}}}')

    try:
        master.tk.eval('package require tkdnd')
        master._tkdnd_loaded = True
    except Exception as e:
        print(f"Failed to load tkdnd package: {e}")




class TkDnD(object):
    def __init__(self, master):
        if not getattr(master, '_tkdnd_loaded', False):
            _load_tkdnd(master)
        self.master = master
        self.tk = master.tk

    # Available pre-defined values for the 'dndtype' parameter:
    #   text/plain
    #   text/plain;charset=UTF-8
    #   text/uri-list

    def bindtarget(self, window, callback, dndtype, event='<Drop>', priority=50):
        cmd = self._prepare_tkdnd_func(callback)
        return self.tk.call('dnd', 'bindtarget', window, dndtype, event,
                cmd, priority)

    def bindtarget_query(self, window, dndtype=None, event='<Drop>'):
        return self.tk.call('dnd', 'bindtarget', window, dndtype, event)

    def cleartarget(self, window):
        self.tk.call('dnd', 'cleartarget', window)


    def bindsource(self, window, callback, dndtype, priority=50):
        cmd = self._prepare_tkdnd_func(callback)
        self.tk.call('dnd', 'bindsource', window, dndtype, cmd, priority)

    def bindsource_query(self, window, dndtype=None):
        return self.tk.call('dnd', 'bindsource', window, dndtype)

    def clearsource(self, window):
        self.tk.call('dnd', 'clearsource', window)


    def drag(self, window, actions=None, descriptions=None,
            cursorwin=None, callback=None):
        cmd = None
        if cursorwin is not None:
            if callback is not None:
                cmd = self._prepare_tkdnd_func(callback)
        self.tk.call('dnd', 'drag', window, actions, descriptions,
                cursorwin, cmd)


    _subst_format = ('%A', '%a', '%b', '%D', '%d', '%m', '%T',
            '%W', '%X', '%Y', '%x', '%y')
    _subst_format_str = " ".join(_subst_format)

    def _prepare_tkdnd_func(self, callback):
        funcid = self.master.register(callback, self._dndsubstitute)
        cmd = ('%s %s' % (funcid, self._subst_format_str))
        return cmd

    def _dndsubstitute(self, *args):
        if len(args) != len(self._subst_format):
            return args

        def try_int(x):
            x = str(x)
            try:
                return int(x)
            except ValueError:
                return x

        A, a, b, D, d, m, T, W, X, Y, x, y = args

        event = tkinter.Event()
        event.action = A       # Current action of the drag and drop operation.
        event.action_list = a  # Action list supported by the drag source.
        event.mouse_button = b # Mouse button pressed during the drag and drop.
        event.data = D         # The data that has been dropped.
        event.descr = d        # The list of descriptions.
        event.modifier = m     # The list of modifier keyboard keys pressed.
        event.dndtype = T
        event.widget = self.master.nametowidget(W)
        event.x_root = X       # Mouse pointer x coord, relative to the root win.
        event.y_root = Y
        event.x = x            # Mouse pointer x coord, relative to the widget.
        event.y = y

        event.action_list = str(event.action_list).split()
        for name in ('mouse_button', 'x', 'y', 'x_root', 'y_root'):
            setattr(event, name, try_int(getattr(event, name)))

        return (event, )