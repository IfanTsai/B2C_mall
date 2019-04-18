from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings

class FdfsStroage(Storage):
    """
    FastDFS文件存储类
    """
    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        """
        保存文件
        :param name: 上传文件的文件名
        :param content: 包含上传文件内容的File对象
        :return:
        """
        # 创建FastDFS客户端实例
        client = Fdfs_client(settings.FDFS_CLIENT_CONFIG)
        # 上传文件
        res = client.upload_by_buffer(content.read())

        # 异常处理
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FastDFS失败')

        # 返回文件id
        return  res.get('Remote file_id')

    def exists(self, name):
        """
        Django判断文件名是否可用
        :param name:
        :return:
        """
        # 文件内容保存在FastDFS上，而不是Django，所以直接返回False
        return False

    def url(self, name):
        """
        返回访问文件的url路径
        :param name:
        :return:
        """
        return settings.NGINX_IP_PORT + name
