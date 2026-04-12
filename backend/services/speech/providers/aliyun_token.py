#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import time
import os
import uuid
import httpx
from urllib import parse
from utils.logger import get_logger

logger = get_logger("AliyunToken")

class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    @staticmethod
    async def create_token(access_key_id, access_key_secret):
        parameters = {'AccessKeyId': access_key_id,
                      'Action': 'CreateToken',
                      'Format': 'JSON',
                      'RegionId': 'cn-shanghai',
                      'SignatureMethod': 'HMAC-SHA1',
                      'SignatureNonce': str(uuid.uuid1()),
                      'SignatureVersion': '1.0',
                      'Timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      'Version': '2019-02-28'}
        # 构造规范化的请求字符串
        query_string = AccessToken._encode_dict(parameters)
        # 构造待签名字符串
        string_to_sign = 'GET' + '&' + AccessToken._encode_text('/') + '&' + AccessToken._encode_text(query_string)
        # 计算签名
        secreted_string = hmac.new(bytes(access_key_secret + '&', encoding='utf-8'),
                                   bytes(string_to_sign, encoding='utf-8'),
                                   hashlib.sha1).digest()
        signature = base64.b64encode(secreted_string)
        # 进行URL编码
        signature = AccessToken._encode_text(signature)
        # 调用服务
        full_url = 'http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s' % (signature, query_string)
        # 提交HTTP GET请求 (async with httpx.AsyncClient())
        async with httpx.AsyncClient() as client:
            response = await client.get(full_url)
            if response.is_success:
                root_obj = response.json()
                key = 'Token'
                if key in root_obj:
                    token = root_obj[key]['Id']
                    expire_time = root_obj[key]['ExpireTime']
                    return token, expire_time
        return None, None

async def getAliToken():
    app_key = os.getenv('ALIYUN_VOICE_APP_KEY')
    access_key_id = os.getenv('ALIYUN_VOICE_AK_ID')
    access_key_secret = os.getenv('ALIYUN_VOICE_AK_SECRET')
    token, expire_time = await AccessToken.create_token(access_key_id, access_key_secret)
    tokenBeijingTime = (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_time))) if expire_time else None
    # logger.info(f'app_key: {app_key}, token: {token}')
    if expire_time:
        logger.info(f'aliyun token expire time: {tokenBeijingTime}')
    return app_key, token