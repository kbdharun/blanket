# Copyright 2020-2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import GObject

from blanket.define import RES_PATH
from blanket.main_player import MainPlayer
from blanket.player import Player
from blanket.settings import Settings


class Sound(GObject.Object):
    """
    Describe a sound with it's properties
    """
    __gtype_name__ = 'Sound'

    playing = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    icon_name = GObject.Property(type=str)

    def __init__(self, name, uri=None, title=None, custom=False, **kwargs):
        super().__init__(**kwargs)

        resource = f'resource:{RES_PATH}/sounds/{name}.ogg'
        icon = 'com.rafaelmardojai.Blanket-{}'

        self._player = None

        self.name = name
        self.uri = uri if uri else resource
        self.title = title if title else name
        self.icon_name = icon.format('sound-wave' if custom else name)
        self.custom = custom

        self.connect('notify::playing', self._playing_changed)
        # Set saved playing state
        if not self.saved_mute:
            self.playing = not self.saved_mute

        # Connect mainplayer preset-changed signal
        MainPlayer.get().connect(
            'preset-changed',
            self._on_preset_changed
        )

        # Connect mainplayer reset-volumes signal
        MainPlayer.get().connect(
            'reset-volumes',
            self._on_reset_volumes
        )

    @property
    def player(self):
        if self._player is None:
            self._player = Player(self)
        return self._player

    @GObject.Property(type=float)
    def saved_volume(self):
        return Settings.get().get_sound_volume(self.name)

    @saved_volume.setter
    def saved_volume(self, volume):
        volume = round(volume, 2)
        self.player.set_virtual_volume(volume)
        Settings.get().set_sound_volume(self.name, volume)

        if volume != 0 and not self.playing:
            self.playing = True

    @property
    def saved_mute(self):
        return Settings.get().get_sound_mute(self.name)

    @saved_mute.setter
    def saved_mute(self, mute):
        Settings.get().set_sound_mute(self.name, mute)

    def remove(self):
        if self.custom:
            self.player.set_virtual_volume(0)
            Settings.get().remove_custom_audio(self.name)

    def _playing_changed(self, _object, _pspec):
        # Toggle player mute state
        if self.playing:
            if self.saved_volume > 0:
                self.player.set_virtual_volume(self.saved_volume)
            else:
                self.player.set_virtual_volume(0.5)
                self.saved_volume = 0.5
        else:
            self.player.set_virtual_volume(0)

        self.saved_mute = not self.playing  # Save playing state

    def _on_preset_changed(self, _player, _preset):
        self.notify('saved_volume')
        self.playing = not self.saved_mute

    def _on_reset_volumes(self, _player):
        self.saved_volume = 0.0
        self.playing = False
