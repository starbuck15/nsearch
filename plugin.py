# -*- coding: utf-8 -*-
#########################################################
# 고정영역
#########################################################
# python
import os
import traceback

# third-party
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify, session, send_from_directory 
from flask_socketio import SocketIO, emit, send
from flask_login import login_user, logout_user, current_user, login_required

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_data, socketio, path_app_root, check_api
from framework.util import Util
from system.logic import SystemLogic

# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

from .model import ModelSetting, ModelAutoHistory
from .logic import Logic
from .logic_normal import LogicNormal

#########################################################


#########################################################
# 플러그인 공용                                       
#########################################################
blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

menu = {
    'main' : [package_name, u'검색'],
    'sub' : [
        ['search', u'검색'], ['popular', u'인기 프로그램'], ['whitelist', u'화이트리스트'], ['log', u'로그']
    ],
    'category' : 'vod',
}

plugin_info = {
    'version' : '0.0.8',
    'name' : 'nSearch',
    'category_name' : 'vod',
    'icon' : '',
    'developer' : 'starbuck',
    'description' : 'Search',
    'home' : 'https://github.com/starbuck15/nsearch',
    'more' : 'https://github.com/starbuck15/nsearch',
    'zip' : 'https://github.com/starbuck15/nsearch/archive/master.zip'
}

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()


#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/search' % package_name)

@blueprint.route('/<sub>')
@login_required
def detail(sub): 
    try:
        if sub == 'search':
            arg = {}
            arg['package_name']  = package_name
            return render_template('%s_%s.html' % (package_name, sub), arg=arg)
        elif sub == 'popular':
            return redirect('/%s/%s/ratings' % (package_name, sub))
        elif sub == 'whitelist':
            return redirect('/%s/%s/history' % (package_name, sub))
        elif sub == 'log':
            return render_template('log.html', package=package_name)
        return render_template('sample.html', title='%s - %s' % (package_name, sub))
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())


@blueprint.route('/<sub>/<sub2>')
@login_required
def second_menu(sub, sub2):
    try:
        if sub == 'popular':
            if sub2 == 'setting':
                arg = ModelSetting.to_dict()
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
            elif sub2 == 'ratings':
                arg = {}
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
            elif sub2 == 'wavve':
                arg = {}
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
            elif sub2 == 'tving':
                arg = {}
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
            elif sub2 == 'tving4k':
                arg = {}
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
        elif sub == 'whitelist':
            if sub2 == 'setting':
                arg = ModelSetting.to_dict()
                arg['package_name']  = package_name
                arg['scheduler'] = str(scheduler.is_include(package_name))
                arg['is_running'] = str(scheduler.is_running(package_name))
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
            elif sub2 == 'wavve':
                arg = {}
                arg['package_name']  = package_name
                wavve_programs = LogicNormal.wavve_get_programs_in_db()
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg, wavve_programs=wavve_programs)
            elif sub2 == 'tving':
                arg = {}
                arg['package_name']  = package_name
                tving_programs = LogicNormal.tving_get_programs_in_db()
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg, tving_programs=tving_programs)
            elif sub2 == 'history':
                arg = {}
                arg['package_name']  = package_name
                return render_template('%s_%s_%s.html' % (package_name, sub, sub2), arg=arg)
        elif sub == 'log':
            return render_template('log.html', package=package_name)
        return render_template('sample.html', title='%s - %s' % (package_name, sub))
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

#########################################################
# For UI
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    logger.debug('AJAX %s %s', package_name, sub)
    try:
        if sub == 'setting_save':
            try:
                ret = ModelSetting.setting_save(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'scheduler':
            try:
                go = request.form['scheduler']
                logger.debug('scheduler :%s', go)
                if go == 'true':
                    Logic.scheduler_start()
                else:
                    Logic.scheduler_stop()
                return jsonify(go)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'one_execute':
            try:
                ret = Logic.one_execute()
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'reset_db':
            try:
                ret = Logic.reset_db()
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'reset_whitelist':
            try:
                ret = Logic.reset_whitelist()
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'wavve_search':
            try:
                keyword = request.form['keyword']
                type = request.form['type']
                page = request.form['page']
                ret = LogicNormal.wavve_search_keyword(keyword, type, page)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'tving_search':
            try:
                keyword = request.form['keyword']
                type = request.form['type']
                page = request.form['page']
                ret = LogicNormal.tving_search_keyword(keyword, type, page)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'wavve_whitelist_save':
            try:
                whitelist_programs = request.form.getlist('wavve_whitelist[]')
                ret = LogicNormal.wavve_set_whitelist(whitelist_programs)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'tving_whitelist_save':
            try:
                whitelist_programs = request.form.getlist('tving_whitelist[]')
                ret = LogicNormal.tving_set_whitelist(whitelist_programs)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'wavve_popular':
            try:
                type = request.form['type']
                # ret = LogicNormal.wavve_get_popular_list(type) # Unwanted thumbnail
                ret = LogicNormal.wavve_get_cfpopular_json(type)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'tving_popular':
            try:
                type = request.form['type']
                ret = LogicNormal.tving_get_popular_json(type)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'tving4k':
            try:
                type = request.form['type']
                ret = LogicNormal.tving_get_SMTV_PROG_4K_json(type)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'ratings':
            try:
                keyword = request.form['keyword']
                ret = LogicNormal.daum_get_ratings_list(keyword)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

        elif sub == 'history':
            try:
                ret = ModelAutoHistory.web_list(request)
                return jsonify(ret)
            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')

    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
@check_api
def api(sub):
    logger.debug('api %s %s', package_name, sub)
    
