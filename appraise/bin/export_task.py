from evaluation.models import *
from corpus.models import Translation
from evaluation.models import _RankingRank
from elementtree.SimpleXMLWriter import XMLWriter
from django.utils.html import escape
import sys
#pip install elementtree

class XmlFormat:            
    HEAD = "appraise-results"
    TASK = {'RankingTask': 'ranking-result',
            'PostEditAllTask': 'post-editing-result',
            'SelectAndPostEditTask': 'post-editing-result',
            'QualityTask': 'quality-result'}
    ITEM = {'RankingTask': 'ranking-item',
            'PostEditAllTask': 'post-editing-item',
            'SelectAndPostEditTask': 'post-editing-item',
            'QualityTask': 'quality-item'}
    SOURCE = "source"
    TRANSLATION = "translation"
    POSTEDIT = "post-editing"
    


class TaraxuDjangoWriter:
    def __init__(self, filename, encoding='utf-8', x=XmlFormat):
        self.xmlfile = open(filename, 'w')
        self.writer = XMLWriter(self.xmlfile, encoding)
        self.x = x
        self.doc = self.writer.start(self.x.HEAD)            
    
    def close(self):
        self.writer.close(self.doc)
        self.xmlfile.close()
        
    def start_task(self, task):
        #detect what type of task this is and remember it for encapsulated elements
        self.ttype = type(task).__name__
        #start task and remember it so that we can close
        self.task = self.writer.start(self.x.TASK[self.ttype],
                                      id=task.corpus.custom_id,
                                      sourcelanguage=task.corpus.language.name)          
    
    def end_task(self, task):
        self.writer.close(self.task)
        
    def add_result(self, result):
        label = self.x.ITEM[self.ttype]
        
        #pythonic way to get to the particular type of the result
        try:
            result = result.rankingresult
        except:
            pass       
        else:
            self.writer.start(label, 
                                id=result.item.source_sentence.custom_id.strip(),
                                duration=str(result.duration),
                                user=result.user.username,
                                
                                )
            ranks = _RankingRank.objects.filter(result=result)
            self.writer.element(self.x.SOURCE, result.item.source_sentence.text)
            for rank in ranks:
                self.writer.element(self.x.TRANSLATION,
                                    rank.translation.text,
                                    system=rank.translation.document.translateddocument.translation_system.name,
                                    rank=str(rank.rank))
            self.writer.end()
        
        try: 
            result = result.selectandposteditresult
        except:
            pass
        else:
            self.writer.start(label,
                                id=result.item.source_sentence.custom_id.strip(),
                                duration=str(result.duration),
                                user=result.user.username,
                                )
            self.writer.element(self.x.SOURCE, result.item.source_sentence.text)
            
            try:
                translation = Translation.objects.get(source_sentence=result.item.source_sentence, document__translateddocument__translation_system=result.system)
                self.writer.element(self.x.TRANSLATION, translation.text)
            except:
                pass
            try:
                self.writer.element(self.x.POSTEDIT, 
                                result.sentence, system=result.system.name, 
                                fromscratch=str(result.fromScratch))
            except:
                self.writer.element(self.x.POSTEDIT,
                                result.sentence, system="?", 
                                fromscratch=str(result.fromScratch))
            self.writer.end()
            
        try:
            result = result.qualityresult
        except:
            pass
        else:
            self.writer.start(label,
                                id=result.item.source_sentence.custom_id.strip(),
                                duration=str(result.duration),
                                user=result.user.username,
                                )
            self.writer.element(self.x.SOURCE, result.item.source_sentence.text)
            
            try:
                result_system = result.item.systems.all()[0]
                translation_text = Translation.objects.get(source_sentence=result.item.source_sentence, document__translateddocument__translation_system=result_system).text
            except:
                translation_text = "<ERROR>"
            try:
                system_name = result_system.name
            except:
                system_name = "?"                
            self.writer.element(self.x.TRANSLATION,
                                translation_text,
                                system=system_name, 
                                score=str(result.score))
            self.writer.end()
            
    
        


def _finished_tasks(keyword, limit):
    """ 
    Fetch finished tasks, whose name matches a given keyword and they are 100% completed
    @param keyword: A keyword string to be looked for
    @type keyword: str
    """
    finished_tasks = []
    task_types = [QualityTask] #, RankingTask, SelectAndPostEditTask, PostEditAllTask]          ####DEBUG
    for task_type in task_types:
        tasks = task_type.objects.filter(task_name__contains=keyword, active=True)
        for task in tasks:
            itemcount = EvaluationItem.objects.filter(task=task).count()
            usercount = task.users.all().count()
            total_itemcount = itemcount * usercount
            resultcount = NewEvaluationResult.objects.filter(item__task=task).count()
            percentage = resultcount*1.00/total_itemcount
            if percentage>=limit:
                finished_tasks.append(task)
    print "Found {} finished tasks".format(len(finished_tasks))
                
    return finished_tasks
    

def _write_task(task, filename):
    xmlwriter = TaraxuDjangoWriter(filename)
    results = NewEvaluationResult.objects.filter(item__task=task).exclude(user__username='wizard')
    xmlwriter.start_task(task)
    for result in results:   
        xmlwriter.add_result(result)
            #print type(result).__name__

    xmlwriter.end_task(task)
    xmlwriter.close()


if __name__ == "__main__":
    try:
        keyword = sys.argv[1]
        directory = sys.argv[2]
            
    except:
        print "Please provide a keyword that should be part of the Task name"
        keyword = "Round 4"
        
    try:
        limit = float(sys.argv[3])
    except:
        limit = 1.00
       

    for task in _finished_tasks(keyword, limit):
    
        filename = directory+"/"+task.corpus.custom_id+"."+type(task).__name__+".results.xml"
        print filename        
        _write_task(task, filename)


        

            



