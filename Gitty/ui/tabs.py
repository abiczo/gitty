from datetime import datetime

import gobject
import gtk

from Gitty.git.client import Client
from Gitty.git.commits import Commit
from Gitty.ui.commits import CommitsTree, ReferencesTree
from Gitty.ui.sourceview import SourceView


class ProjectTab(gtk.VBox):
    def __init__(self, path):
        gtk.VBox.__init__(self, False, 0)
        self.client = Client(path)

        self.set_border_width(6)

        paned = gtk.VPaned()
        paned.show()
        self.pack_start(paned, True, True, 0)

        widget = self.__build_top_pane()
        widget.show()
        paned.pack1(widget, True)

        widget = self.__build_bottom_pane()
        widget.show()
        paned.pack2(widget, False)

    def __build_top_pane(self):
        def on_references_toggled(toggle):
            if toggle.get_active():
                self.refs_swin.show()
            else:
                self.refs_swin.hide()

        vbox = gtk.VBox(False, 6)

        buttonbox = gtk.HButtonBox()
        buttonbox.show()
        vbox.pack_start(buttonbox, False, False, 0)
        buttonbox.set_layout(gtk.BUTTONBOX_START)

        refs_button = gtk.ToggleButton("References")
        refs_button.show()
        buttonbox.pack_start(refs_button, False, False, 0)
        refs_button.set_active(True)
        refs_button.connect('toggled', on_references_toggled)

        paned = gtk.HPaned()
        paned.show()
        vbox.pack_start(paned, True, True, 0)
        paned.set_position(200) # XXX Hardcoding sucks

        # Build the references list
        self.refs_swin = gtk.ScrolledWindow()
        self.refs_swin.show()
        paned.pack1(self.refs_swin, False)
        self.refs_swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.refs_swin.set_shadow_type(gtk.SHADOW_IN)

        self.refs_tree = ReferencesTree()
        self.refs_tree.show()
        self.refs_swin.add(self.refs_tree)
        self.refs_tree.connect('reference_changed',
            lambda w, ref: self.commits_tree.select_reference(ref))

        # Build the commits list
        swin = gtk.ScrolledWindow()
        swin.show()
        paned.pack2(swin, True)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        swin.set_shadow_type(gtk.SHADOW_IN)

        self.commits_tree = CommitsTree()
        self.commits_tree.show()
        swin.add(self.commits_tree)

        self.commits_tree.connect('commit_changed', self.on_commit_changed)
        self.commits_tree.connect('references_changed',
                                  lambda w, refs: self.refs_tree.load(refs))

        self.commits_tree.update_commits()

        return vbox

    def __build_bottom_pane(self):
        vbox = gtk.VBox(False, 6)

        hbox = gtk.HBox(False, 6)
        hbox.show()
        vbox.pack_start(hbox, False, False, 0)

        label = gtk.Label("<b>SHA1 ID:</b>")
        label.show()
        hbox.pack_start(label, False, False, 0)
        label.set_use_markup(True)

        self.sha1_label = gtk.Label()
        self.sha1_label.show()
        hbox.pack_start(self.sha1_label, False, False, 0)
        self.sha1_label.set_max_width_chars(40)
        self.sha1_label.set_selectable(True)

        diff_options_hbox = gtk.HBox(False, 0);
        diff_options_hbox.show()
        vbox.pack_start(diff_options_hbox, False, False, 0)

        context_hbox = gtk.HBox(False, 0)
        context_hbox.show()

        context_label = gtk.Label("Lines of context: ")
        context_label.show()
        context_hbox.pack_start(context_label, False, False, 0)

        self.context_button = gtk.SpinButton(gtk.Adjustment(3, 0, 100, 1, 10))
        self.context_button.set_numeric(True)
        self.context_button.connect("value-changed", self.on_context_changed)
        self.context_button.show();
        context_hbox.pack_start(self.context_button, False, False, 0)

        diff_options_hbox.pack_start(context_hbox, False, False, 0)

        self.ignore_space_button = gtk.CheckButton("Ignore space change")
        self.ignore_space_button.connect("toggled",
                                         self.on_ignore_space_toggled)
        self.ignore_space_button.show()
        diff_options_hbox.pack_start(self.ignore_space_button, False, False,
                                     24)

        paned = gtk.HPaned()
        paned.show()
        vbox.pack_start(paned, True, True, 0)

        self.content_notebook = gtk.Notebook()
        self.content_notebook.show()
        paned.pack1(self.content_notebook, True)

        self.diff_viewer = SourceView()
        self.diff_viewer.show()
        self.content_notebook.append_page(self.diff_viewer, gtk.Label("Diff"))
        self.diff_viewer.set_mimetype("text/x-patch")

        self.old_version_view = SourceView()
        self.old_version_view.show()
        self.content_notebook.append_page(self.old_version_view,
                                          gtk.Label("Old Version"))
        self.old_version_view.set_mimetype("text/x-patch")

        self.new_version_view = SourceView()
        self.new_version_view.show()
        self.content_notebook.append_page(self.new_version_view,
                                          gtk.Label("New Version"))
        self.new_version_view.set_mimetype("text/x-patch")

        return vbox

    def on_commit_changed(self, widget, commit):
        self.sha1_label.set_text(commit.commit_sha1)

        context_lines = self.context_button.get_value_as_int()
        ignore_space_change = self.ignore_space_button.get_active()

        diff = self.get_commit_contents(commit, True, True,
                                        context_lines, ignore_space_change)
        self.diff_viewer.set_text(diff)

        diff_old = self.get_commit_contents(commit, True, False,
                                            context_lines, ignore_space_change)
        self.old_version_view.set_text(diff_old)

        diff_new = self.get_commit_contents(commit, False, True,
                                            context_lines, ignore_space_change)
        self.new_version_view.set_text(diff_new)

    def on_references_clicked(self, widget):
        pass

    def on_context_changed(self, widget):
        if self.commits_tree.selected_commit is not None:
            self.on_commit_changed(self.commits_tree,
                                   self.commits_tree.selected_commit)

    def on_ignore_space_toggled(self, widget):
        if self.commits_tree.selected_commit is not None:
            self.on_commit_changed(self.commits_tree,
                                   self.commits_tree.selected_commit)

    def get_commit_contents(self, commit, show_old=True, show_new=True,
                            context_lines=3, ignore_space_change=False):
        diff = self.client.diff_tree(commit.commit_sha1, context_lines,
                                     ignore_space_change)

        header = self.client.get_commit_header(commit.commit_sha1)

        contents  = "Author:    %s  %s\n" % (header["author"]["name"],
                                             header["author"]["time"])
        contents += "Committer: %s  %s\n" % (header["committer"]["name"],
                                             header["committer"]["time"])
        if "parent" in header:
            contents += "Parent:    %s (%s)\n" % (header["parent"], "")
        contents += "Child:     %s (%s)\n" % ("", "")
        contents += "Branch:    %s\n" % ("")

        contents += "\n%s\n\n" % header["message"]

        contents += self.filter_diff(diff, show_old, show_new)

        return contents

    def filter_diff(self, diff_output, show_old, show_new):
        diff_lines = []
        in_header = True
        is_merge = False

        for line in diff_output.split('\n'):
            if line.startswith("diff "):
                in_header = True
                is_merge = line.startswith("diff --cc")
                diff_lines.append(line)
            elif line.startswith("@@"):
                in_header = False
                diff_lines.append(line)
            elif in_header:
                diff_lines.append(line)
            else:
                # no old/new version distinction for merge diffs
                if is_merge or \
                   (not line.startswith("-") and not line.startswith("+")) or \
                   (line.startswith("-") and show_old) or \
                   (line.startswith("+") and show_new):
                    diff_lines.append(line)

        return "\n".join(diff_lines)
