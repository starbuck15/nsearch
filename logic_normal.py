# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
from datetime import datetime
import threading
import time

# third-party
import json
import requests
import lxml.html

# sjva 공용
from framework import app, db, scheduler, path_app_root, celery, socketio
from framework.job import Job
from framework.util import Util
from framework import py_urllib

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelAutoHistory

#########################################################

class LogicNormal(object):
    wavve_config = {
        'base_url': 'https://apis.wavve.com',
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
            auto_tving_order = ModelSetting.get('auto_tving_order')
            auto_priority = ModelSetting.get_int('auto_priority')
            auto_delete = ModelSetting.get_bool('auto_delete')
            
            if auto_wavve_whitelist_active and auto_tving_whitelist_active:
                auto_wavve_whitelist, auto_wavve_total = LogicNormal.wavve_get_cfpopular_list(auto_wavve_whitelist_limit)
                auto_tving_whitelist, auto_tving_total = LogicNormal.tving_get_popular_list(auto_tving_whitelist_limit)
                if auto_priority == 0: # wavve + tving
                    pass
                elif auto_priority == 1: # wavve > tving
                    auto_tving_whitelist = list(set(auto_tving_whitelist) - set(auto_wavve_whitelist))
                elif auto_priority == 2: # wavve < tving
                    auto_wavve_whitelist = list(set(auto_wavve_whitelist) - set(auto_tving_whitelist))
            elif auto_wavve_whitelist_active:
                auto_wavve_whitelist, auto_wavve_total = LogicNormal.wavve_get_cfpopular_list(auto_wavve_whitelist_limit)
            elif auto_tving_whitelist_active:
                auto_tving_whitelist, auto_tving_total = LogicNormal.tving_get_popular_list(auto_tving_whitelist_limit)

            if auto_wavve_whitelist_active:
                cur_wavve_whitelist = LogicNormal.wavve_get_whitelist()
                new_wavve_whitelist = list(set(cur_wavve_whitelist + auto_wavve_whitelist))
                if auto_delete:
                    new_wavve_whitelist = LogicNormal.wavve_purge_whitelist(new_wavve_whitelist)
                ret = LogicNormal.wavve_set_whitelist(new_wavve_whitelist)
                if ret:
                    added_whitelist = list(set(new_wavve_whitelist) - set(cur_wavve_whitelist))
                    if len(added_whitelist):
                        added_whitelist_program = ', '.join(added_whitelist)
                        logger.info('added_wavve_programs:%s', added_whitelist_program)
                        for title in added_whitelist:
                            data = {}
                            data['source'] = 'wavve'
                            data['title'] = title
                            data['img_url'] = ''
                            data['program_id'] = ''
                            data['episode_id'] = ''
                            try:
                                total = next((x for x in auto_wavve_total if x['title'] == title), False)
                                data['img_url'] = total['img_url']
                                data['program_id'] = total['program_id']
                                data['episode_id'] = total['episode_id']
                            except Exception as e:
                                pass
                            ModelAutoHistory.save(data)

            if auto_tving_whitelist_active:
                cur_tving_whitelist = LogicNormal.tving_get_whitelist()
                new_tving_whitelist = list(set(cur_tving_whitelist + auto_tving_whitelist))
                if auto_delete:
                    new_tving_whitelist = LogicNormal.tving_purge_whitelist(new_tving_whitelist)
                ret = LogicNormal.tving_set_whitelist(new_tving_whitelist)
                if ret:
                    added_whitelist = list(set(new_tving_whitelist) - set(cur_tving_whitelist))
                    if len(added_whitelist):
                        added_whitelist_program = ', '.join(added_whitelist)
                        logger.info('added_tving_programs:%s', added_whitelist_program)
                        for title in added_whitelist:
                            data = {}
                            data['source'] = 'tving'
                            data['title'] = title
                            data['img_url'] = ''
                            data['program_id'] = ''
                            data['episode_id'] = ''
                            try:
                                total = next((x for x in auto_tving_total if x['title'] == title), False)
                                data['img_url'] = 'image.tving.com' + total['img_url']
                                data['program_id'] = total['program_id']
                                data['episode_id'] = total['episode_id']
                            except Exception as e:
                                pass
                            ModelAutoHistory.save(data)

            logger.debug('=======================================')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    #########################################################
    
    @staticmethod
    def wavve_get_search_json(keyword, type='all', page=1):
        try:
            param = LogicNormal.wavve_config['base_parameter'].copy()
            param['type'] = type
            param['keyword'] = keyword
            param['offset'] = (int(page) - 1) * 20
            param['limit'] = 20
            param['orderby'] = 'score'
            url = '%s/search?%s' % (LogicNormal.wavve_config['base_url'], py_urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_get_search_json(keyword, type='all', page=1):
        try:
            param = {}
            param['kwd'] = keyword
            param['notFoundText'] = keyword
            default_param = 'siteName=TVING_WEB&category=PROGRAM&pageNum=%s&pageSize=50&indexType=both&methodType=allwordthruindex&payFree=ALL&runTime=ALL&grade=ALL&genre=ALL&screen=CSSD0100&os=CSOD0900&network=CSND0900&sort1=ins_dt&sort2=frequency&sort3=NO&type1=desc&type2=desc&type3=desc&fixedType=Y&spcMethod=someword&spcSize=0&adult_yn=&reKwd=&xwd=' % page
            url = '%s/search/getSearch.jsp?%s&%s' % (LogicNormal.tving_config['search_url'], default_param, py_urllib.urlencode(param))
            res = requests.get(url)
            data = res.json()
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def wavve_get_popular_json(type='all'):
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
            # url = '%s/vod/popularprograms?%s' % (LogicNormal.wavve_config['base_url'], py_urllib.urlencode(param))
            url = '%s/vod/popularcontents?%s' % (LogicNormal.wavve_config['base_url'], py_urllib.urlencode(param))
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
    def wavve_get_cfpopular_json(type='all'):
        try:
            param = LogicNormal.wavve_config['base_parameter'].copy()
            param['uiparent'] = 'FN0'
            param['uirank'] = '0'
            if type == 'dra':
                param['genre'] = '01'
                param['broadcastid'] = 'FN0_VN327_pc'
                param['uitype'] = 'VN327'
            elif type == 'ent':
                param['genre'] = '02'
                param['broadcastid'] = 'FN0_VN326_pc'
                param['uitype'] = 'VN326'
            elif type == 'doc':
                param['genre'] = '03'
                param['broadcastid'] = 'FN0_VN328_pc'
                param['uitype'] = 'VN328'
            else:
                param['genre'] = 'all' # 01 드라마, 02 예능, 03 시사교양, 09 해외시리즈, 08 애니메이션, 06 키즈, 05 스포츠
                param['broadcastid'] = 'FN0_VN327_pc' # unknown
                param['uitype'] = 'VN327' # unknown
            param['WeekDay'] = 'all'
            param['came'] = 'broadcast'
            param['subgenre'] = 'all'
            param['channel'] = 'all'
            param['contenttype'] = 'vod'
            param['offset'] = '0'
            param['limit'] = '30'
            param['orderby'] = 'viewtime'
            url = '%s/cf/vod/popularcontents?%s' % (LogicNormal.wavve_config['base_url'], py_urllib.urlencode(param))
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
    def tving_get_popular_json(type='all', order='viewDay'):
        try:
            auto_tving_order = ModelSetting.get('auto_tving_order')
            
            param = {}
            if type == 'dra':
                param['multiCategoryCode'] = 'PCA'
            elif type == 'ent':
                param['multiCategoryCode'] = 'PCD'
            elif type == 'doc':
                param['multiCategoryCode'] = 'PCK'
            else:
                param['multiCategoryCode'] = ''
            # order : viewDay, viewWeek
            param['order'] = auto_tving_order
            default_param = 'pageNo=1&pageSize=30&adult=all&free=all&guest=all&scope=all&lastFrequency=y&personal=N&screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610'
            url = '%s/v2/media/episodes?%s&%s' % (LogicNormal.tving_config['base_url'], default_param, py_urllib.urlencode(param))
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
    def tving_get_SMTV_PROG_4K_json(type='program'):
        try:
            param = {}
            if type == 'program':
                param['positionKey'] = 'SMTV_PROG_4K'
            elif type == 'movie':
                param['positionKey'] = 'SMTV_MV_4K'
            default_param = 'screenCode=CSSD1200&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=aeef9047f92b9dc4ebabc71fe4b124bf&pocType=APP_Z_TVING_1.0'
            url = '%s/v2/operator/highlights?%s&%s' % (LogicNormal.tving_config['base_url'], default_param, py_urllib.urlencode(param))
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

    #########################################################

    @staticmethod
    def wavve_search_keyword(keyword, type='all', page=1):
        try:
            data = LogicNormal.wavve_get_search_json(keyword, type, page)

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
    def tving_search_keyword(keyword, type='all', page=1):
        try:
            data = LogicNormal.tving_get_search_json(keyword, type, page)

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
    def wavve_get_cfpopular_list(limit):
        try:
            # data = []
            # ret = LogicNormal.wavve_get_cfpopular_json()
            # if ret['ret']:
            #     data = [x['title_list'][0]['text'].strip() for x in ret['data']['cell_toplist']['celllist']]
            #     if limit > len(data):
            #         limit = len(data)
            #     data = data[:limit]
            #     # Ignore delimiter (,) in title.
            #     sdata = ', '.join(data)
            #     data = [x.strip() for x in sdata.split(',')]
            #     data = Util.get_list_except_empty(data)

            data = []
            data_total = []
            ret = LogicNormal.wavve_get_cfpopular_json()
            if ret['ret']:
                data = [x['title_list'][0]['text'].strip() for x in ret['data']['cell_toplist']['celllist']]
                for x in ret['data']['cell_toplist']['celllist']:
                    item = {}
                    item['source'] = 'wavve'
                    item['title'] = x['title_list'][0]['text'].strip()
                    item['img_url'] = x['thumbnail']
                    item['program_id'] = ''
                    item['episode_id'] = x['event_list'][0]['bodylist'][3].split(':')[1]
                    data_total.append(item)

                if limit > len(data):
                    limit = len(data)
                data = data[:limit]
                # Ignore delimiter (,) in title.
                sdata = ', '.join(data)
                data = [x.strip() for x in sdata.split(',')]
                data = Util.get_list_except_empty(data)
            return data, data_total
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def tving_get_popular_list(limit):
        try:
            # data = []
            # ret = LogicNormal.tving_get_popular_json()
            # if ret['ret']:
            #     data = [x['program']['name']['ko'].strip() for x in ret['data']['body']['result']]
            #     if limit > len(data):
            #         limit = len(data)
            #     data = data[:limit]
            #     # Ignore delimiter (,) in title.
            #     sdata = ', '.join(data)
            #     data = [x.strip() for x in sdata.split(',')]
            #     data = Util.get_list_except_empty(data)

            data = []
            data_total = []
            ret = LogicNormal.tving_get_popular_json()
            if ret['ret']:
                data = [x['program']['name']['ko'].strip() for x in ret['data']['body']['result']]
                for x in ret['data']['body']['result']:
                    item = {}
                    item['source'] = 'tving'
                    item['title'] = x['program']['name']['ko'].strip()
                    tmp = x['program']['image']
                    item['img_url'] = next((x for x in tmp if x['code'] == 'CAIP0900'), False)['url']
                    item['program_id'] = x['program']['code']
                    item['episode_id'] = x['episode']['code']
                    data_total.append(item)

                if limit > len(data):
                    limit = len(data)
                data = data[:limit]
                # Ignore delimiter (,) in title.
                sdata = ', '.join(data)
                data = [x.strip() for x in sdata.split(',')]
                data = Util.get_list_except_empty(data)
            return data, data_total
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
            url = 'https://search.daum.net/search?w=tot&q=%s' % py_urllib.quote(keyword.encode('utf8'))
            res = session.get(url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
            html = res.content
            #logger.debug(html)
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
            
    #########################################################
    
    @staticmethod
    def wavve_get_programs_in_db():
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
    def tving_get_programs_in_db():
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
    def wavve_purge_whitelist(whitelist_programs):
        try:
            import datetime
            from wavve.model import ModelWavveEpisode as ModelWavveEpisode
            month_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            query = db.session.query(ModelWavveEpisode.programtitle, ModelWavveEpisode.channelname)
            query = query.filter((ModelWavveEpisode.call == 'auto') & (ModelWavveEpisode.releasedate > month_ago))
            query = query.group_by(ModelWavveEpisode.programtitle)
            tmp = query.all()
            
            data = [x.programtitle.strip() for x in tmp]
            removed_whitelist_programs = []
            for item in list(set(whitelist_programs)):
                # if item not in data:
                if not any(item in s for s in data):
                    whitelist_programs.remove(item)
                    removed_whitelist_programs.append(item)

            if len(removed_whitelist_programs):
                removed_whitelist_program = ', '.join(removed_whitelist_programs)
                logger.info('removed_or_ignored_wavve_programs:%s', removed_whitelist_program)
            
            return whitelist_programs
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def tving_purge_whitelist(whitelist_programs):
        try:
            import datetime
            from tving.model import Episode as ModelTvingEpisode
            month_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%y%m%d')
            query = db.session.query(ModelTvingEpisode.program_name, ModelTvingEpisode.channel_name)
            query = query.filter((ModelTvingEpisode.call == 'auto') & (ModelTvingEpisode.broadcast_date > month_ago))
            query = query.group_by(ModelTvingEpisode.program_name)
            tmp = query.all()
            
            data = [x.program_name.strip() for x in tmp]
            removed_whitelist_programs = []
            for item in list(set(whitelist_programs)):
                # if item not in data:
                if not any(item in s for s in data):
                    whitelist_programs.remove(item)
                    removed_whitelist_programs.append(item)

            if len(removed_whitelist_programs):
                removed_whitelist_program = ', '.join(removed_whitelist_programs)
                logger.info('removed_or_ignored_tving_programs:%s', removed_whitelist_program)
            
            return whitelist_programs
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def wavve_get_whitelist():
        try:
            from wavve.model import ModelSetting as ModelWavveSetting
            whitelist_program = ModelWavveSetting.get('whitelist_program')
            whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
            whitelist_programs = Util.get_list_except_empty(whitelist_programs)
            return whitelist_programs
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def tving_get_whitelist():
        try:
            from tving.model import ModelSetting as ModelWavveSetting
            whitelist_program = ModelWavveSetting.get('whitelist_program')
            whitelist_programs = [x.strip() for x in whitelist_program.replace('\n', ',').split(',')]
            whitelist_programs = Util.get_list_except_empty(whitelist_programs)
            return whitelist_programs
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    def wavve_set_whitelist(whitelist_programs):
        try:
            from wavve.model import ModelSetting as ModelWavveSetting
            whitelist_program = ', '.join(whitelist_programs)
            ModelWavveSetting.set('whitelist_program',whitelist_program)
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def tving_set_whitelist(whitelist_programs):
        try:
            from tving.model import ModelSetting as ModelTvingSetting
            whitelist_program = ', '.join(whitelist_programs)
            ModelTvingSetting.set('whitelist_program',whitelist_program)
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_plex_path(filepath):
        try:
            rule = ModelSetting.get('plex_path_rule')
            logger.debug('rule: %s', rule)
            if rule == u'' or rule.find('|') == -1:
                return filepath
            if rule is not None:
                tmp = rule.split('|')
                ret = filepath.replace(tmp[0], tmp[1])

                # SJVA-PMS의 플랫폼이 다른 경우
                if tmp[0][0] != tmp[1][0]:
                    if filepath[0] == '/': # Linux   -> Windows
                        ret = ret.replace('/', '\\')
                    else:                  # Windows -> Linux
                        ret = ret.replace('\\', '/')
                return ret

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def do_strm_proc(target_path, section_id):
        logger.debug('Thread started:do_strm_proc()')
        # STRM 파일 생성
        with open(target_path, 'w') as f: f.write('1')

        logger.debug('strm 파일 생성완료(%s)', target_path)
        data ={'type':'success', 'msg':'파일생성완료({p}): 스캔명령전송대기중({t}s)'.format(p=target_path, t=ModelSetting.get('plex_scan_delay'))}
        socketio.emit("notify", data, namespace='/framework', broadcate=True)

        while True:
            logger.debug('스캔명령 전송 대기...')
            time.sleep(ModelSetting.get_int('plex_scan_delay'))
            if os.path.isfile(target_path):
                break

        from plex.model import ModelSetting as PlexModelSetting
        server = PlexModelSetting.get('server_url')
        token = PlexModelSetting.get('server_token')
        logger.debug('스캔명령 전송: server(%s), token(%s), section_id(%s)', server, token, section_id)
        url = '{server}/library/sections/{section_id}/refresh?X-Plex-Token={token}'.format(server=server, section_id=section_id, token=token)

        res = requests.get(url)
        if res.status_code == 200:
            logger.debug('스캔명령 전송 완료: %s', target_path)
            data = {'type':'success', 'msg':'아이템({p}) 추가/스캔요청 완료.'.format(p=target_path)}
        else:
            logger.error('스캔명령 전송 실패: %s', target_path)
            data = {'type':'warning', 'msg':'스캔명령 전송 실패! 로그를 확인해주세요'}
        socketio.emit("notify", data, namespace='/framework', broadcate=True)

    @staticmethod
    def create_strm(ctype, title):
        try:
            logger.debug('strm 생성 요청하기(유형:%s, 제목:%s)', ctype, title)
            if ctype == 'show': library_path = ModelSetting.get('show_library_path')
            else: library_path = ModelSetting.get('movie_library_path')

            if not os.path.isdir(library_path):
                logger.error('show_library_path error(%s)', library_path)
                return {'ret':'error', 'data':'{c} 라이브러리 경로를 확인하세요.'.format(c=ctype)}

            target_path = os.path.join(library_path, title + '.strm')
            if os.path.isfile(target_path):
                return {'ret':'error', 'data':'({p})파일이 이미 존재합니다.'.format(p=target_path)}

            plex_path = LogicNormal.get_plex_path(library_path)
            logger.debug('local_path(%s), plex_path(%s)', library_path, plex_path)

            import plex
            section_id = plex.LogicNormal.get_section_id_by_filepath(plex_path)
            if section_id == -1:
                return {'ret':'error', 'data':'Plex경로오류! \"{p}\" 경로를 확인해 주세요'.format(p=plex_path)}

            logger.debug('get_section_id: path(%s), section_id(%s)', library_path, section_id)

            def func():
                time.sleep(1)
                LogicNormal.do_strm_proc(target_path, section_id)

            thread = threading.Thread(target=func, args=())
            thread.setDaemon(True)
            thread.start()

            logger.debug('%s 추가 요청 완료', title)
            return {'ret':'success', 'data':'{title} 추가요청 완료'.format(title=title)}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return {'ret':'error', 'data': '에러발생, 로그를 확인해주세요'}
