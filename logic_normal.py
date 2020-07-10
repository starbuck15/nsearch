# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
import urllib
from datetime import datetime

# third-party
import json
import requests
import urllib
import lxml.html

# sjva 공용
from framework import app, db, scheduler, path_app_root, celery
from framework.job import Job
from framework.util import Util

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting

#########################################################

class LogicNormal(object):
    wavve_config = {
        'base_url': 'https://apis.pooq.co.kr',
        'base_parameter': {
            'apikey': 'E5F3E0D30947AA5440556471321BB6D9',
            'credential': 'none',
            'device': 'pc',
            'partner': 'pooq',
            'pooqzone': 'none',
            'region': 'kor',
            'drm': 'wm',
            'targetage': 'auto'
        }
    }
    tving_config = {
        'base_url': 'https://api.tving.com',
        'search_url': 'https://search.tving.com',
    }

    @staticmethod
    def scheduler_function():
        try:
            logger.debug('nsearch scheduler_function start..')
            
            auto_wavve_whitelist_active = ModelSetting.get_bool('auto_wavve_whitelist_active')
            auto_wavve_whitelist_limit = ModelSetting.get_int('auto_wavve_whitelist_limit')
            auto_tving_whitelist_active = ModelSetting.get_bool('auto_tving_whitelist_active')
            auto_tving_whitelist_limit = ModelSetting.get_int('auto_tving_whitelist_limit')
            
            if auto_wavve_whitelist_active:
                ret = LogicNormal.wavve_get_cfpopular_list()
                if ret['ret']:
                    auto_wavve_whitelist = [x['title_list'][0]['text'].strip() for x in ret['data']['cell_toplist']['celllist']]
                    auto_wavve_whitelist = auto_wavve_whitelist[:auto_wavve_whitelist_limit]
                    auto_wavve_whitelist = Util.get_list_except_empty(auto_wavve_whitelist)

                    from wavve.model import ModelSetting as ModelWavveSetting
                    whitelist_program = ModelWavveSetting.get('whitelist_program')
                    whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
                    whitelist_programs = Util.get_list_except_empty(whitelist_programs)

                    new_whitelist_programs = whitelist_programs + auto_wavve_whitelist
                    new_whitelist_programs = list(set(new_whitelist_programs))
                    new_whitelist_program = ', '.join(new_whitelist_programs)
                    
                    added_whitelist_programs = list(set(new_whitelist_programs) - set(whitelist_programs))
                    added_whitelist_program = ', '.join(added_whitelist_programs)
                    logger.info('added_wavve_programs:%s', added_whitelist_program)
                    
                    whitelist_program = ModelWavveSetting.set('whitelist_program',new_whitelist_program)

            if auto_tving_whitelist_active:
                ret = LogicNormal.tving_get_popular_list()
                if ret['ret']:
                    auto_tving_whitelist = [x['program']['name']['ko'].strip() for x in ret['data']['body']['result']]
                    auto_tving_whitelist = auto_tving_whitelist[:auto_tving_whitelist_limit]
                    auto_tving_whitelist = Util.get_list_except_empty(auto_tving_whitelist)

                    from tving.model import ModelSetting as ModelTvingSetting
                    whitelist_program = ModelTvingSetting.get('whitelist_program')
                    whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
                    whitelist_programs = Util.get_list_except_empty(whitelist_programs)

                    new_whitelist_programs = whitelist_programs + auto_tving_whitelist
                    new_whitelist_programs = list(set(new_whitelist_programs))
                    new_whitelist_program = ', '.join(new_whitelist_programs)
                    
                    added_whitelist_programs = list(set(new_whitelist_programs) - set(whitelist_programs))
                    added_whitelist_program = ', '.join(added_whitelist_programs)
                    logger.info('added_tving_programs:%s', added_whitelist_program)
                    
                    whitelist_program = ModelTvingSetting.set('whitelist_program',new_whitelist_program)

            logger.debug('=======================================')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def wavve_get_search_list(keyword, type='all', page=1):
        try:
            param = LogicNormal.wavve_config['base_parameter'].copy()
            param['type'] = type
            param['keyword'] = keyword
            param['offset'] = (int(page) - 1) * 20
            param['limit'] = 20
            param['orderby'] = 'score'
            url = '%s/search?%s' % (LogicNormal.wavve_config['base_url'], urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def wavve_search_keyword(keyword, type='all', page=1):
        try:
            data = LogicNormal.wavve_get_search_list(keyword, type, page)

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
            param = {}
            param['kwd'] = keyword
            param['notFoundText'] = keyword
            default_param = 'siteName=TVING_WEB&category=PROGRAM&pageNum=%s&pageSize=50&indexType=both&methodType=allwordthruindex&payFree=ALL&runTime=ALL&grade=ALL&genre=ALL&screen=CSSD0100&os=CSOD0900&network=CSND0900&sort1=ins_dt&sort2=frequency&sort3=NO&type1=desc&type2=desc&type3=desc&fixedType=Y&spcMethod=someword&spcSize=0&adult_yn=&reKwd=&xwd=' % page
            url = '%s/search/getSearch.jsp?%s&%s' % (LogicNormal.tving_config['search_url'], default_param, urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_search_keyword(keyword, type='all', page=1):
        try:
            data = LogicNormal.tving_get_search_list(keyword, type, page)

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
    def wavve_get_popular_list(type='all'):
        try:
            param = LogicNormal.wavve_config['base_parameter'].copy()
            if type == 'dra':
                param['genre'] = '01'
            elif type == 'ent':
                param['genre'] = '02'
            elif type == 'doc':
                param['genre'] = '03'
            else:
                param['genre'] = 'all' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
            param['subgenre'] = 'all'
            param['channel'] = 'all'
            param['type'] = 'all' # general, onair, all
            param['offset'] = '0'
            param['limit'] = '30'
            # params['onair'] = 'y' # all 전체, y 방영중, n 종영 ## valid in popularprograms
            # url = '%s/vod/popularprograms?%s' % (LogicNormal.wavve_config['base_url'], urllib.urlencode(param))
            url = '%s/vod/popularcontents?%s' % (LogicNormal.wavve_config['base_url'], urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            
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
    def wavve_get_cfpopular_list(type='all'):
        try:
            param = LogicNormal.wavve_config['base_parameter'].copy()
            if type == 'dra':
                param['genre'] = '01'
                param['broadcastid'] = 'FN0_VN327_pc'
            elif type == 'ent':
                param['genre'] = '02'
                param['broadcastid'] = 'FN0_VN326_pc'
            elif type == 'doc':
                param['genre'] = '03'
                param['broadcastid'] = 'FN0_VN328_pc'
            else:
                param['genre'] = 'all' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
                param['broadcastid'] = 'FN0_VN327_pc' # unknown
            param['WeekDay'] = 'all'
            param['came'] = 'broadcast'
            param['subgenre'] = 'all'
            param['channel'] = 'all'
            param['contenttype'] = 'vod'
            param['offset'] = '0'
            param['limit'] = '30'
            param['orderby'] = 'viewtime'
            url = '%s/cf/vod/popularcontents?%s' % (LogicNormal.wavve_config['base_url'], urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            
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
    def tving_get_popular_list(type='all'):
        try:
            param = {}
            if type == 'dra':
                param['multiCategoryCode'] = 'PCA'
            elif type == 'ent':
                param['multiCategoryCode'] = 'PCD'
            elif type == 'doc':
                param['multiCategoryCode'] = 'PCK'
            else:
                param['multiCategoryCode'] = ''
            default_param = 'pageNo=1&pageSize=30&order=viewDay&adult=all&free=all&guest=all&scope=all&lastFrequency=y&personal=N&screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610'
            # order : viewDay, viewWeek
            url = '%s/v2/media/episodes?%s&%s' % (LogicNormal.tving_config['base_url'], default_param, urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()

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
            param = {}
            if type == 'program':
                param['positionKey'] = 'SMTV_PROG_4K'
            elif type == 'movie':
                param['positionKey'] = 'SMTV_MV_4K'
            default_param = 'screenCode=CSSD1200&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=aeef9047f92b9dc4ebabc71fe4b124bf&pocType=APP_Z_TVING_1.0'
            url = '%s/v2/operator/highlights?%s&%s' % (LogicNormal.tving_config['base_url'], default_param, urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()

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
    def daum_get_ratings_list(keyword):
        try:
            # drama_keywords = {'월화드라마', '수목드라마', '금요/주말드라마', '일일/아침드라마'}
            # ent_keywords = {'월요일예능', '화요일예능', '수요일예능', '목요일예능', '금요일예능', '토요일예능', '일요일예능'}
            from framework.common.daum import headers, session
            from system.logic_site import SystemLogicSite
            url = 'https://search.daum.net/search?w=tot&q=%s' % urllib.quote(keyword.encode('utf8'))
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
    