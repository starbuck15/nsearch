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
            # logger.debug('get_search_list:%s', url)
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
            # logger.debug('get_program_list:%s', url)
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
    def wavve_get_popular(type='all'):
        try:
            url = 'https://apis.pooq.co.kr/vod/popularcontents'
            # url = 'https://apis.pooq.co.kr/vod/popularprograms'
            params = Logic.WAVVE_DEFAULT_PARAM.copy()
            # params['onair'] = 'y' # all 전체, y 방영중, n 종영
            params['genre'] = '01' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
            if type == 'dra':
                params['genre'] = '01'
            elif type == 'ent':
                params['genre'] = '02'
            elif type == 'doc':
                params['genre'] = '03'
            else:
                params['genre'] = 'all' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
            params['subgenre'] = 'all'
            params['channel'] = 'all'
            params['type'] = 'all' # general, onair, all
            params['offset'] = '0'
            params['limit'] = '30'
            url = '%s?%s' % (url, urllib.urlencode(params))
            # logger.debug('get_search_list:%s', url)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            data = json.load(response, encoding='utf8')
            
            if len(data['list']) > 0:
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
    def wavve_get_popular_cf(type='all'):
        try:
            # url = 'https://apis.wavve.com/cf/supermultisections/GN2'
            # params = Logic.WAVVE_DEFAULT_PARAM.copy()
            # url = '%s?%s' % (url, urllib.urlencode(params))
            # request = urllib2.Request(url)
            # response = urllib2.urlopen(request)
            # data = json.load(response, encoding='utf8')
            
            url = 'https://apis.pooq.co.kr/cf/vod/popularcontents'
            params = Logic.WAVVE_DEFAULT_PARAM.copy()
            params['genre'] = '01' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
            if type == 'dra':
                params['genre'] = '01'
                params['broadcastid'] = 'FN0_VN327_pc'
            elif type == 'ent':
                params['genre'] = '02'
                params['broadcastid'] = 'FN0_VN326_pc'
            elif type == 'doc':
                params['genre'] = '03'
                params['broadcastid'] = 'FN0_VN328_pc'
            else:
                params['genre'] = 'all' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
                params['broadcastid'] = 'FN0_VN327_pc' # unknown
            params['WeekDay'] = 'all'
            params['came'] = 'broadcast'
            params['subgenre'] = 'all'
            params['channel'] = 'all'
            params['contenttype'] = 'vod'
            params['offset'] = '0'
            params['limit'] = '30'
            params['orderby'] = 'viewtime'
            url = '%s?%s' % (url, urllib.urlencode(params))
            # logger.debug('get_search_list:%s', url)
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            data = json.load(response, encoding='utf8')
            
            if len(data['cell_toplist']['celllist']) > 0:
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
    def tving_get_popular(type='all'):
        try:
            url = 'https://api.tving.com/v2/media/episodes?'
            url += 'pageNo=1&pageSize=30&order=viewDay&adult=all&free=all&guest=all&scope=all&lastFrequency=y&personal=N&screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610'
            # url += 'pageNo=1&pageSize=30&order=viewWeek&adult=all&free=all&guest=all&scope=all&lastFrequency=y&personal=N&screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610'
            params = {}
            if type == 'dra':
                param = '&multiCategoryCode=PCA'
            elif type == 'ent':
                param = '&multiCategoryCode=PCD'
            elif type == 'doc':
                param = '&multiCategoryCode=PCK'
            else:
                param = ''
            url = '%s%s%s' % (url, urllib.urlencode(params), param)
            # logger.debug('get_4k_list:%s', url)
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
            # logger.debug('get_4k_list:%s', url)
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

            from framework.common.daum import headers, session
            from system.logic_site import SystemLogicSite
            res = session.get(url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
            html = res.content
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
            
    @staticmethod
    def wavve_programs():
        try:
            import datetime
            from wavve.model import ModelSetting as ModelWavveSetting
            from wavve.model import ModelWavveEpisode as ModelWavveEpisode
            whitelist_program = ModelWavveSetting.get('whitelist_program')
            whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
            whitelist_programs = Util.get_list_except_empty(whitelist_programs)
            month_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            # query = ModelWavveEpisode.query.filter((ModelWavveEpisode.call == 'auto') & (ModelWavveEpisode.releasedate > month_ago))
            query = db.session.query(ModelWavveEpisode.programtitle, ModelWavveEpisode.channelname)
            query = query.filter((ModelWavveEpisode.call == 'auto') & (ModelWavveEpisode.releasedate > month_ago))
            query = query.group_by(ModelWavveEpisode.programtitle)
            tmp = query.all()
            
            data = []
            count = 0
            for item in tmp:
                data_item = {}
                data_item['channel_name'] = item.channelname
                data_item['program_name'] = item.programtitle.strip()
                data_item['display'] = '[' + data_item['channel_name'] + '] ' + data_item['program_name']
                if data_item['program_name'] in whitelist_programs:
                    data_item['whitelist'] = '1'
                    count = count + 1
                    whitelist_programs.remove(data_item['program_name'])
                else:
                    data_item['whitelist'] = '0'
                data.append(data_item)
            
            for item in list(set(whitelist_programs)):
                data_item = {}
                data_item['channel_name'] = ''
                data_item['program_name'] = item.strip()
                data_item['display'] = data_item['program_name']
                data_item['whitelist'] = '1'
                count = count + 1
                data.append(data_item)
            
            data.sort(key=lambda elem: elem['display'])
            return {'data': data, 
                    'count': count,
                    'total': len(data)}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def tving_programs():
        try:
            import datetime
            from tving.model import ModelSetting as ModelTvingSetting
            from tving.model import Episode as ModelTvingEpisode
            whitelist_program = ModelTvingSetting.get('whitelist_program')
            whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
            whitelist_programs = Util.get_list_except_empty(whitelist_programs)
            month_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%y%m%d')
            # query = ModelTvingEpisode.query.filter((ModelTvingEpisode.call == 'auto') & (ModelTvingEpisode.broadcast_date > month_ago))
            query = db.session.query(ModelTvingEpisode.program_name, ModelTvingEpisode.channel_name)
            query = query.filter((ModelTvingEpisode.call == 'auto') & (ModelTvingEpisode.broadcast_date > month_ago))
            query = query.group_by(ModelTvingEpisode.program_name)
            tmp = query.all()
            
            data = []
            count = 0
            for item in tmp:
                data_item = {}
                data_item['channel_name'] = item.channel_name
                data_item['program_name'] = item.program_name.strip()
                data_item['display'] = '[' + data_item['channel_name'] + '] ' + data_item['program_name']
                if data_item['program_name'] in whitelist_programs:
                    data_item['whitelist'] = '1'
                    count = count + 1
                    whitelist_programs.remove(data_item['program_name'])
                else:
                    data_item['whitelist'] = '0'
                data.append(data_item)
            
            for item in list(set(whitelist_programs)):
                data_item = {}
                data_item['channel_name'] = ''
                data_item['program_name'] = item.strip()
                data_item['display'] = data_item['program_name']
                data_item['whitelist'] = '1'
                count = count + 1
                data.append(data_item)
            
            data.sort(key=lambda elem: elem['display'])
            return {'data': data, 
                    'count': count,
                    'total': len(data)}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def wavve_whitelist_save(req):
        try:
            from wavve.model import ModelSetting as ModelWavveSetting
            whitelist_programs = req.form.getlist('wavve_whitelist[]')
            whitelist_program = ', '.join(whitelist_programs)
            logger.debug(whitelist_program)
            whitelist_program = ModelWavveSetting.set('whitelist_program',whitelist_program)
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def tving_whitelist_save(req):
        try:
            from tving.model import ModelSetting as ModelTvingSetting
            whitelist_programs = req.form.getlist('tving_whitelist[]')
            whitelist_program = ', '.join(whitelist_programs)
            logger.debug(whitelist_program)
            whitelist_program = ModelTvingSetting.set('whitelist_program',whitelist_program)
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False