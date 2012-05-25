#!/usr/bin/python

import os
import logging

from gi.repository import Gtk, Gdk, Gio, GObject
from gi.repository import AppIndicator3 as AppIndicator

from gimpanel.debug import log_traceback, log_func
from gimpanel.ui import Handle
from gimpanel.common import CONFIG_ROOT
from gimpanel.controller import GimPanelController
from gimpanel.langpanel import LangPanel

log = logging.getLogger('GimPanel')

class GimPanel(Gtk.Window):
    def __init__(self, session_bus):
        Gtk.Window.__init__(self, type=Gtk.WindowType.POPUP)
        self.set_resizable(False)
        self.set_border_width(6)
        self.set_size_request(100, -1)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        handle = Handle()
        hbox.pack_start(handle, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       spacing=3)
        hbox.pack_start(vbox, True, True, 6)

        self._preedit_label = Gtk.Label()
        self._preedit_label.set_alignment(0, 0.5)
        vbox.pack_start(self._preedit_label, True, True, 0)

        self._separator = Gtk.Separator()
        vbox.pack_start(self._separator, False, False, 0)

        self._aux_label = Gtk.Label()
        self._aux_label.set_alignment(0, 0.5)
        vbox.pack_start(self._aux_label, True, True, 0)

        self._lookup_label = Gtk.Label()
        self._lookup_label.set_alignment(0, 0.5)
        vbox.pack_start(self._lookup_label, True, True, 0)

        self._show_preedit = False
        self._show_lookup = False
        self._show_aux = False

        self._cursor_x = 0
        self._cursor_y = 0
        self._cursor_h = 0

        self._controller = GimPanelController(session_bus, self)

        self.setup_indicator()

        self.langpanel = LangPanel(self._controller)
        self.langpanel.show_all()
        self.langpanel.hide()

        self.connect('destroy', self.on_gimpanel_exit)
        self.connect("size-allocate", lambda w, a: self._move_position())
        self.connect('realize', self.on_realize)

    def on_realize(self, widget):
        self._controller.PanelCreated()
        self._controller.PanelCreated2()
        self._controller.TriggerProperty('/Fcitx/im')

    @log_func(log)
    def on_gimpanel_exit(self, widget):
        self.langpanel.destroy()
        Gtk.main_quit()

    def setup_indicator(self):
        self.appindicator = AppIndicator.Indicator.new('gimpanel',
                                                       'fcitx-kbd',
                                                       AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.appindicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        menu = Gtk.Menu()

        item = Gtk.MenuItem(_('Quit'))
        item.connect('activate', self.on_gimpanel_exit)
        menu.append(item)

        menu.show_all()

        self.appindicator.set_menu(menu)

    def on_trigger_menu(self, widget, im):
        self._controller.TriggerProperty(im)

    def update_menu(self, args=None):
        menu = self.appindicator.get_menu()

        if args:
            for item in menu.get_children()[:-1]:
                item.destroy()

            if args[0]:
                menu.insert(Gtk.SeparatorMenuItem(), 0)

            group_item = None
            for i, arg in enumerate(args):
                log.debug("menu item: %s" % arg)
                item_name = arg.split(':')[1]
                item = Gtk.RadioMenuItem(item_name)
                if group_item:
                    item.set_property('group', group_item)
                if i == 0:
                    group_item = item
                if self.langpanel.get_current_im() == item_name:
                    item.set_active(True)

                item.connect('activate', self.on_trigger_menu, arg.split(':')[0])
                menu.insert(item, i)
        else:
            for item in menu.get_children()[:-2]:
                item.handler_block_by_func(self.on_trigger_menu)
                item.set_active(item.get_label() == self.langpanel.get_current_im())
                item.handler_unblock_by_func(self.on_trigger_menu)

        menu.show_all()

    def ExecMenu(self, *args):
        self.update_menu(args[0])

    def UpdatePreeditText(self, text, attr):
        self._preedit_label.set_markup('<span color="#c131b5">%s</span>' % text)

    def UpdateAux(self, text, attr):
        self._aux_label.set_markup('<span color="blue">%s</span>' % text)

    def UpdateLookupTable(self, *args):
        text = []
        highlight_first = (len(args[0]) > 1)
        for i, index in enumerate(args[0]):
            if i == 0 and highlight_first:
                text.append("%s<span bgcolor='#f07746' fgcolor='white'>%s</span> " % (index, args[1][i].strip()))
            else:
                text.append("%s%s" % (index, args[1][i]))

        self._lookup_label.set_markup(''.join(text))

    def ShowPreedit(self, to_show):
        self._show_preedit = to_show
        self._preedit_label.set_visible(self._show_preedit)
        self._separator.set_visible(self._show_preedit)
        if not self._show_preedit:
            self._preedit_label.set_text('')

    def ShowLookupTable(self, to_show):
        self._show_lookup = to_show
        if not self._show_lookup:
            self._lookup_label.set_text('')

    def ShowAux(self, to_show):
        self._show_aux = to_show
        self._aux_label.set_visible(self._show_aux)
        if not self._show_aux:
            self._aux_label.set_text('')

    def RegisterProperties(self, args):
        self.langpanel.reset_toolbar_items()

        for arg in args:
            prop_name = arg.split(':')[0]

            if prop_name in self.langpanel.fcitx_prop_dict.keys():
                setattr(self.langpanel, self.langpanel.fcitx_prop_dict[prop_name], arg)
            else:
                log.warning('RegisterProperties: No handle prop name: %s' % prop_name)

    def UpdateProperty(self, value):
        prop_name = value.split(':')[0]
        icon_name = value.split(':')[2]

        if prop_name in self.langpanel.fcitx_prop_dict.keys():
            if self.langpanel.is_default_im():
                self.appindicator.set_property("attention-icon-name", icon_name)
                self.appindicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            else:
                self.appindicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            setattr(self.langpanel, self.langpanel.fcitx_prop_dict[prop_name], value)
        else:
            log.warning('UpdateProperty: No handle prop name: %s' % prop_name)

    def Enable(self, enabled):
        self.update_menu()
        self.langpanel.set_visible(enabled)

    def do_visible_task(self):
        if self._preedit_label.get_text() or \
           self._aux_label.get_text() or \
           self._lookup_label.get_text():
            self.set_visible(True)
        else:
            self.set_visible(False)

    def _move_position(self):
        window_right = self._cursor_x + self.get_allocation().width
        window_bottom = self._cursor_y + self._cursor_h + self.get_allocation().height

        root_window = Gdk.get_default_root_window()
        screen_width, screen_height = root_window.get_width(), root_window.get_height()
        if window_right > screen_width:
            x = screen_width - self.get_allocation().width
        else:
            x = self._cursor_x

        if window_bottom > screen_height:
            y = self._cursor_y - self.get_allocation().height
        else:
            y = self._cursor_y + self._cursor_h

        log.debug("Move gimpanel to %sx%s" % (x, y))
        self.move(x, y)

    def run(self):
        self.show_all()
        self.do_visible_task()
        Gtk.main()
