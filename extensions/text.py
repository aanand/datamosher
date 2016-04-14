# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random
import os
import re


def random_code(min_length, max_length):
    filenames = get_all_files('extensions') + ['bot.py']

    code = read_random_file(filenames)
    code = re.sub(r'\s+', ' ', code)

    text = random_excerpt(code, min_length, max_length)
    text = to_fullwidth(text)
    text = damage(text)

    return text


def get_all_files(top):
    return [
        os.path.join(dirpath, name)
        for (dirpath, dirnames, filenames) in os.walk(top)
        for name in filenames
    ]


def read_random_file(filenames):
    while True:
        filename = random.choice(filenames)
        try:
            with open(filename) as f:
                contents = f.read().decode('utf-8')
                if contents:
                    return contents
        except UnicodeDecodeError:
            pass


def random_excerpt(text, min_length, max_length):
    min_length = min(len(text), min_length)
    max_length = min(len(text), max_length)
    length = random.randint(min_length, max_length)
    pos = random.randint(0, len(text)-length)
    return text[pos:pos+length]


# http://stackoverflow.com/a/8327034
def to_fullwidth(text):
    normal = ' 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    wide = '　０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！゛＃＄％＆（）＊＋、ー。／：；〈＝〉？＠［\\］＾＿‘｛｜｝～'
    widemap = dict((ord(x[0]), x[1]) for x in zip(normal, wide))
    return text.translate(widemap)


def damage(text):
    """
    Replace characters in text with random block characters.
    The probability of replacing a character quadratically approaches 1 as you
    approach the end of the text.
    """
    chars = [c for c in text]

    for idx in range(len(chars)):
        probability = (float(idx) / len(chars)) ** 2
        if random.random() < probability:
            chars[idx] = unichr(random.randint(0x2580, 0x259F))

    return ''.join(chars)


if __name__ == '__main__':
    text = random_code(25, 50)
    print(text)
