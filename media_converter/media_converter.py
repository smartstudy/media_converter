import subprocess
from pyfileinfo import PyFileInfo
from media_converter.codecs import VideoCodec, AudioCodec, H264, AAC
from media_converter.tracks import Track, AudioTrack, VideoTrack


class MediaConverter:
    def __init__(self, tracks, dst):
        if not isinstance(tracks, list):
            tracks = [tracks]

        self._tracks = tracks
        self._dst = PyFileInfo(dst)
        self._command = None
        self._infiles = None
        self._start = None
        self._duration = None

    def convert(self, start=None, end=None, duration=None):
        self._start = start
        self._end = end
        self._duration = duration

        self._create_command()

        subprocess.call(self._command)

    @property
    def tracks(self):
        for track in self._tracks:
            if isinstance(track, Track):
                yield track
                continue

            for codec in self._get_default_codecs():
                if isinstance(codec, VideoCodec):
                    yield VideoTrack(track, codec)
                elif isinstance(codec, AudioCodec):
                    yield AudioTrack(track, codec)

    def _create_command(self):
        self._init_command()
        self._append_instreams()
        self._append_tracks()
        self._append_time_options()
        self._append_dst()

    def _init_command(self):
        self._command = ['/usr/local/bin/ffmpeg', '-y']
        self._infiles = []

    def _append_instreams(self):
        for track in self.tracks:
            instream = track.outstream.instream
            if instream.as_ffmpeg_instream() in self._infiles:
                continue

            self._infiles.append(instream.as_ffmpeg_instream())
            self._command.extend(instream.as_ffmpeg_instream())

    def _append_tracks(self):
        for track in self.tracks:
            instream = track.outstream.instream
            infile_index = self._infiles.index(instream.as_ffmpeg_instream())
            filter = track.outstream.filter_options_for_ffmpeg(infile_index)
            if len(filter) == 0:
                self._command.extend(['-map', f'{infile_index}:{instream.track_type}:{instream.track_index}'])
            else:
                self._command.extend(['-filter_complex', filter, '-map', '[vout0]'])

            self._command.extend(track.codec.options_for_ffmpeg())

    def _append_time_options(self):
        options = []
        if self._start is not None:
            options.extend(['-ss', str(self._start)])

        if self._duration is not None:
            options.extend(['-t', str(self._duration)])
        elif self._end is not None:
            options.extend(['-to', str(self._end)])

        if len(options) == 0 and self._has_not_timed_blank_instream():
            self._command.append('-shortest')
        else:
            self._command.extend(options)

    def _has_not_timed_blank_instream(self):
        for track in self.tracks:
            instream = track.outstream.instream
            if instream.is_blank() and instream.duration is None:
                return True

        return False

    def _append_dst(self):
        self._command.append(self._dst.path)

    def _get_default_codecs(self):
        default_codecs = {
            '.mkv': [H264, AAC],
            '.mp4': [H264, AAC],
            '.m4v': [H264],
            '.m4a': [AAC],
        }

        for codec in default_codecs[self._dst.extension.lower()]:
            yield codec()
