from hashlib import md5
import base64


def digest(*, username, realm, password, method, uri, nonce, qop: str = None, **kwargs) -> str:
    """
    HTTP 摘要认证(MD5) ，传入变量必须key=value的形式
    :param username: 用户名
    :param realm: 认证域
    :param password: 密码
    :param method: 请求方法（大写） e.g: [GET, OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY]
    :param uri: 请求地址
    :param nonce: 服务端随机数
    :param qop: 质量等级
    :param kwargs : 其他参与计算的参数，包括 [entity_body, nc, cnonce]
    :return: response: md5 最终计算结果
    """

    # calculate  HA1 and HA2
    qop = '' if qop is None else qop.lower()
    HA1 = md5((username + ":" + realm + ":" + password).encode()).hexdigest()

    if 'auth-int' in qop:
        entity_body = kwargs.pop("entity_body")
        HA2 = md5((method + ":" + uri + ":" + md5(entity_body.encode()).hexdigest()))

    elif 'auth' in qop or qop == '':
        HA2 = md5((method + ":" + uri).encode()).hexdigest()
    else:
        raise TypeError('Unsupported auth type: %s' % qop)

    # calculate response
    if 'auth' in qop:
        nc = kwargs.pop('nc')
        cnonce = kwargs.pop('cnonce')
        response = md5((HA1 + ":" + nonce + ':' + nc + ":" + cnonce + ":" + qop + ":" + HA2).encode()).hexdigest()
    else:
        response = md5((HA1 + ":" + nonce + ":" + HA2).encode()).hexdigest()
    return response




# http://lists.mplayerhq.hu/pipermail/mplayer-dev-eng/2008-March/056903.html
def rn5_auth(username, realm, password, nonce, uuid):
    MUNGE_TEMPLATE = '%-.200s%-.200s%-.200sCopyright (C) 1995,1996,1997 RealNetworks, Inc.'
    authstr = "%-.200s:%-.200s:%-.200s" % (username, realm, password)
    first_pass = md5(authstr).hexdigest()

    munged = MUNGE_TEMPLATE % (first_pass, nonce, uuid)
    return md5(munged).hexdigest()


def basic(username, password=''):
    auth_str = '%s:%s' % (username, password)
    auth_str = base64.b64encode(auth_str)
    return auth_str


if __name__ == '__main__':
    result = digest(username='admin', password='tsit2019',
                    realm='IP Camera(D4918)',
                    method="DESCRIBE",
                    uri="rtsp://192.168.201.14:554/h264/ch1/sub/av_stream",
                    nonce='325dbaf043b7cba36b17da397381f421',
                    )

    print(result)
