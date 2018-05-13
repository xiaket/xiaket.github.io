#!/usr/bin/env python
#coding=utf-8
"""
Author:         Xia Kai <xiaket@gmail.com>
Filename:       iTunes.py
Type:           Class definition
Last modified:  2010-05-24 14:02

Description:
Python class for iTunes Media Library file.

Confession: I know nothing of xml, so this is a very bad example for parsing
xml files.
"""
import sys
from datetime import datetime

from urllib import unquote
from xml.dom import minidom


def get_date(timestring):
    """
    This function would return a datestring in iTunes Music Library file into a
    datetime object in python.
    """
    return datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%SZ")


def read_list(main_node):
    item_list = []
    for node in main_node.childNodes:
        if isinstance(node, minidom.Element) and node.hasChildNodes():
            item_list.append(read_key_value(node))
    return item_list


def get_value(type, node):
    """
    This function would get the value coresponding to a key in a dom tree.
    """
    if type == 'integer':
        return int(node.childNodes[0].data)
    elif type == 'string':
        return node.childNodes[0].data
    elif type == 'date':
        return get_date(node.childNodes[0].data)
    elif type == 'dict':
        return read_key_value(node)
    elif type == 'array':
        return read_list(node)
    elif type == 'data':
        return node.childNodes[0].data
    elif type in ['true', 'false']:
        return type == 'true'
    else:
        print type, node
        import sys
        sys.exit()


def read_key_value(main_node):
    """
    Since iTunes Music Library file is arranged in key-value form, it is thus
    reasonable to separate a node into a list of key-value pairs. So here we
    have this function.
    This function would accept a node as parameter, and would return a list of
    key-value pairs.
    """
    pair_dict = {}
    for node in main_node.childNodes:
        if isinstance(node, minidom.Element) and node.hasChildNodes():
            if node.tagName == 'key':
                _key = node.childNodes[0].data
                if isinstance(node.nextSibling, minidom.Element) and not \
                    isinstance(node.nextSibling, minidom.Text):
                    _type = node.nextSibling.tagName
                    _value = get_value(_type, node.nextSibling)
                    pair_dict[_key] = _value
                else:
                    # If nextSibling is a Text instance, we have to jump twice
                    # to get the real node.
                    _type = node.nextSibling.nextSibling.tagName
                    _value = get_value(_type, node.nextSibling.nextSibling)
                    pair_dict[_key] = _value
    return pair_dict


def simplify_directory_name(folder_string):
    """
    In this function we translated possible utf8 encoded file/folder names into
    unicode and return it.
    """
    if folder_string[:17] == u'file://localhost/':
        return unquote(str(folder_string[17:])).decode("UTF-8")
    else:
        return folder_string


class Track(object):
    """
    This class would hold track information.
    """
    def __init__(self, track_dict):
        """
        This function would accept a xml.dom.Node object as parameter.
        keys in the dict:

            Album                   十二楼的莫文蔚
            Kind                    Apple Lossless 音频文件
            Persistent ID           F82E8A083F92D9C6
            Date Modified           2009-11-16 15:22:35
            Name                    两个女孩
            Artist                  莫文蔚
            Sample Rate             44100
            Total Time              239351
            Track Number            7
            Library Folder Count    1
            Date Added              2010-05-08 02:28:50
            Location                file://localhost/D:/%E6%88%91%E7%9A%84%E9%9F%B3%E4%B9%90/%E8%8E%AB%E6%96%87%E8%94%9A/%E5%8D%81%E4%BA%8C%E6%A5%BC%E7%9A%84%E8%8E%AB%E6%96%87%E8%94%9A/07%20%E4%B8%A4%E4%B8%AA%E5%A5%B3%E5%AD%A9.m4a
            Artwork Count           1
            Track Type              File
            Year                    2000
            Track ID                2436
            Bit Rate                1411
            File Folder Count       4
            Size                    21145469

        Properties that interests me:

            Album                   十二楼的莫文蔚
            Kind                    Apple Lossless 音频文件
            Date Modified           2009-11-16 15:22:35
            Name                    两个女孩
            Artist                  莫文蔚
            Total Time              239351
            Track Number            7
            Date Added              2010-05-08 02:28:50
            Location                file://localhost/D:/%E6%88%91%E7%9A%84%E9%9F%B3%E4%B9%90/%E8%8E%AB%E6%96%87%E8%94%9A/%E5%8D%81%E4%BA%8C%E6%A5%BC%E7%9A%84%E8%8E%AB%E6%96%87%E8%94%9A/07%20%E4%B8%A4%E4%B8%AA%E5%A5%B3%E5%AD%A9.m4a
            Year                    2000
            Track ID                2436
            Size                    21145469
        """
        self.id = track_dict['Track ID']
        self.album = track_dict.get('Album', None)
        self.track_number = track_dict.get('Track Number', None)
        self.kind = track_dict['Kind']
        self.name = track_dict['Name']
        self.artist = track_dict.get('Artist', None)
        self.length = track_dict['Total Time']
        self.year = track_dict.get('Year', None)
        self.size = track_dict['Size']
        self.location = simplify_directory_name(track_dict['Location'])
        self.modified = track_dict['Date Modified']
        self.added = track_dict['Date Added']

    def __repr__(self):
        return ("<%s(%s)>" % (self.name, self.artist)).encode("UTF-8")


class Playlist(object):
    """
    This class would hold playlist information.
    """
    def __init__(self, library_kls, playlist_dict):
        """
        This function would accept a xml.dom.Node object as parameter.
        keys in the dict:

            Name                    资料库
            All Items               True
            Playlist Persistent ID  29E1F8DE7095CE21
            Visible                 False
            Master                  True
            Playlist ID             2706
            Playlist                Items

        Properties that interests me:

            Name                    资料库
            Playlist ID             2706
            Playlist Items          list

        """
        self.id = playlist_dict['Playlist ID']
        self.name = playlist_dict['Name']
        if self.name == 'Genius':
            self.list = []
        else:
            self.list = []
            for track_info in playlist_dict['Playlist Items']:
                track_id = track_info['Track ID']
                self.list.append(library_kls.tracks[track_id])

    def __repr__(self):
        return ("<%s (%s)>" % (self.name.encode("UTF-8"), len(self.list)))


class iTunesLibrary(object):
    """
    This class would hold media information in a iTunes Media Library file.
    """
    def __init__(self, file='iTunes Music Library.xml'):
        xmlfile = minidom.parse(file)
        library_meta = xmlfile.getElementsByTagName('plist')[0].childNodes[1]
        kmeta_dict = read_key_value(library_meta)
        self.app_version = meta_dict['Application Version']
        self.folder = simplify_directory_name(meta_dict['Music Folder'])
        self.tracks = {}
        for track_dict in meta_dict['Tracks']:
            track = Track(meta_dict['Tracks'][track_dict])
            self.tracks[track.id] = track
        self.playlists = []
        for playlist in meta_dict['Playlists']:
            self.playlists.append(Playlist(self, playlist))


def main():
    """
    This function would read 'iTunes Music Library.xml' from current directory
    and parse it.
    """
    library = iTunesLibrary()
    for track_id in library.tracks:
        track = library.tracks[track_id]
        print track.name, track.album, track.artist, track.length


if __name__ == "__main__":
    main()
