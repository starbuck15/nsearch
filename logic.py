# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import logging

# third-party
import json
import requests
import urllib
import urllib2
import lxml.html

# sjva 공용
from framework import db, scheduler
from framework.job import Job
from framework.util import Util

# 패키지
import system
from .model import ModelSetting

package_name = __name__.split('.')[0]
logger = logging.getLogger(package_name)
#########################################################


class Logic(object):
    db_default = {'wavve_plugin': 'wavve',
                 'tving_plugin': 'tving',
                 'list_method': 'album'}
    current_keyword = None

    WAVVE_DEFAULT_PARAM = {'apikey': 'E5F3E0D30947AA5440556471321BB6D9',
         'credential': 'none',
         'device': 'pc',
         'partner': 'pooq',
         'pooqzone': 'none',
         'region': 'kor',
         'drm': 'wm',
         'targetage': 'auto'}
    WAVVE_LIMIT = 20

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            Logic.db_init()

            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_setting_value(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    ##################################################################

    @staticmethod
    def wavve_get_search_list(keyword, type='all', page=1):
        try:
            url = 'https://apis.pooq.co.kr/search'
            params = Logic.WAVVE_DEFAULT_PARAM.copy()
            params['type'] = type
            params['keyword'] = keyword
            params['offset'] = (int(page) - 1) * Logic.WAVVE_LIMIT
            params['limit'] = Logic.WAVVE_LIMIT
            params['orderby'] = 'score'
            url = '%s?%s' % (url, urllib.urlencode(params))
            logger.debug('get_search_list:%s', url)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            data = json.load(response, encoding='utf8')
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def wavve_search_keyword(keyword, type='all', page=1):
        try:
            data = Logic.wavve_get_search_list(keyword, type, page)

            if int(data[0]['totalcount']) > 0:
                return {'ret': True,
                        'page': page,
                        'keyword': keyword,
                        'data': data}
            else:
                return {'ret': False,
                        'page': page,
                        'keyword': keyword,
                        'data': data}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_get_search_list(keyword, type='all', page=1):
        try:
            url = 'https://search.tving.com/search/getSearch.jsp?'
            params = {}
            params['kwd'] = keyword
            params['notFoundText'] = keyword
            param = '&siteName=TVING_WEB&category=PROGRAM&pageNum=%s&pageSize=50&indexType=both&methodType=allwordthruindex&payFree=ALL&runTime=ALL&grade=ALL&genre=ALL&screen=CSSD0100&os=CSOD0900&network=CSND0900&sort1=ins_dt&sort2=frequency&sort3=NO&type1=desc&type2=desc&type3=desc&fixedType=Y&spcMethod=someword&spcSize=0&adult_yn=&reKwd=&xwd=' % page
            url = '%s%s%s' % (url, urllib.urlencode(params), param)
            logger.debug('get_program_list:%s', url)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            data = json.load(response, encoding='utf8')
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_search_keyword(keyword, type='all', page=1):
        try:
            data = Logic.tving_get_search_list(keyword, type, page)

            if int(data['programRsb']['count']) > 0:
                return {'ret': True,
                        'page': page,
                        'keyword': keyword,
                        'data': data['programRsb']['dataList']}
            else:
                return {'ret': False,
                        'page': page,
                        'keyword': keyword,
                        'data': data}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_get_SMTV_PROG_4K_list(type='program'):
        try:
            url = 'http://api.tving.com/v2/operator/highlights?'
            params = {}
            if type == 'program':
                param = 'positionKey=SMTV_PROG_4K&screenCode=CSSD1200&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=aeef9047f92b9dc4ebabc71fe4b124bf&pocType=APP_Z_TVING_1.0&callback=__jp12'
            elif type == 'movie':
                param = 'positionKey=SMTV_MV_4K&screenCode=CSSD1200&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=aeef9047f92b9dc4ebabc71fe4b124bf&pocType=APP_Z_TVING_1.0&callback=__jp10'
            param = param.split('&callback=')[0]
            url = '%s%s%s' % (url, urllib.urlencode(params), param)
            logger.debug('get_4k_list:%s', url)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            data = json.load(response, encoding='utf8')

            if len(data['body']['result']) > 0:
                return {'ret': True,
                        'type': type,
                        'data': data}
            else:
                return {'ret': False,
                        'type': type,
                        'data': data}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def daum_get_ratings(keyword):
        try:
            # drama_keywords = {'월화드라마', '수목드라마', '금요/주말드라마', '일일/아침드라마'}
            # ent_keywords = {'월요일예능', '화요일예능', '수요일예능', '목요일예능', '금요일예능', '토요일예능', '일요일예능'}

            logger.debug('get_daum_ratings %s', keyword)
            url = 'https://search.daum.net/search?w=tot&q=%s' % urllib.quote(keyword.encode('utf8'))

            request = urllib2.Request(url)
            request.add_header('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36')
            response = urllib2.urlopen(request)
            html = response.read()
            root = lxml.html.fromstring(html)
            list_program = root.xpath('//ol[@class="list_program item_cont"]/li')

            data = []
            for item in list_program:
                data_item = {}
                data_item['title'] = item.xpath('./div/strong/a/text()')[0]
                data_item['air_time'] = item.xpath('./div/span[1]/text()')[0]
                data_item['provider'] = item.xpath('./div/span[@class="txt_subinfo"][2]/text()')[0]
                data_item['image'] = item.xpath('./a/img/@src')
                data_item['scheduled'] = item.xpath('./div/span[@class="txt_subinfo"]/span[@class="txt_subinfo"]/text()')
                data_item['ratings'] = item.xpath('./div/span[@class="txt_subinfo"][2]/span[@class="f_red"]/text()')

                if len(data_item['image']):
                    data_item['image'] = data_item['image'][0]
                else:
                    data_item['image'] = 'http://www.okbible.com/data/skin/okbible_1/images/common/noimage.gif'
                    # data_item['image'] = 'https://search1.daumcdn.net/search/statics/common/pi/thumb/noimage_151203.png'
                if len(data_item['scheduled']):
                    data_item['scheduled'] = data_item['scheduled'][0]
                if len(data_item['ratings']):
                    data_item['ratings'] = data_item['ratings'][0]

                data.append(data_item)

            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())