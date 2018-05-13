#!/usr/bin/env python
#coding=utf-8
"""
Author:         Xia Kai <xiaket@corp.netease.com/xiaket@gmail.com>
Filename:       itunes-playing.py
Type:           Utility
Last modified:  2011-09-26 13:09

Description:
这个脚本将能够从iTunes中拿到正在播放的音乐信息, 并格式化后发一条新浪微博.
"""
import hmac
import httplib
import json
import os
import time

from binascii import b2a_base64
from hashlib import sha1
from random import randint
from urllib import urlencode, quote
from urlparse import parse_qsl


APPKEY = "3601110248"
APPSEC = "3c9c0a86f786ae7297c61b85efbabfa6"
ACCKEY = ""
ACCSEC = ""
HOST = 'api.t.sina.com.cn'
URL = 'http://api.t.sina.com.cn%s'
HTTP_METHOD = "GET"

USE_PIC = True   # 如果不发专辑图片, 将此设为False.
POST_FORMAT = u"#我正在听# #Now Playing# %(name)s - %(artist)s, 专辑<%(album)s>, 播放列表'%(playlist)s', 已播放%(playedcount)s次"


class OAuthToken(object):
    """一个放Token的数据结构."""
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthHandler(object):
    def __init__(self):
        self.request_token = None
        self.verifier = None
        self.access_token = None
        if ACCKEY and ACCSEC:
            self.access_token = OAuthToken(ACCKEY, ACCSEC)
        else:
            authorization_url = self.get_authorization_url()
            import webbrowser
            if not webbrowser.open(authorization_url):
                print 'Please authorize: %s' %  authorization_url
            self.verifier = raw_input(u'请输入授权码: '.encode("GB2312")).strip()
            self.access_token = self.get_access_token()
            self.write_self()
            self.verifier = None

    def http_request(self, method, path, parameters, headers):
        """包装了httplib的连接请求."""
        conn = httplib.HTTPConnection(HOST)
        if 'post_data' in parameters:
            # This is a hack for posting pictures to the server.
            post_data = parameters['post_data']
            del parameters['post_data']
        else:
            post_data = urlencode(parameters)
        parameters.update({
            'oauth_consumer_key': APPKEY,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': ''.join([str(randint(0, 9)) for i in range(8)]),
            'oauth_version': '1.0',
            'oauth_signature_method': 'HMAC-SHA1',
        })
        if self.access_token:
            parameters['oauth_token'] = self.access_token.key
        if self.verifier:
            parameters['oauth_verifier'] = self.verifier
            parameters['oauth_token'] = self.request_token.key
            parameters['oauth_signature'] = encrypt_with_hmac(method, path, parameters, self.request_token)
        else:
            parameters['oauth_signature'] = encrypt_with_hmac(method, path, parameters, self.access_token)

        auth_header = 'OAuth realm=""'
        for key, value in parameters.iteritems():
            if key[:6] == 'oauth_':
                auth_header += ', %s="%s"' % (key, escape(str(value)))
        headers.update({'Authorization': auth_header})

        try:
            conn.request(method, path, headers=headers, body=post_data)
            resp = conn.getresponse()
        except httplib.HTTPException:
            raise RuntimeError('Failed to send request')

        response = resp.read()
        conn.close()
        if resp.status != 200:
            json_dict = json.loads(response)
            error_msg = 'error_code: %(error_code)s, %(error)s' % json_dict
            raise RuntimeError(error_msg)

        return response

    def get_authorization_url(self):
        """Get the authorization URL to redirect the user"""
        response_str = self.http_request('GET', '/oauth/request_token', {}, {})
        response_dict = dict(parse_qsl(response_str))
        self.request_token = OAuthToken(
            response_dict['oauth_token'], response_dict['oauth_token_secret'],
        )
        return URL % "/oauth/authorize?oauth_token=%s" % self.request_token.key

    def get_access_token(self):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        response_str = self.http_request('GET', '/oauth/access_token', {}, {})
        _dict = dict(parse_qsl(response_str))
        return OAuthToken(_dict['oauth_token'], _dict['oauth_token_secret'])

    def write_self(self):
        """这个函数会将access_token中的值写到当前文件中去."""
        import sys
        fullpath = sys.path[0]
        filename = os.path.split(sys.argv[0])[-1]
        filepath = os.path.join(fullpath, filename)
        tmpfile = filepath + ".tmp"
        orig_file = open(filepath)
        temp_file = open(tmpfile, 'w')
        for line in orig_file:
            if line.strip() == 'ACCKEY = ""':
                temp_file.write('ACCKEY = "%s"\n' % self.access_token.key)
                continue
            elif line.strip() == 'ACCSEC = ""':
                temp_file.write('ACCSEC = "%s"\n' % self.access_token.secret)
                continue
            temp_file.write(line)
        temp_file.close()
        orig_file.close()
        os.remove(filepath)
        os.rename(tmpfile, filepath)

    def api_request(self, path, parameters={}, headers={}):
        """调用http_request来进行API请求."""
        headers.setdefault("Host", HOST)
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        self.http_request('POST', path, parameters, headers)


