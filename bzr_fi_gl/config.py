# -*- coding: utf-8 -*-
'''
开阖ERP采用AGPL-3协议，版权(CopyRight)归以下代码提交者所有

2013    开阖软件 Jeff Wang,OpenERPJeff      (jeff@osbzr.com)            初始版本
2013    mrshelly                            (mrshelly@hotmail.com)
2013    buke                                (wangbuke@gmail.com)        add lru cache for get_amount in menu open
2013    joshuajan                           (popkar77@gmail.com)

'''

from openerp.osv import fields, osv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import openerp.addons.decimal_precision as dp
from openerp.addons.bzr_base import check_cycle
from openerp.addons.bzr_base.config import bzrcache

#凭证类型 fi.doc.type

class fi_doc_type(osv.osv):
    _name='fi.doc.type'
    _description=u'凭证字'
    _columns={
        'name':fields.char(u'凭证字',size=10,required=True),
    }
class fi_acc_type(osv.osv):
    _name='fi.acc.type'
    _description=u'科目类型'
    _columns={
        'name':fields.char(u'类型',size=64,required=True),
    }

class fi_report(osv.osv):
    _name='fi.report'
    _description=u'报表行'
    _order='type, sequence'
    def __compute(self, cr, uid, ids, field_name, arg, context=None):
        result={}
        period=self.pool.get('fi.period').find(cr,uid,
                  fields.date.context_today(self,cr,uid),context)
        for report in self.browse(cr, uid, ids, context=context):
            result[report.id] = self.get_amount(cr,uid,report.id,period,context)
        return result


    _columns={
        'name':fields.char(u'文本',size=128),
        'sequence':fields.integer(u'序号'),  # 有些报表行是没有行号的，所以要用这个来排序
        'line':fields.char(u'行号',size=4),
        'type':fields.selection([('1','资产负债表（资产）'),('2','资产负债表（负债和权益）'),('3','利润表'),('4','现金流量表')],string="所属报表"),
        'parent_id':fields.many2one('fi.report', u'上级'),
        'account_ids':fields.one2many('fi.acc','report_id',u'科目'),
        'children_ids':fields.one2many('fi.report','parent_id',u'下级'),
        'year_start':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                     string=u'年初余额',multi='balance'),
        'year_debit':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                     string=u'本年借方',multi='balance'),
        'year_credit':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                     string=u'本年贷方',multi='balance'),
        'period_start':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                    string=u'期初余额',multi='balance'),
        'period_debit':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                    string=u'本期借方',multi='balance'),
        'period_credit':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                    string=u'本期贷方',multi='balance'),
        'period_end':fields.function(__compute, digits_compute=dp.get_precision('Account'),
                    string=u'期末余额',multi='balance'),
    }

    @bzrcache()
    def get_amount(self,cr,uid,id,period_id,context=None):
        '''报表行的金额'''
        result ={
#        'report':id,             #报表行
#        'period':period_id,      #期间
        'year_start':0.00,       #年初余额
        'year_debit':0.00,       #本年借方
        'year_credit':0.00,      #本年贷方
        'period_start':0.00,     #期初余额
        'period_debit':0.00,     #本期借方
        'period_credit':0.00,    #本期贷方
        'period_end':0.00,       #期末余额
        }

        obj_period = self.pool.get('fi.period')
        obj_acc = self.pool.get('fi.acc')

        this_report = self.read(cr,uid,id,['children_ids',
                     'account_ids','reverse'],context=context)

        # 如有下级表行，汇总下级表行金额
        for child in this_report['children_ids']:
            l = self.get_amount(cr,uid,child,period_id,context)
            result['year_start']+=l['year_start']
            result['year_debit']+=l['year_debit']
            result['year_credit']+=l['year_credit']
            result['period_start']+=l['period_start']
            result['period_debit']+=l['period_debit']
            result['period_credit']+=l['period_credit']
            result['period_end']+=l['period_end']

        # 取得表行科目
        for acc in this_report['account_ids']:
            l = obj_acc.get_amount(cr,uid,acc,period_id,context)
            result['year_start']+=l['year_start']
            result['year_debit']+=l['year_debit']
            result['year_credit']+=l['year_credit']
            result['period_start']+=l['period_start']
            result['period_debit']+=l['period_debit']
            result['period_credit']+=l['period_credit']
            result['period_end']+=l['period_end']

        return result
    _constraints = [
        (check_cycle,u'不能创建循环的层级关系',['parent_id']),
                   ]
class fi_year(osv.osv):
    _name='fi.year'
    _description=u'会计年度'
    _columns = {
        'name':fields.char(u'会计年度',size=64,required=True),
        'company_id':fields.many2one('res.company',u'公司'),
        's_date':fields.date('开始日期',required=True),
        'e_date':fields.date(u'结束日期',required=True),
        'period_ids':fields.one2many('fi.period','year_id','期间'),
    }
    _order = 's_date'

    def create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('fi.period')
        for fy in self.browse(cr, uid, ids, context=context):
            ds = datetime.strptime(fy.s_date, '%Y-%m-%d')
            while ds.strftime('%Y-%m-%d') < fy.e_date:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.e_date:
                    de = datetime.strptime(fy.e_date, '%Y-%m-%d')

                period_obj.create(cr, uid, {
                    'company_id':1,#fy.company_id,
                    'name': ds.strftime('%Y%m'),
                    'month':int(ds.strftime('%m')),
                    's_date': ds.strftime('%Y-%m-%d'),
                    'e_date': de.strftime('%Y-%m-%d'),
                    'year_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

class fi_cost_type(osv.osv):
    '''辅助核算类型'''
    _name = 'fi.cost.type'
    _columns = {
        'name':fields.char('名称',size=64),
        'model':fields.char('对象',size=64),
        'format':fields.char('账簿格式',size=64)
                }
