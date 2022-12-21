# Copyright 2020-2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gettext import gettext as _
from gi.repository import Gio, GObject, Gtk

from blanket.sound import SoundObject, SoundPlayer


class PlayPauseButton(Gtk.Button):
    __gtype_name__ = 'PlayPauseButton'

    playing = GObject.Property(type=bool, default=True)

    def __init__(self):
        super().__init__()

        self.add_css_class('playpause')
        self.add_css_class('circular')
        self.add_css_class('suggested-action')

        self.connect('notify::playing', self._on_playing_changed)

    def _on_playing_changed(self, _object, _pspec):
        if self.playing:
            self.set_icon_name('media-playback-pause-symbolic')
        else:
            self.set_icon_name('media-playback-start-symbolic')


class SoundItem(Gtk.Box):
    __gtype_name__ = 'SoundItem'

    playing = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    icon_name = GObject.Property(type=str)

    def __init__(self):
        super().__init__()

        self.props.orientation = Gtk.Orientation.VERTICAL
        self.props.spacing = 6
        self.add_css_class('sound-item')

        self.connect('notify::playing', self._playing_changed)

        self.icon = Gtk.Image(pixel_size=64, halign=Gtk.Align.CENTER)
        self.bind_property('icon_name', self.icon, 'icon_name', GObject.BindingFlags.SYNC_CREATE)
        self.append(self.icon)

        self.label = Gtk.Label()
        self.bind_property('title', self.label, 'label', GObject.BindingFlags.SYNC_CREATE)
        self.append(self.label)

    def _playing_changed(self, _object, _pspec):
        if not self.playing:
            self.icon.remove_css_class('accent')
        elif not self.icon.has_css_class('accent'):
            self.icon.add_css_class('accent')


@Gtk.Template(resource_path='/com/rafaelmardojai/Blanket/volume-row.ui')
class VolumeRow(Gtk.ListBoxRow):
    __gtype_name__ = 'VolumeRow'

    title = GObject.Property(type=str)
    volume = GObject.Property(type=float)

    def __init__(self):
        super().__init__()


@Gtk.Template(resource_path='/com/rafaelmardojai/Blanket/sound-row.ui')
class SoundRow(Gtk.ListBoxRow):
    __gtype_name__ = 'SoundRow'

    """
    SoundRow
    Widget to show, play and manage a sound
    """

    custom = GObject.Property(type=bool, default=False)

    icon = Gtk.Template.Child()
    title = Gtk.Template.Child()
    volume = Gtk.Template.Child()
    remove_btn = Gtk.Template.Child()

    def __init__(self, sound, model):
        super().__init__()

        self.custom = sound.custom

        self.first_load = True
        # SoundObject
        self.sound = sound
        # Gio.ListStore
        self.model = model
        # Create a new SoundPlayer
        self.player = SoundPlayer(self.sound)

        # Set title
        self.title.set_label(self.sound.title)
        # Connect scale with volume function
        self.volume.connect('value-changed', self._on_volume_changed)
        # Load saved volume
        self.volume.set_value(self.sound.saved_volume)
        # Set icon
        self.icon.props.icon_name = self.sound.icon_name
        # Connect remove
        self.remove_btn.connect('clicked', self.remove)

        # Connect mainplayer preset-changed signal
        self.sound.mainplayer.connect(
            'preset-changed',
            self._on_preset_changed
        )
        # Connect mainplayer reset-volumes signal
        self.sound.mainplayer.connect(
            'reset-volumes',
            self._on_reset_volumes
        )

    def remove(self, _button):
        if self.sound.custom:
            # Remove audio from list
            self.model.remove(self.get_index())
            # Remove player
            self.player.remove()
            # Remove audio from settings
            self.sound.remove()

    def toggle_mute(self):
        # Toggle player mute state
        if self.sound.saved_volume > 0:
            self.sound.saved_mute = not self.sound.saved_mute

        if self.sound.saved_mute:
            self.player.set_virtual_volume(0)
        elif self.sound.saved_volume > 0:
            self.player.set_virtual_volume(self.sound.saved_volume)
        else:
            self.volume.set_value(0.5)

        self._update_active_state()

    def _on_volume_changed(self, scale):
        # Round volume value
        volume = round(scale.get_value(), 2)
        # Save volume on settings
        self.sound.saved_volume = volume

        if self.first_load and self.sound.saved_mute:
            self.player.set_virtual_volume(0)
            self.first_load = False
        else:
            self.player.set_virtual_volume(volume)
            self.sound.saved_mute = False

        self._update_active_state()

    def _update_active_state(self):
        if self.sound.saved_mute or self.sound.saved_volume == 0:
            self._show_active_indicator(False)
        else:
            self._show_active_indicator(True)

    def _show_active_indicator(self, show):
        if not show:
            self.icon.remove_css_class('accent')
        elif not self.icon.has_css_class('accent'):
            self.icon.add_css_class('accent')

    def _on_preset_changed(self, _player):
        self.first_load = True
        self.volume.set_value(self.sound.saved_volume)

    def _on_reset_volumes(self, _player):
        self.volume.set_value(0.0)


class SoundsGroup(Gtk.Box):
    __gtype_name__ = 'SoundsGroup'
    """
    SoundsGroup
    Group SoundRow with a title
    """

    __gsignals__ = {
        'add-clicked': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, title, custom=False):
        super().__init__()

        # Setup box props
        self.props.orientation = Gtk.Orientation.VERTICAL
        self.props.spacing = 6

        # Create GioListStore to store sounds
        self.model = Gio.ListStore.new(SoundObject)

        # Create group name label
        label = Gtk.Label()
        label.props.label = title
        label.props.halign = Gtk.Align.START
        label.add_css_class('title-3')
        self.append(label)

        # Create group GtkListBox
        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class('boxed-list')
        self.append(self.listbox)

        # Bind GtkListBox with GioListStore
        self.listbox.bind_model(self.model, self._create_sound_widget)
        # Connect row activated signal
        self.listbox.connect('row-activated', self._on_row_activated)

        # Show add button if group is for custom sounds
        if custom:
            add_btn = Gtk.Button()
            add_btn.props.label = _('Add Custom Sound…')
            add_btn.connect('clicked', self.__on_add_clicked)
            self.append(add_btn)

    def add(self, sound):
        self.model.append(sound)

    def _create_sound_widget(self, sound):
        widget = SoundRow(sound, self.model)
        return widget

    def _on_row_activated(self, _list, row):
        if isinstance(row, SoundRow):
            # Toggle sound mute state
            row.toggle_mute()

    def __on_add_clicked(self, _button):
        self.emit('add-clicked')
