# from data_process import ReverseIndex
#
# a = [
#     {
#         'title': '中国教育学会',
#         'word': '中国教育学会',
#         'description': ' 新中国成立最早、规模最大的全国性教育学术团体，覆盖基础教育所有学科，遵循学术为本、服务立会的办会方针，助推中小学校长、教师及广大会员的职业进步和专业成长。',
#         'href': 'http://www.cse.edu.cn/index/index.html?category=9'
#     },
#     {
#         'title': '黄金宝_天天基金网',
#         'word': '天天基金网,1234567,网上交易，基金买卖，基金申购，基金赎回，买基金，卖基金，活期宝，基金怎么买，基金超市，热销基金，基金主题，高收益基金，固定收益基金，基金净值,基金网,基金交易,免费开户,企业开户，开放式基金,封闭式基金,每日基金净值,基金净值估算，基金公司,净值实时走势,基金行情,基金折价率,基金吧,基金学校,基金评级,基金代码,财富节,1218财富节,加息券,免费领红包,年终奖,理财节,高端理财,基金理财,财富管理',
#         'description': '天天基金网,1234567,网上交易，基金买卖，基金申购，基金赎回，买基金，卖基金，活期宝，基金怎么买，基金超市，热销基金，基金主题，高收益基金，固定收益基金，基金净值,基金网,基金交易,免费开户,企业开户，开放式基金,封闭式基金,每日基金净值,基金净值估算，基金公司,净值实时走势,基金行情,基金折价率,基金吧,基金学校,基金评级,基金代码,财富节,1218财富节,加息券,免费领红包,年终奖,理财节,高端理财,基金理财,财富管理',
#         'href': 'http://fundsc.eastmoney.com/2016/huangjinbao/?spm=100015.rwm'
#     },
# ]
#
# reverse = ReverseIndex()
# reverse.build_index(a)
# print(reverse.index)
# reverse.save_index()

# import jieba
#
# a = jieba.cut_for_search('GitHub updates platform with passkeys and DevOps streamlining | VentureBeat')

# from mongodb import MongoDB, del_repeat, find_all
# with MongoDB() as db:
#     a = find_all(db.col)
#     print(list(a[0:100]))