def escape(s):
    """Escape a URL including any /."""
    return quote(s, safe='~')

def normalize(parameters):
    """Return a string that contains the parameters that must be signed."""
    params = parameters
    try:
        # Exclude the signature if it exists.
        del params['oauth_signature']
    except:
        pass
    # Escape key values before sorting.
    key_values = [(escape(k), escape(v)) for k, v in params.items()]
    # Sort lexicographically, first after key, then after value.
    key_values.sort()
    return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

def encrypt_with_hmac(method, path, parameters, token=None):
    url = URL % path
    normalized_parameters = normalize(parameters)
    sig = (escape(method), escape(url), escape(normalized_parameters))
    key = '%s&' % escape(APPSEC)
    if token:
        key += escape(token.secret)
    raw = '&'.join(sig)
    hashed = hmac.new(key, raw, sha1)
    return b2a_base64(hashed.digest())[:-1]

def get_pic_body(status, filename):
    """编一个formdata出来, 返回含有post_data的字典和header."""
    try:
        if os.path.getsize(filename) > (5 * 1024 * 1024):
            raise RuntimeError('File too big')
    except os.error:
        raise RuntimeError('Unable to access file')

    fobj = open(filename, 'rb')
    boundary = "-"*20 + str(randint(1000000000, 99999999999))
    body = []
    body.append('--' + boundary)
    body.append('Content-Disposition: form-data; name="status"')
    body.append('')
    body.append(status)
    body.append('--' + boundary)
    body.append('Content-Disposition: form-data; name="pic"; filename="%s"' % filename)
    body.append('Content-Type: image/%s' % filename.split(".")[-1])
    body.append('Content-Transfer-Encoding: binary')
    body.append('')
    body.append(fobj.read())
    fobj.close()
    body.append('--' + boundary + '--\r\n')
    body = '\r\n'.join(body)
    headers = {
        'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
        'Content-Length': len(body),
    }
    return {'post_data': body}, headers

def get_content_dict():
    """
    如果不需要发图或者发不了, 返回一个字典, 作为parameters参数供API使用.
    如果需要发图, 返回两个字典, 分别是parameters和header.
    """
    try:
        from win32com.client import Dispatch
    except ImportError:
        status = "测试%s" % randint(1024, 65535)
        pic_name = '/home/xiaket/kde.png'
        if not USE_PIC:
            return {'status': status}
        else:
            return get_pic_body(status, pic_name)

    itunes = Dispatch("iTunes.Application")
    track = itunes.CurrentTrack
    track_info = {
        'name': track.Name,
        'artist': track.Artist,
        'playlist': track.Playlist.Name,
        'album': track.Album,
        'dateadded': track.DateAdded.Format(),
        'duration': track.Duration,
        'genere': track.Genre,
        'playedcount': track.PlayedCount,
        'rating': track.Rating,
        'size': "%.1fM" % (track.Size / 1024. /1024),
        'year': track.Year,
        'time': track.Time,
    }
    status = (POST_FORMAT % track_info).encode("UTF8")
    if USE_PIC:
        artwork = track.Artwork
        if artwork.Count > 0:
            format_dict = {
                0: 'Unknown',
                1: 'jepg',
                2: 'png',
                3: 'bmp',
            }
            picobj = artwork.Item(1)
            pic_format = picobj.Format
            if pic_format in [0, 3]:
                # 这两个格式不被新浪微博支持.
                return {'status': status}
            else:
                temp_dir = os.environ['TEMP']
                pic_name = '%s\\artwork.%s' % (temp_dir, format_dict[pic_format])
                picobj.SaveArtworkToFile(pic_name)
                return get_pic_body(status, pic_name)
        else:
            return {'status': status}

def main():
    oauth_handler = OAuthHandler()
    path = '/statuses/upload.json' if USE_PIC else 'statuses/update.json'
    oauth_handler.api_request(path, *get_content_dict())


if __name__ == "__main__":
    main()
