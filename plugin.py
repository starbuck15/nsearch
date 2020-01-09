# -*- coding: utf-8 -*-
#########################################################
# 고정영역
#########################################################
# python
import os
import sys
import traceback

# third-party
from flask import Blueprint, request, Response, render_template, redirect, jsonify
from flask_login import login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler
from framework.util import Util
from system.logic import SystemLogic
            
# 패키지
from .logic import Logic
from .model import ModelSetting

package_name = __name__.split('.')[0]
logger = get_logger(package_name)

blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

plugin_info = {
    'version' : '0.0.2',
    'name' : 'nSearch',
    'category_name' : 'vod',
    'icon' : '',
    'developer' : 'starbuck',
    'description' : 'Search',
    'home' : 'https://github.com/starbuck15/nsearch',
    'more' : 'https://github.com/starbuck15/nsearch',
    'zip' : 'https://github.com/starbuck15/nsearch/archive/master.zip'
}
#########################################################

# 메뉴 구성.
menu = {
    'main' : [package_name, '검색'],
    'sub' : [
        ['search', '검색'], ['tving4k', '티빙 UHD 4K'], ['ratings', '시청률 순위'], ['log', '로그']
    ],
    'category' : 'vod',
}

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/search' % package_name)

@blueprint.route('/<sub>')
@login_required
def detail(sub): 
    if sub == 'search':
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            # arg['wavve_plugin'] = request.args.get('wavve_plugin')
            # arg['tving_plugin'] = request.args.get('tving_plugin')
            # arg['code'] = request.args.get('code')
            # return render_template('%s_search.html' % package_name, sub=sub, arg=arg)
            return render_template('%s_search.html' % (package_name), arg=arg)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    if sub == 'tving4k':
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            return render_template('%s_tving4k.html' % (package_name), arg=arg)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    if sub == 'ratings':
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            return render_template('%s_ratings.html' % (package_name), arg=arg)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI (보통 웹에서 요청하는 정보에 대한 결과를 리턴한다.)
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
def ajax(sub):
    logger.debug('AJAX %s %s', package_name, sub)
    if sub == 'setting_save':
        try:
            ret = Logic.setting_save(request)
            return jsonify(ret)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    elif sub == 'wavve_search':
        try:
            keyword = request.form['keyword']
            type = request.form['type']
            page = request.form['page']
            ret = Logic.wavve_search_keyword(keyword, type, page)
            return jsonify(ret)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    elif sub == 'tving_search':
        try:
            keyword = request.form['keyword']
            type = request.form['type']
            page = request.form['page']
            ret = Logic.tving_search_keyword(keyword, type, page)
            return jsonify(ret)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    elif sub == 'tving4k':
        try:
            type = request.form['type']
            ret = Logic.tving_get_SMTV_PROG_4K_list(type)
            return jsonify(ret)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    elif sub == 'ratings':
        try:
            keyword = request.form['keyword']
            ret = Logic.daum_get_ratings(keyword)
            return jsonify(ret)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return jsonify('fail')

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
def api(sub):
    logger.debug('api %s %s', package_name, sub)
    
