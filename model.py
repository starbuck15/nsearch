# -*- coding: utf-8 -*-
#########################################################
# python
import traceback
from datetime import datetime
import json
import os

# third-party
from sqlalchemy import or_, and_, func, not_, desc
from sqlalchemy.orm import backref

# sjva 공용
from framework import app, db, path_app_root
from framework.util import Util

# 패키지
from .plugin import logger, package_name

app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name))
#########################################################
        
class ModelSetting(db.Model):
    __tablename__ = '%s_setting' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
 
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value.strip()
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def get_int(key):
        try:
            return int(ModelSetting.get(key))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def get_bool(key):
        try:
            return (ModelSetting.get(key) == 'True')
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def set(key, value):
        try:
            item = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
            if item is not None:
                item.value = value.strip()
                db.session.commit()
            else:
                db.session.add(ModelSetting(key, value.strip()))
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def to_dict():
        try:
            return Util.db_list_to_dict(db.session.query(ModelSetting).all())
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                if key in ['scheduler', 'is_running']:
                    continue
                if key.startswith('tmp_'):
                    continue
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True                  
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.debug('Error Key:%s Value:%s', key, value)
            return False

    @staticmethod
    def save_recent_to_json(key, value):
        try:
            entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
            entity.value = json.dumps(value)
            db.session.commit()
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.debug('Error Key:%s Value:%s', key, value)
            return False

    @staticmethod
    def get_list(key):
        try:
            value = ModelSetting.get(key)
            values = [x.strip().replace(' ', '').strip() for x in value.replace('\n', '|').split('|')]
            values = Util.get_list_except_empty(values)
            return values
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_rule_dict(key):
        try:
            rule_dict = {}
            value = ModelSetting.get(key)
            values = [x.strip().replace(' ', '').strip() for x in value.split('\n')]
            values = Util.get_list_except_empty(values)
            for x in values:
                k, v = [y.strip().replace(' ','').strip() for y in x.split(',')]
                rule_dict[k] = v
            return rule_dict
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

class ModelAutoHistory(db.Model):
    __tablename__ = 'plugin_%s_auto_history' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)

    source = db.Column(db.String)
    title = db.Column(db.String)
    img_url = db.Column(db.String)
    program_id = db.Column(db.String)
    episode_id = db.Column(db.String)
    
    def __init__(self, source, title, img_url, program_id, episode_id):
        self.created_time = datetime.now()
        self.source = source
        self.title = title
        self.img_url = img_url
        self.program_id = program_id
        self.episode_id = episode_id

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') if self.created_time is not None else ''
        return ret

    @staticmethod
    def get_list(by_dict=False):
        try:
            tmp = db.session.query(ModelAutoHistory).all()
            if by_dict:
                tmp = [x.as_dict() for x in tmp]
            return tmp
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def save(data):
        try:
            item = ModelAutoHistory(data['source'], data['title'], data['img_url'], data['program_id'], data['episode_id'])
            db.session.add(item)
            db.session.commit()
            return item.id
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def web_list(req):
        try:
            ret = {}
            page = 1
            # page_size = ModelSetting.get_int('web_page_size')
            page_size = 30
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'search_word' in req.form:
                search = req.form['search_word']
            order = req.form['order'] if 'order' in req.form else 'desc'

            query = ModelAutoHistory.make_query(search=search, order=order)
            count = query.count()
            query = query.limit(page_size).offset((page-1)*page_size)
            logger.debug('ModelAutoHistory count:%s', count)
            lists = query.all()
            ret['list'] = [item.as_dict() for item in lists]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def make_query(search='', order='desc'):
        query = db.session.query(ModelAutoHistory)
        if search is not None and search != '':
            if search.find('|') != -1:
                tmp = search.split('|')
                conditions = []
                for tt in tmp:
                    if tt != '':
                        conditions.append(ModelAutoHistory.title.like('%'+tt.strip()+'%') )
                query = query.filter(or_(*conditions))
            elif search.find(',') != -1:
                tmp = search.split(',')
                for tt in tmp:
                    if tt != '':
                        query = query.filter(ModelAutoHistory.title.like('%'+tt.strip()+'%'))
            else:
                query = query.filter(or_(ModelAutoHistory.title.like('%'+search+'%'), ModelAutoHistory.title.like('%'+search+'%')))

        if order == 'desc':
            query = query.order_by(desc(ModelAutoHistory.id))
        else:
            query = query.order_by(ModelAutoHistory.id)

        return query
