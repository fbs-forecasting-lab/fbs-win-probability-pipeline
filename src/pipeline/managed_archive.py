"""Bounded, non-extracting model archive reader shared by native and local checks.

Only regular payloads and inert per-member PAX timestamps are supported. Parse
extension records directly: tarfile's merged dictionary can hide duplicate keys
or silently ignore malformed records. Never apply a PAX path/link/size override.
"""

import re
import tarfile
import zlib

FILES = frozenset(('model.joblib', 'evaluation.json', 'calibration.json',
                   'holdout_predictions.csv', 'sample_predictions.csv',
                   'exclusions.json', 'model_metadata.json'))
MAX_BYTES = 32 * 1024 * 1024
MAX_TAR_BYTES = MAX_BYTES + 64 * 1024
TIMESTAMPS = frozenset(('atime', 'ctime', 'mtime', 'LIBARCHIVE.creationtime'))


def _require(condition):
    if not condition:
        raise ValueError('Invalid or unsafe managed archive.')


def _timestamps(payload):
    """Validate every length-delimited record, including uniqueness and its end."""
    _require(0 < len(payload) <= 4096)
    offset, seen = 0, set()
    while offset < len(payload):
        space = payload.find(b' ', offset)
        _require(space > offset)
        length = payload[offset:space]
        _require(re.fullmatch(rb'[1-9][0-9]{0,3}', length) is not None)
        end = offset + int(length)
        _require(space + 1 < end <= len(payload) and payload[end - 1:end] == b'\n')
        record = payload[space + 1:end - 1].decode('ascii')
        key, separator, value = record.partition('=')
        _require(separator and key in TIMESTAMPS and key not in seen
                 and re.fullmatch(r'[0-9]{1,20}(?:\.[0-9]{1,12})?', value) is not None)
        seen.add(key)
        offset = end


def read_archive(content, *, max_bytes=MAX_BYTES, max_tar_bytes=MAX_TAR_BYTES):
    """Return exactly seven canonical payloads without extracting or loading them.

    Check raw header checksums, record lengths, padding and two-block terminators.
    A single gzip member is allowed; concatenated streams/trailing bytes are not.
    All compressed, expanded and cumulative payload allocations are bounded.
    """
    _require(type(content) is bytes and 0 < len(content) <= max_bytes)
    try:
        if content.startswith(b'\x1f\x8b'):
            stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
            raw = stream.decompress(content, max_tar_bytes + 1)
            _require(stream.eof and not stream.unused_data and not stream.unconsumed_tail)
        else:
            raw = content
        _require(len(raw) <= max_tar_bytes and len(raw) % 512 == 0)
        artifacts, offset, total, root_seen, pending = {}, 0, 0, False, False
        while offset + 512 <= len(raw) and any(raw[offset:offset + 512]):
            member = tarfile.TarInfo.frombuf(raw[offset:offset + 512], 'utf-8', 'strict')
            _require(0 <= member.size <= max_bytes and not member.linkname)
            start = offset + 512
            end = start + member.size
            padded_end = start + ((member.size + 511) // 512) * 512
            _require(padded_end <= len(raw) and not any(raw[end:padded_end]))
            payload = raw[start:end]
            offset = padded_end
            if member.type == tarfile.XHDTYPE:
                _require(not pending)
                _timestamps(payload)
                pending = True
                continue
            if member.type == tarfile.DIRTYPE and member.name in ('.', './'):
                _require(not root_seen and member.size == 0)
                root_seen = True
            else:
                name = member.name[2:] if member.name.startswith('./') else member.name
                _require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                         and name in FILES and name not in artifacts)
                total += member.size
                _require(total <= max_bytes)
                artifacts[name] = payload
            pending = False
        _require(not pending and set(artifacts) == FILES
                 and len(raw) - offset >= 1024 and not any(raw[offset:]))
        return artifacts
    except (EOFError, tarfile.TarError, UnicodeError, ValueError, zlib.error):
        raise ValueError('Invalid or unsafe managed archive.') from None
