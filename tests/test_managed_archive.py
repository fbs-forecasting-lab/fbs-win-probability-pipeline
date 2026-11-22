"""Byte-level adversarial archive fixtures, with no model loading or network."""

import gzip
import tarfile
import unittest
from unittest.mock import patch

from src.pipeline.managed_archive import FILES, read_archive


def record(key, value):
    body = f' {key}={value}\n'.encode()
    length = len(body) + 1
    while length != len(body) + len(str(length)):
        length = len(body) + len(str(length))
    return str(length).encode() + body


def member(name, payload=b'', kind=tarfile.REGTYPE, link=''):
    header = tarfile.TarInfo(name)
    header.size, header.type, header.linkname = len(payload), kind, link
    return header.tobuf(format=tarfile.USTAR_FORMAT) + payload + b'\0' * (-len(payload) % 512)


class ManagedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('socket.create_connection', side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('offline')))
        self.files = {name: ('synthetic ' + name).encode() for name in sorted(FILES)}
        self.records = b''.join(record(k, '1795331812.0896530') for k in
                               ('atime', 'ctime', 'mtime', 'LIBARCHIVE.creationtime'))

    def tar(self, extension=None):
        parts = []
        for name, data in self.files.items():
            if extension is not None:
                parts.append(member('./PaxHeaders.X/' + name, extension, tarfile.XHDTYPE))
            parts.append(member(name, data))
        return b''.join(parts) + b'\0' * 1024

    def test_observed_seven_local_timestamp_headers_preserve_payloads(self):
        raw = self.tar(self.records)
        self.assertEqual(read_archive(raw), self.files)
        self.assertEqual(read_archive(gzip.compress(raw)), self.files)

    def test_duplicate_malformed_or_incomplete_pax_records_fail(self):
        for payload in (self.records + record('atime', '123'), b'', b'0 atime=1\n',
                        b'999 atime=1\n', b'09 atime=1\n', b'12 atime=1\n',
                        self.records[:-1], self.records + b'x', b'12 atime=\xff\n',
                        record('atime', 'nan'), record('mtime', '1e9')):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                read_archive(self.tar(payload))

    def test_unknown_and_path_link_size_overrides_fail_even_if_benign(self):
        for key, value in (('path', 'model.joblib'), ('linkpath', 'model.joblib'),
                           ('size', '1'), ('SCHILY.mode', '0644'), ('unknown', '1')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                read_archive(self.tar(record(key, value)))

    def test_global_chained_and_orphan_extensions_fail(self):
        pax = member('pax', self.records, tarfile.XHDTYPE)
        for value in (member('global', self.records, tarfile.XGLTYPE) + self.tar(),
                      pax + self.tar(self.records),
                      self.tar()[:-1024] + pax + b'\0' * 1024,
                      member('long', b'model.joblib\0', tarfile.GNUTYPE_LONGNAME) + self.tar()):
            with self.assertRaises(ValueError):
                read_archive(value)

    def test_checksum_padding_truncation_and_terminators_fail(self):
        raw = self.tar(self.records)
        bad_checksum = bytes([raw[0] ^ 1]) + raw[1:]
        pad = 512 + len(self.records)
        bad_padding = raw[:pad] + b'X' + raw[pad + 1:]
        for value in (bad_checksum, bad_padding, raw[:-512], raw[:-1], raw[:1536],
                      raw + b'x' * 512, gzip.compress(raw)[:-1],
                      gzip.compress(raw) + b'garbage', gzip.compress(raw) + gzip.compress(b'')):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                read_archive(value)

    def test_traversal_alias_links_special_members_and_duplicates_fail(self):
        for name, kind, link in (
                ('../model.joblib', tarfile.REGTYPE, ''), ('/model.joblib', tarfile.REGTYPE, ''),
                ('././model.joblib', tarfile.REGTYPE, ''), ('./model.joblib', tarfile.REGTYPE, ''),
                ('model.joblib', tarfile.SYMTYPE, 'elsewhere'),
                ('model.joblib', tarfile.LNKTYPE, 'elsewhere'),
                ('model.joblib', tarfile.FIFOTYPE, ''), ('model.joblib', tarfile.CHRTYPE, ''),
                ('model.joblib', tarfile.BLKTYPE, ''), ('subdir', tarfile.DIRTYPE, '')):
            with self.subTest(name=name, kind=kind), self.assertRaises(ValueError):
                read_archive(member(name, kind=kind, link=link) + self.tar())

    def test_plain_root_prefix_and_limits_remain_strict(self):
        root = member('./', kind=tarfile.DIRTYPE)
        raw = root + b''.join(member('./' + n, b) for n, b in self.files.items()) + b'\0' * 1024
        self.assertEqual(read_archive(raw), self.files)
        for value in (root + raw, member('model.joblib', b'only one') + b'\0' * 1024):
            with self.assertRaises(ValueError):
                read_archive(value)
        for kwargs in ({'max_bytes': 32}, {'max_tar_bytes': 512}):
            with self.assertRaises(ValueError):
                read_archive(gzip.compress(raw), **kwargs)


if __name__ == '__main__':
    unittest.main()
