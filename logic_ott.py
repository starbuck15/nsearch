# -*- coding: utf-8 -*-
#########################################################
# python
import os
import datetime
import traceback
from datetime import datetime, timedelta
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

class LogicOtt(object):
    OttShowList = []
    OttMovieList = []

    PrevWavveRecentItem = None
    PrevTvingRecentItem = None

    @staticmethod
    def ott_show_scheduler_function():
        try:
            logger.debug('[schedule] ott_show scheduler_function start..')

            wavve_list = LogicOtt.get_recent_wavve_list()
            tving_list = LogicOtt.get_recent_tving_list()
            recent_list = wavve_list+tving_list

            target_list = []

            logger.debug('[schedule] recent vod items:{n}, T({t}), W({w})'.
                format(n=len(recent_list), w=LogicOtt.PrevWavveRecentItem['title'], t=LogicOtt.PrevTvingRecentItem['title']))

            for recent in recent_list:
                daum_info = LogicOtt.get_daum_tv_info(recent['title'])
                for item in LogicOtt.OttShowList:
                    #logger.debug('title r({r}),m({m})'.format(r=recent['title'],m=item['title']))
                    if item['status'] != 1: continue # 방영중이 아닌 경우 제외
                    if daum_info and daum_info['code'] != '':
                        if daum_info['code'] == item['code']:
                            logger.debug('[schedule] 메타갱신 대상에 추가(%s)', item['title'])
                            target_list.append(item)
                    else:
                        if recent['title'] == item['title'].encode('utf-8'):
                            logger.debug('[schedule] 메타갱신 대상에 추가(%s)', item['title'])
                            target_list.append(item)

            if len(target_list) > 0: LogicOtt.do_metadata_refresh(target_list)
            else: logger.debug('[schedule] no target item(s) recent vod')

            """
            wd = [u'월', u'화', u'수', u'목', u'금', u'토', u'일']

            sch_interval = ModelSetting.get_int('ott_show_scheduler_interval') # 분
            delay = ModelSetting.get_int('meta_update_delay') #분
            target_list = []

            # 대상설정 방송시간이 a-b 사이에 있는 작품을 대상으로 함
            now = datetime.now()
            a_time = now - timedelta(minutes=(delay + sch_interval + 5))
            b_time = now - timedelta(minutes=(delay - sch_interval - 5))

            logger.info('[schedule] 메타 갱신대상 시간: {a} ~ {b}'.format(a=a_time.strftime('%Y-%m-%d %H:%M:%S'),b=b_time.strftime('%Y-%m-%d %H:%M:%S')))
            # 대상 요일 설정
            twday = wd[a_time.weekday()]

            for item in LogicOtt.OttShowList:
                if item['status'] != 1: continue # 방영중이 아닌 경우 제외
                if 'broadcast_info' not in item.keys(): continue # 방영정보가 없는 경우 제외
                if item['broadcast_info'] is None: continue
                if 'wdays' not in item['broadcast_info'].keys(): continue

                wdays = item['broadcast_info']['wdays']
                broadcast_time = (item['broadcast_info']['hour'] * 100) + item['broadcast_info']['min']
                a = a_time.hour * 100 + a_time.minute
                b = b_time.hour * 100 + b_time.minute

                if a_time.day == b_time.day:
                    if twday not in wdays: continue
                    if a > b: # 날짜가 바뀐 경우
                        if broadcast_time  >= a or broadcast_time <= b:
                            logger.debug('[schedule] 메타갱신 대상에 추가(%s)', item['title'])
                            target_list.append(item)
                    else:
                        if broadcast_time  >= a and broadcast_time <= b:
                            logger.debug('[schedule] 메타갱신 대상에 추가(%s)', item['title'])
                            target_list.append(item)

            if len(target_list) > 0:
                LogicOtt.do_metadata_refresh(target_list)
            """

            logger.debug('[schedule] ott_show scheduler_function end..')

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False


    @staticmethod
    def get_recent_wavve_list():
        try:
            wavve_list = []
            import framework.wavve.api as Wavve
            vod_list = Wavve.vod_newcontents(page=1)['list']
            for vod in vod_list:
                item = dict()
                item['title'] = LogicOtt.change_text_for_use_filename(vod['programtitle'])
                item['code'] = vod['programid']
                item['channel'] = vod['channelname']
                item['episode'] = vod['episodenumber']
                item['qvod'] = True if vod['episodetitle'].find('Quick VOD') != -1 else False

                #logger.debug('{t},{e},{q}'.format(t=item['title'],e=item['episode'],q=item['qvod']))
                wavve_list.append(item)

            logger.debug('[schedule] wavve: recent count: {n}'.format(n=len(wavve_list)))

            # TODO: 여러페이지 탐색 처리
            if LogicOtt.PrevWavveRecentItem != None and LogicOtt.PrevWavveRecentItem in wavve_list:
                idx = wavve_list.index(LogicOtt.PrevWavveRecentItem)
                wavve_list = wavve_list[:idx]

            if len(wavve_list) > 0:
                LogicOtt.PrevWavveRecentItem = wavve_list[0]
                ModelSetting.save_recent_to_json('prev_wavve_recent_json', wavve_list[0])

            logger.debug('[schedule] wavve: recent vod items(processed):{n}'.format(n=len(wavve_list)))
            return wavve_list
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_recent_tving_list():
        try:
            tving_list = list()

            import framework.tving.api as Tving
            from tving.basic import TvingBasic
            from tving.model import Episode
            vod_list = Tving.get_vod_list(page=1)['body']['result']
            for vod in vod_list:
                episode = Episode('auto')
                json_data, url = TvingBasic.get_episode_json(vod['episode']['code'], 'FHD')
                episode = TvingBasic.make_episode_by_json(episode, json_data, url)
                quick_vod = True if url.find('quick_vod') != -1 else False

                item = dict()
                item['title'] = LogicOtt.change_text_for_use_filename(vod['program']['name']['ko'])
                item['code'] = vod['program']['code']
                item['channel'] = vod['channel']['name']['ko']
                item['episode'] = vod['episode']['frequency']
                item['qvod'] = quick_vod

                #logger.debug('{t},{e},{q}'.format(t=item['title'],e=item['episode'],q=item['qvod']))
                tving_list.append(item)

            logger.debug('[schedule] tving: recent count: {n}'.format(n=len(tving_list)))

            # TODO: 여러페이지 탐색 처리
            if LogicOtt.PrevTvingRecentItem != None and LogicOtt.PrevTvingRecentItem in tving_list:
                idx = tving_list.index(LogicOtt.PrevTvingRecentItem)
                tving_list = tving_list[:idx]

            if len(tving_list) > 0:
                LogicOtt.PrevTvingRecentItem = tving_list[0]
                ModelSetting.save_recent_to_json('prev_tving_recent_json', tving_list[0])

            logger.debug('[schedule] tving: recent vod items(processed):{n}'.format(n=len(tving_list)))
            return tving_list
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_recent_vod_list():
        try:
            wavve_list = LogicOtt.get_recent_wavve_list()
            tving_list = LogicOtt.get_recent_tving_list()
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_plex_path(filepath):
        try:
            rule = ModelSetting.get('plex_path_rule')
            #logger.debug('rule: %s', rule)
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
    def change_text_for_use_filename(text):
        try:
            import re
            return re.sub('[\\/:*?\"<>|]', '', text).strip()
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def do_strm_proc(ctype, target_path, section_id):
        logger.debug('Thread started:do_strm_proc()')

        title = os.path.splitext(os.path.basename(target_path))[0]

        if ctype == 'show': # TV show ott 
            daum_info = LogicOtt.get_daum_tv_info(title)
            if daum_info is None:
                logger.debug('메타데이터 조회 실패(%s)', title)
                data ={'type':'warning', 'msg':'메타데이터 조회 실패({t})'.format(t=title)}
                socketio.emit("notify", data, namespace='/framework', broadcate=True)
                return
        else: # Movie ott
            daum_info = {'movie':'TODO'}

        # 파일생성: 최초
        LogicOtt.save_dauminfo_to_file(target_path, daum_info)
        logger.debug('strm 파일 생성완료(%s)', target_path)
        data ={'type':'success', 'msg':'파일생성완료({p}): 스캔명령전송대기중({t}s)'.format(p=target_path, t=ModelSetting.get('plex_scan_delay'))}
        socketio.emit("notify", data, namespace='/framework', broadcate=True)

        cnt = 0
        while True:
            if cnt > 30: break
            logger.debug('스캔명령 전송 대기...')
            time.sleep(ModelSetting.get_int('plex_scan_delay'))
	    cnt += 1
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

            filename = LogicOtt.change_text_for_use_filename(title)
            target_path = os.path.join(library_path, filename + '.strm')
            if os.path.isfile(target_path):
                return {'ret':'error', 'data':'({p})파일이 이미 존재합니다.'.format(p=target_path)}

            plex_path = LogicOtt.get_plex_path(library_path)
            logger.debug('local_path(%s), plex_path(%s)', library_path, plex_path)

            import plex
            section_id = plex.LogicNormal.get_section_id_by_filepath(plex_path)
            if section_id == -1:
                return {'ret':'error', 'data':'Plex경로오류! \"{p}\" 경로를 확인해 주세요'.format(p=plex_path)}

            logger.debug('get_section_id: path(%s), section_id(%s)', library_path, section_id)

            def func():
                time.sleep(1)
                LogicOtt.do_strm_proc(ctype, target_path, section_id)

            thread = threading.Thread(target=func, args=())
            thread.setDaemon(True)
            thread.start()

            logger.debug('%s 추가 요청 완료', target_path)
            return {'ret':'success', 'data':'{title} 추가요청 완료'.format(title=title)}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return {'ret':'error', 'data': '에러발생, 로그를 확인해주세요'}

    @staticmethod
    def get_extra_meta(fpath, daum_info):
        try:
            with open(fpath, 'w') as f:
                json.dump(daum_info, f, indent=2)

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def append_item_to_show_list(newitem):
        try:
            for item in LogicOtt.OttShowList:
                if item['file_path'] == newitem['file_path']:
                    logger.info('already exist in OttShowList(%s)', item['file_path'])
                    return

            LogicOtt.OttShowList.append(newitem)

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def save_dauminfo_to_file(fpath, daum_info):
        try:
            from datetime import datetime as dt
            with open(fpath, 'w') as f:
                json.dump(daum_info, f, indent=2)

            stat = os.stat(fpath)
            title = os.path.splitext(os.path.basename(fpath))[0]

            item = {}
            item['title'] = title
            item['ctime'] = dt.now().strftime('%Y-%m-%d %H:%M:%S')
            item['mtime'] = dt.now().strftime('%Y-%m-%d %H:%M:%S')
            item['file_path'] = fpath
            item['plex_path'] = LogicOtt.get_plex_path(fpath)

            item['status'] = daum_info['status']
            item['code'] = daum_info['code']
            item['poster_url'] = daum_info['poster_url']
            item['genre'] = daum_info['genre']
            if item['status'] == 1:
                item['broadcast_info'] = daum_info['broadcast_info']

            LogicOtt.append_item_to_show_list(item)

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def load_dauminfo_from_file(fpath):
        try:
            with open(fpath, 'r') as f:
                daum_info = json.load(f)
            return daum_info
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def parse_broadcast_info(broadcast_str):
        try:
            import re
            wd = [u'월', u'화', u'수', u'목', u'금', u'토', u'일']
            rx = r'(?P<wday>.+)\s(?P<ampm>오후|오전)\s(?P<hour>\d{1,2})[:](?P<min>\d{1,2})'

            ret = {}
            wdays = []

            #logger.debug('broadcast_str: %s', broadcast_str)
            match = re.compile(rx).search(broadcast_str.encode('utf-8'))
            #logger.debug(match)
            if match:
                wday = match.group('wday')
                tm_hour = int(match.group('hour'))
                tm_min = int(match.group('min'))
                # 요일
                if wday.find(u'~') != -1:  # 월~금 형태
                    tmp = wday.split(u'~')
                    wdays = wd[wd.index(tmp[0].strip()):wd.index(tmp[1].strip())+1]
                else: # 월, 화, 수.. 형태
                    for w in wday.split(','):
                        wdays.append(w.strip())
                # 시간: 24시간 형태로 변경
                if match.group('ampm') == '오후':
                    tm_hour += 12
                return {'wdays': wdays, 'hour': tm_hour, 'min':tm_min}

            logger.error('parse_broadcast_info() failed')

            return None

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_daum_tv_info(title, fpath=None):
        try:
            from lib_metadata import SiteDaumTv
            daum_info = {}

            if fpath is None:
                ret = SiteDaumTv.search(title)
                if ret['ret'] != 'success':
                    logger.error('failed to get daum metadata info(%s)', title)
                    return None
                info = ret['data']

                daum_info['code'] = info['code'] if 'code' in info.keys() else ''
                # 1: 방송중, 2: 종영, 0: 방송예정
                daum_info['status'] = info['status'] if 'status' in info.keys() else -1
                daum_info['poster_url'] = info['image_url'] if 'image_url' in info.keys() else ''
                daum_info['genre'] = info['genre'] if 'genre' in info.keys() else ''

                tmpinfo = info['broadcast_info'] if 'broadcast_info' in info.keys() else ''
                #logger.debug('broadcast_info')
                #logger.debug(tmpinfo)
                # 방영중인 경우에만 처리
                if tmpinfo != '' and daum_info['status'] == 1:
                    daum_info['broadcast_info'] = LogicOtt.parse_broadcast_info(tmpinfo)
            else:
                daum_info = LogicOtt.load_dauminfo_from_file(fpath)
                # 파일이 이전파일인 경우 갱신
                if 'code' not in daum_info.keys():
                    ret = SiteDaumTv.search(title)
                    if ret['ret'] != 'success':
                        logger.error('failed to get daum metadata info(%s)', title)
                        return None
                    info = ret['data']

                    daum_info['code'] = info['code'] if 'code' in info.keys() else ''
                    # 1: 방송중, 2: 종영, 0: 방송예정
                    daum_info['status'] = info['status'] if 'status' in info.keys() else -1
                    daum_info['poster_url'] = info['image_url'] if 'image_url' in info.keys() else ''
                    daum_info['genre'] = info['genre'] if 'genre' in info.keys() else ''

                    tmpinfo = info['broadcast_info'] if 'broadcast_info' in info.keys() else ''
                    # 임시 예외처리
                    tmpinfo = tmpinfo.replace('&nbsp;', ' ').replace('&nbsp', ' ')
                    logger.debug('broadcast_info')
                    logger.debug(tmpinfo)
                    # 방영중인 경우에만 처리
                    if tmpinfo != '' and daum_info['status'] == 1:
                        daum_info['broadcast_info'] = LogicOtt.parse_broadcast_info(tmpinfo)
                        logger.debug(daum_info['broadcast_info'])


                    LogicOtt.save_dauminfo_to_file(fpath, daum_info)

            return daum_info

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def load_show_items():
        try:
            logger.info('load_show_items(): started')
            from datetime import datetime as dt

            library_path = ModelSetting.get('show_library_path')
            # SJVA에서 GDrive를 마운트 하는 경우 대응
            while not os.path.isdir(library_path):
                logger.error('failed to load show items')
                time.sleep(0.5)

            for fname in os.listdir(library_path):
                file_path = os.path.join(library_path, fname)
                if not os.path.isfile(file_path):
                    continue

                stat = os.stat(file_path)
                title = os.path.splitext(fname)[0]
                ctime = stat.st_ctime
                mtime = stat.st_mtime

                item = {}
                item['title'] = title
                item['ctime'] = dt.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
                item['mtime'] = dt.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                item['file_path'] = file_path
                item['plex_path'] = LogicOtt.get_plex_path(file_path)


                daum_info = LogicOtt.get_daum_tv_info(title, fpath=file_path)
                item['status'] = daum_info['status']
                item['code'] = daum_info['code']
                item['poster_url'] = daum_info['poster_url']
                item['genre'] = daum_info['genre']
                if item['status'] == 1:
                    item['broadcast_info'] = daum_info['broadcast_info']

                LogicOtt.append_item_to_show_list(item)

            logger.info('load_show_items(): %d items loaded', len(LogicOtt.OttShowList))

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def plexott_show_list(req):
        try:
            logger.debug(req.form)
            wds = {'mon':u'월','tue':u'화','wed':u'수','thu':u'목','fri':u'금','sat':u'토','sun':u'일'}
            grs = {'dra':u'드라마', 'ent':u'예능'}
            ret = {}
            search_word = None

            if req.form['search_word'] != u'': search_word = req.form['search_word']
            logger.debug('search_word: %s', search_word)

            wtype = req.form['wtype'] # week-day
            gtype = req.form['gtype'] # genre
            showlist = LogicOtt.OttShowList[:]
            slist = []

            # 검색어 처리
            if search_word:
                for item in LogicOtt.OttShowList:
                    if item['title'].decode('utf-8').find(search_word) != -1:
                        slist.append(item)
            else:
                slist = showlist[:]

            if wtype == 'all' and gtype == 'all':
                ret['list'] = slist
                ret['ret'] = 'success'
                return ret

            # 장르 처리
            glist = []
            for item in slist:
                if gtype == 'all':
                    glist.append(item)
                elif gtype == 'dra' or gtype == 'ent':
                    if item['genre'] == grs[gtype]:
                        glist.append(item)
                else:
                    if item['genre'] != u'드라마' and item['genre'] != u'예능':
                        glist.append(item)

            # 전체요일이면 그냥 리턴
            if wtype == 'all':
                ret['list'] = glist
                ret['ret'] = 'success'
                return ret

            wlist = []
            if wtype == 'onair': # 방영중
                for item in glist:
                    if item['status'] == 1: wlist.append(item)
                ret['ret'] = 'success'
                ret['list'] = wlist
                return ret
            if wtype == 'end': #종영
                for item in glist:
                    if item['status'] == 2: wlist.append(item)
                ret['list'] = wlist
                ret['ret'] = 'success'
                return ret

            # 요일이 지정된 경우
            wday = wds[wtype]
            for item in glist:
                # 방영중이 아닌경우 스킵
                #logger.debug(item)
                if item['status'] != 1: continue
                if item['broadcast_info'] is None: continue
                if 'broadcast_info' not in item.keys(): continue

                # 비대상 요일 처리
                #logger.debug('wday:%s,wdays:%s', wday, ",".join(item['broadcast_info']['wdays']))
                if wday in item['broadcast_info']['wdays']:
                    #logger.debug('match wday! %s', item['title'])
                    wlist.append(item)

            ret['list'] = wlist
            ret['ret'] = 'success'
            return ret

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def plexott_movie_list(req):
        try:
            from datetime import datetime as dt

            library_path = ModelSetting.get('show_library_path')
            ret = {}
            item_list = []
            if not os.path.isdir(library_path):
                return {'ret':'error', 'msg':'check tv-ott-path setting in nsearh plugin.'}

            for fname in os.listdir(library_path):
                file_path = os.path.join(library_path, fname)
                if not os.path.isfile(file_path):
                    continue

                stat = os.stat(file_path)

                title = os.path.splitext(fname)[0]
                ctime = stat.st_ctime
                mtime = stat.st_mtime

                item = {}
                item['title'] = title
                item['ctime'] = dt.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
                item['mtime'] = dt.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                item['file_path'] = file_path
                item['plex_path'] = LogicOtt.get_plex_path(file_path)


                daum_info = LogicOtt.get_daum_tv_info(title, fpath=file_path)
                item['status'] = daum_info['status']
                item['last_episode_date'] = daum_info['last_episode_date']
                item['last_episode_no'] = daum_info['last_episode_no']
                item['episode_count'] = daum_info['episode_count']
                item['poster_url'] = daum_info['poster_url']
                item['start_date'] = daum_info['start_date']
                if item['status'] == 1:
                    item['broadcast_info'] = daum_info['broadcast_info']

                item_list.append(item)

            ret['ret'] = 'success'
            ret['list'] = item_list
            return ret

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def do_metadata_refresh(tlist):
        try:
            import plex
            count = 0
            for item in tlist:
                logger.debug('메타데이터갱신: %s', item['plex_path'])
                plex.LogicNormal.metadata_refresh(item['plex_path'])
                count += 1

                logger.debug('Daum 정보 조회 및 갱신: %s', item['title'])
                daum_info = LogicOtt.get_daum_tv_info(item['title'])
                if daum_info is None:
                    logger.error('Daum 정보 조회실패: %s', item['title'])
                    continue

                # 방영상태가 바뀐 경우
                if item['status'] != daum_info['status']:
                    logger.debug('방영정보가 변경되어 파일갱신: %s', item['file_path'])
                    LogicOtt.save_dauminfo_to_file(item['file_path'], daum_info)
                    MemItem = LogicOtt.OttShowList[LogicOtt.OttShowList.index(item)]
                    MemItem['status'] = daum_info['status']

                if ModelSetting.get_bool('meta_update_notify'):
                    data = {'type':'success', 'msg':'메타데이터 갱신요청완료({p})'.format(p=item['plex_path'])}
                    socketio.emit("notify", data, namespace='/framework', broadcate=True)

                time.sleep(ModelSetting.get_int('meta_update_interval'))

            data = {'type':'success', 'msg':'메타데이터 갱신요청완료({n}건)'.format(n=count)}
            socketio.emit("notify", data, namespace='/framework', broadcate=True)

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            data = {'type':'warning', 'msg':'메타갱신실패, 로그를 확인해주세요'}
            socketio.emit("notify", data, namespace='/framework', broadcate=True)

    @staticmethod
    def show_metadata_refresh(req):
        try:
            logger.debug(req.form)
            ret = {}
            req_type = None
            if 'list' not in req.form.keys(): req_type = 'all'
            else: title_list = req.form['list'].split(u',')

            movie_list = LogicOtt.OttMovieList[:]
            target_list = []

            if req_type == 'all':
                target_list = movie_list
            else:
                for item in movie_list:
                    if item['title'] in title_list:
                        target_list.append(item)

            def func():
                time.sleep(3)
                LogicOtt.do_metadata_refresh(target_list)

            thread = threading.Thread(target=func, args=())
            thread.setDaemon(True)
            thread.start()

            ret = {'ret':'success', 'msg':'{n}개의 아이템 메타업테이트 요청 완료'.format(n=len(target_list))}
            return ret
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_metadata_refresh(req):
        try:
            logger.debug(req.form)
            ret = {}
            req_type = None
            if 'list' not in req.form.keys(): req_type = 'all'
            else: title_list = req.form['list'].split(u',')

            show_list = LogicOtt.OttShowList[:]
            target_list = []

            if req_type == 'all':
                target_list = show_list
            else:
                for item in show_list:
                    if item['title'] in title_list:
                        target_list.append(item)

            def func():
                time.sleep(3)
                LogicOtt.do_metadata_refresh(target_list)

            thread = threading.Thread(target=func, args=())
            thread.setDaemon(True)
            thread.start()

            ret = {'ret':'success', 'msg':'{n}개의 아이템 메타업테이트 요청 완료'.format(n=len(target_list))}
            return ret
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def do_remove_file(fpath):
        try:
            os.remove(fpath)
            data = {'type':'success', 'msg':'파일삭제 성공({f})'.format(f=fpath)}
            socketio.emit("notify", data, namespace='/framework', broadcate=True)

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            data = {'type':'warning', 'msg':'파일삭제실패, 로그를 확인해주세요'}
            socketio.emit("notify", data, namespace='/framework', broadcate=True)

    @staticmethod
    def remove_file(fpath):
        try:
            ret = {}
            if not os.path.isfile(fpath):
                return {'ret':'error', 'msg':'삭제실패: 존재하지 않는 파일입니다.'}

            for item in LogicOtt.OttShowList:
                if item['file_path'] == fpath:
                    LogicOtt.OttShowList.remove(item)

                    def func():
                        time.sleep(2)
                        LogicOtt.do_remove_file(fpath)

                    thread = threading.Thread(target=func, args=())
                    thread.setDaemon(True)
                    thread.start()

                    logger.debug('파일을 삭제요청 완료.(%s)', fpath)
                    ret = {'ret':'success', 'msg':'파일삭제 요청({f})'.format(f=fpath)}
                    return ret

            return {'ret':'error', 'msg':'리스트에 정보가 존재하지 않습니다.'}

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            return {'ret':'error', 'msg':'삭제실패(exception): 로그를 확인해주세요. '}

    @staticmethod
    def movie_search_tving(keyword):
        try:
            tlist = []
            import framework.tving.api as Tving
            l = Tving.search_tv(keyword)
            if not l: return []
            for r in l:
                m = dict()
                m['type'] = 'tving'
                m['title'] = r['mast_nm']
                m['code'] = r['mast_cd']
                m['year'] = r['broad_dt'][:4]
                m['poster_url'] = 'https://image.tving.com' + r['web_url']
                tlist.append(m)

            return tlist

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_search_wavve(keyword):
        try:
            wlist = []
            import framework.wavve.api as Wavve
            l = Wavve.search_movie(keyword)['list']
            # TODO: 에러처리
            if len(l) == 0: return []
            for i in l:
                movieid = i['movieid']
                r = Wavve.movie_contents_movieid(movieid)
                m = dict()
                m['type'] = 'wavve'
                m['title'] = r['title']
                m['code'] = r['movieid']
                m['year'] = r['releasedate'][:4] if 'releasedate' in r else '-'
                m['poster_url'] = 'https://' + r['image']
                wlist.append(m)

            return wlist

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_search(keyword):
        try:
            tlist = LogicOtt.movie_search_tving(keyword)
            wlist = LogicOtt.movie_search_wavve(keyword)
            movie_list = tlist + wlist
            return movie_list

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

