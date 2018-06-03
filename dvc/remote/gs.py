import posixpath
from google.cloud import storage

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from dvc.remote.base import Remote


class RemoteGS(Remote):
    PARAM_ETAG = 'etag'

    def __init__(self, project, config):
        #FIXME
        from dvc.config import Config

        self.project = project
        self.url = config.get[Config.SECTION_REMOTE_URL]
        self.projectname = config.get(Config.SECTION_GCP_PROJECTNAME, None)

    @property
    def bucket(self):
        return urlparse(self.url).netloc

    @property
    def prefix(self):
        return urlparse(self.url).path.lstrip('/')

    @property
    def gs(self):
        return storage.Client()

    def get_etag(self, bucket, key):
        blob = self.gs.bucket(bucket).get_blob(key)
        if not blob:
            return None

        return blob.etag

    def save_info(self, path_info):
        if path_info['scheme'] != 'gs':
            raise NotImplementedError

        return {self.PARAM_ETAG: self.get_etag(path_info['bucket'], path_info['key'])}

    def save(self, path_info):
        if path_info['scheme'] != 'gs':
            raise NotImplementedError

        etag = self.get_etag(path_info['bucket'], path_info['key'])
        dest_key = posixpath.join(self.prefix, etag[0:2], etag[2:])

        blob = self.gs.bucket(path_info['bucket']).get_blob(path_info['key'])
        if not blob:
            raise DvcException('{} doesn\'t exist in the cloud'.format(path_info['key']))

        self.gs.bucket(self.bucket).copy_blob(blob, self.bucket, name=dest_key)

        return {PARAM_ETAG: etag}

    def checkout(self, path_info, checksum_info):
        if path_info['scheme'] != 'gs':
            raise NotImplementedError

        etag = checksum_info.get(PARAM_ETAG, None)
        if not etag:
            return

        key = posixpath.join(self.prefix, etag[0:2], etag[2:])
        blob = self.gs.bucket(self.bucket).get_blob(key)
        if not blob:
            raise DvcException('{} doesn\'t exist in the cloud'.format(key))

        self.gs.bucket(path_info['bucket']).copy_blob(blob, path_info['bucket'], name=path_info['key'])
