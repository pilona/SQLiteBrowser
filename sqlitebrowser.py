#! /usr/bin/env python3

from signal import signal, SIGINT, SIG_DFL
import sqlite3
from gi.repository import Gtk, Gdk


# http://stackoverflow.com/questions/11996394/is-there-a-way-to-get-a-schema-of-a-database-from-within-python
# https://www.sqlite.org/datatype3.html
# http://stackoverflow.com/questions/1447187/embed-a-spreadsheet-table-in-a-pygtk-application
# http://lazka.github.io/pgi-docs/Gtk-3.0/classes/
# https://developer.gnome.org/gtk3/stable/ch03.html
# http://python-gtk-3-tutorial.readthedocs.org/en/latest/index.html


class SqliteBrowser(Gtk.Window):
    def __init__(self, db):
        super().__init__(title='-'.join([self.__class__.__name__, db]))

        self.db = sqlite3.connect(db)
        self.db.row_factory = sqlite3.Row
        self._loaddb()

        ctrl = Gdk.ModifierType.CONTROL_MASK
        alt = Gdk.ModifierType.MOD1_MASK
        self._bindings = [({(None, Gdk.KEY_q)}, self.destroy),
                          ({(ctrl, Gdk.KEY_z)}, self.iconify),
                          ({(ctrl, Gdk.KEY_r)}, self._reloaddb),
                          ({(ctrl, Gdk.KEY_o)}, self._promptdb)]
        self.connect('key-release-event', self._key_pressed)

    def _loaddb(self, db=None):
        if db is not None:
            self.db.close()
            self.db = db
            self.remove(self.get_child())

        tables = [row
                  for row, *_
                  in self.db.execute('''
                                     SELECT name
                                     FROM sqlite_master
                                     WHERE type = 'table' AND
                                           name NOT LIKE 'sqlite_%'
                                     ORDER BY name
                                     ''')]
        titles = [title
                  for title, *_
                  in self.db.execute('PRAGMA table_info(sqlite_master)')
                            .description]
        # TODO: Convert to dict of dict, where inner indexed by column name
        columns = {table: [dict(zip(titles, columnattrs))
                           for columnattrs
                           in self.db.execute('PRAGMA table_info({})'
                                              .format(table))]
                   for table in tables}
        columns = {table: {
                       ctuples['name']: {
                           attribute: value
                           for attribute, value
                           in ctuples.items()
                           if attribute != 'name'
                       }
                       for ctuples
                       in columns
                   }
                   for table, columns
                   in columns.items()}

        if len(tables) == 0:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING,
                                       Gtk.ButtonsType.OK,
                                       'Database has no tables')
            dialog.run()
            dialog.destroy()
            return
        else:
            del titles
            del tables

        # http://stackoverflow.com/questions/3164262/lazy-loaded-list-view-in-gtk
        vbox = Gtk.VBox()
        for table, cinfos in columns.items():
            vbox.add(Gtk.Label(table))
            order = list(cinfos)
            model = Gtk.ListStore(*[str] * len(order))
            # Yes, we must do string substitution here.
            query = self.db.execute('SELECT * FROM {}'.format(table))
            for row in query:
                model.append([str(row[column]) for column in order])

            view = Gtk.TreeView(model=model)
            for colno, col in enumerate(order):
                # What's confusing about TreeViewColumn is that text refers to
                # which column in the ListStore from which to get the data to
                # display.
                view.append_column(Gtk.TreeViewColumn(col,
                                                      Gtk.CellRendererText(),
                                                      text=colno))
            vbox.add(view)
        self.add(vbox)

    def _reloaddb(self, widget, event):
        self.loaddb()

    def _promptdb(self, db):
        self.reloaddb(choosedb())

    def _key_pressed(self, widget, event):
        if event.type == Gdk.EventType.KEY_RELEASE:
            for keys, callback in self._bindings:
                for mask, key in keys:
                    if event.keyval == key:
                        if mask is not None:
                            if event.state & mask:
                                callback()
                        else:
                            callback()


def choosedb():
    dialog = Gtk.FileChooserDialog(title='Open DB…',
                                   action=Gtk.FileChooserAction.OPEN,
                                   buttons=[Gtk.STOCK_CANCEL,
                                            Gtk.ResponseType.CANCEL,
                                            Gtk.STOCK_OPEN,
                                            Gtk.ResponseType.OK])
    response = dialog.run()
    try:
        if response == Gtk.ResponseType.OK:
            return dialog.get_filename()
        else:
            raise RuntimeError()
    finally:
        dialog.destroy()


if __name__ == '__main__':
    from sys import exit
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('db', nargs='?')
    args = parser.parse_args()

    if args.db is None:
        try:
            args.db = choosedb()
        except:
            exit(1)

    gui = SqliteBrowser(args.db)
    gui.connect('delete-event', Gtk.main_quit)
    signal(SIGINT, SIG_DFL)
    gui.show_all()
    Gtk.main()
