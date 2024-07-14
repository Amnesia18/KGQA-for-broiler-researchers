from django.shortcuts import render
from django.http import JsonResponse
from py2neo import Graph
import jieba.posseg as pseg
import jieba
from fuzzywuzzy import fuzz
import os

# 建立与Neo4j的连接
graph = Graph("http://localhost:7474", auth=('neo4j', '123456'))

# 定义用户意图模式和响应模板
school = [
    '这位专家是哪个学校的研究人员？',
    '这位专家是哪个学校的成员？',
    '这位专家属于哪个学校？',
    '请问这位专家是哪个学校的？',
    '这位专家在哪个学校工作？'
]

Researchunits = [
    '这位专家是哪个单位的研究人员？',
    '这位专家是哪个研究单位的成员？',
    '这位专家属于哪个机构？',
    '这位专家在哪个单位工作？',
    '这位专家的研究单位是什么？'
]

Jobtitle = [
    '这位专家的职称有哪些？',
    '这位专家的专业职称有哪些？',
    '请问这位专家的职称是什么？',
    '这位专家的学术头衔是什么？',
    '这位专家的工作职位是什么？'
]

degree = [
    '这位专家的学位是什么？',
    '这位专家的学历背景是什么？',
    '这位专家拥有怎样的学位？',
    '这位专家的最高学历是什么？',
    '请问这位专家的学术学位是什么？'
]

position = [
    '这位专家的职位是什么？',
    '请问这位专家的工作职位是什么？',
    '这位专家担任什么职位？',
    '这位专家的工作岗位是什么？',
    '这位专家的职务是什么？'
]

research = [
    '这个专家的研究方向是什么',
    '这个专家的研究方向是什么？',
    '这位专家主要研究什么领域？',
    '这位专家的研究领域有哪些？',
    '这位专家关注的研究主题是什么？',
    '这位专家的主要研究课题是什么？',
    '这位专家在什么方面开展研究？',
    '这位专家的研究重点是什么',
    '这位专家致力于哪方面的研究？',
    '这位专家专注于哪类研究？',
    '这位专家的科研工作涉及哪些方面？'
]

relationship = [
    '这两位专家之间的关系是什么？',
    '请问这两位专家合作过哪些项目？',
    '这两位专家共同发表过哪些论文？',
    '这两位专家之间的合作是什么？',
    '请问这两位专家之间有何联系？'
]

# 响应模板
schoolResponse = '{}这位专家所在的学校是{}'
ResearchunitsResponse = '{}这位专家的研究单位是{}'
JobtitleResponse = '{}这位专家的职称是{}'
degreeResponse = '{}这位专家的学位是{}'
positionResponse = '{}这位专家的职位是{}'
researchResponse = '{}这位专家的研究方向是{}'
relationshipResponse = '{} 和 {} 之间的关系是: {}'

# 用户意图模式字典
stencil = {
    'school': school,
    'Researchunits': Researchunits,
    'Jobtitle': Jobtitle,
    'degree': degree,
    'position': position,
    'research': research,
    'relationship': relationship
}

# 响应模板字典
responseDict = {
    'schoolResponse': schoolResponse,
    'ResearchunitsResponse': ResearchunitsResponse,
    'JobtitleResponse': JobtitleResponse,
    'degreeResponse': degreeResponse,
    'positionResponse': positionResponse,
    'researchResponse': researchResponse,
    'relationshipResponse': relationshipResponse
}


def AssignIntension(text):
    stencilDegree = {}
    for key, value in stencil.items():
        score = 0
        for item in value:
            degree = fuzz.partial_ratio(text, item)
            score += degree
        stencilDegree[key] = score / len(value)
    return stencilDegree


def getExpertName(text):
    expertName = ''
    jieba.load_userdict('./expert.txt')  # 加载自定义词典
    words = pseg.cut(text)
    for w in words:
        if w.flag == 'zj':
            expertName = w.word
    return expertName


def SearchGraph(expertName, stencilDict={}, targetExpert=None):
    classification = max(stencilDict, key=stencilDict.get)
    if classification == 'research':
        cypher = f'''
        MATCH (e:Expert {{name: "{expertName}"}})-[:研究]->(r:Theme2)
        RETURN r.theme AS field
        '''
        result = graph.run(cypher).data()

        if not result:
            return classification, "No data available"

        fields = [record['field'] for record in result]
        data = '; '.join(fields)
    elif targetExpert:
        cypher = f'''
        MATCH (n:Expert)-[r]->(m:Expert)
        WHERE n.name = "{expertName}" AND m.name = "{targetExpert}"
        RETURN type(r) AS relation
        UNION
        MATCH (n:Expert)<-[r]-(m:Expert)
        WHERE n.name = "{expertName}" AND m.name = "{targetExpert}"
        RETURN type(r) AS relation
        '''
        result = graph.run(cypher).data()

        if not result:
            return classification, "No data available"

        relations = [record['relation'] for record in result]
        data = '; '.join(relations)
    else:
        cypher = f'MATCH (n:Expert) WHERE n.name = "{expertName}" RETURN n.{classification} AS result'
        result = graph.run(cypher).data()

        if not result:
            return classification, "No data available"

        data = result[0].get('result', 'No data available')

    return classification, data


def respondQuery(expertName, classification, item):
    query = classification + 'Response'
    response = responseDict.get(query, '{}该问题暂无答案')
    return response.format(expertName, item)


def respondRelationshipQuery(expertName, targetExpert, relations):
    response = responseDict.get('relationshipResponse', '{} 和 {} 之间没有关系数据')
    return response.format(expertName, targetExpert, relations)


def query(request):
    if request.method == 'GET':
        queryText = request.GET.get('query')
        if queryText is None:
            return render(request, 'qa/query.html')

        experts = queryText.split('和')  # 简单处理多个专家名字
        if len(experts) == 2:
            expertName = getExpertName(experts[0])
            targetExpert = getExpertName(experts[1])
            dict = AssignIntension(queryText)
            classification, result = SearchGraph(expertName, dict, targetExpert=targetExpert)
            response = respondRelationshipQuery(expertName, targetExpert, result)
        else:
            expertName = getExpertName(queryText)
            dict = AssignIntension(queryText)
            classification, result = SearchGraph(expertName, dict)
            response = respondQuery(expertName, classification, result)

        return JsonResponse({'response': response})
    return render(request, 'qa/query.html')
