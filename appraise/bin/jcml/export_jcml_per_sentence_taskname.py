#export PYTHONPATH=$PYTHONPATH:/wizard/qualitative/src/
#export DJANGO_SETTINGS_MODULE=appraise.settings

from evaluation.models import _RankingRank
from evaluation.models import *
from corpus.models import *

from sentence.sentence import SimpleSentence
from sentence.parallelsentence import ParallelSentence
from io_utils.sax.saxps2jcml import IncrementalJcml
from numpy import std, average
import os

KEYWORD = "Round 4"
OUTPUT_FILENAME = "R4.jcml"
OUTPUT_FOLDER = "/local/qt21/data/evaluation_interface/results/r4/jcml"

def ranks2simplesentences(ranks):
    """
    Convert a list of rank objects into a list of SimpleSentence objects
    """
    translationlist = []
    for rank in ranks:
        tgt_text = rank.translation.text
        tgt_attributes = {}
        tgt_attributes['system'] = rank.translation.document.translateddocument.translation_system.name
        tgt_attributes['rank'] = str(rank.rank)
        
        tgt_attributes.update(get_quality_attributes(rank))
        tgt_attributes.update(get_selectpostedit_attributes(rank))
        
        translationlist.append(SimpleSentence(tgt_text, tgt_attributes))
    return translationlist
    

def get_quality_attributes(rank):
    """
    Get the quality scores in the database for the given ranking sentence
    and put feautures in a dic
    """
    att = {}
    ranking_result = rank.result
    ranking_user = rank.result.user
    ranked_system = rank.translation.document.translateddocument.translation_system
    rank_source_sentence = rank.result.item.source_sentence
    quality_results = QualityResult.objects.select_related('user').filter(item__systems__id__exact=ranked_system.id,
                                                   item__source_sentence=rank_source_sentence).exclude(user__username='wizard' )
    
    i=0
    all_scores = []
    
    if quality_results.count() == 0:
        return {"quality_scored": False}
    
    for result in quality_results:
        i+=1
        att["quality_{}_user".format(i)] = result.user.username
        result_score = result.score
        att["quality_{}_score".format(i)] = str(result_score)
        all_scores.append(result_score)
    
    att["quality_all_scores_avg"] = average(all_scores)
    att["quality_all_scores_std"] = std(all_scores)
    att["quality_all_scores_min"] = min(all_scores)
    att["quality_all_scores_max"] = max(all_scores)                
    

    thisuser_quality_results = quality_results.filter(user=ranking_user)
    if thisuser_quality_results.count() == 0:
        att["quality_my_scores"] = "None"
        return att
    thisuser_quality_scores = [result.score for result in thisuser_quality_results]
    att["quality_my_scores"] = ",".join([str(score) for score in thisuser_quality_scores])
    att["quality_my_scores_avg"] = average(thisuser_quality_scores)
    att["quality_my_scores_std"] = std(thisuser_quality_scores)
    att["quality_my_scores_min"] = min(thisuser_quality_scores)
    att["quality_my_scores_max"] = max(thisuser_quality_scores)        
    return att
    
  
def get_selectpostedit_attributes(rank):
    """
    Get the annotations from select and postedit from the database for the given ranking sentence
    """
    att = {}
    ranking_result = rank.result
    ranked_system = rank.translation.document.translateddocument.translation_system
    rank_source_sentence = rank.result.item.source_sentence
    selectpostedit_results = SelectAndPostEditResult.objects.filter(system=ranked_system, item__source_sentence=rank_source_sentence).exclude(user__username='wizard')

    selectpostedit_count = selectpostedit_results.count()
    if selectpostedit_count == 0:
        return {"selectpostedit": 0}
    att["selectpostedit"] = 1
    att["selectpostedit_count"] = selectpostedit_count
    return att
    
        
    
    


def write_parallelsentences(sourcesentences, writer):
    """
    get all source sentences for the particular document and write them with the given writer
    """
    for sourcesentence in sourcesentences: #TODO remove debug
        parallelsentence_attributes = {}
        parallelsentence_attributes['id'] = sourcesentence.custom_id.strip()
        src_text = sourcesentence.text        
        writer_src = SimpleSentence(src_text)
        parallelsentence_attributes['langsrc'] = sourcesentence.document.language.name.lower()
        parallelsentence_attributes['testset'] = sourcesentence.document.sourcedocument.custom_id
        
        ranking_results = RankingResult.objects.filter(item__source_sentence=sourcesentence).exclude(user__username='wizard')
        
        writer_translations = []
        
        #TODO: fetch here quality score and post-editing if possible

        #get all ranking judgments for this source sentence (may be more than one)
        for ranking_result in ranking_results:
            parallelsentence_attributes['judge_id'] = ranking_result.user.username
            parallelsentence_attributes['langtgt'] = ranking_result.item.task.targetLanguage.name.lower()
            parallelsentence_attributes['result_id'] = ranking_result.id
            
            
            #get the ranking list for this particular judgment
            ranks = _RankingRank.objects.select_related('result','translation__document__translateddocument','result__item', 'result__user').filter(result=ranking_result)            
            writer_translations = ranks2simplesentences(ranks)
            
            #write one parallel sentence for each ranking judgment
            writer_parallelsentence = ParallelSentence(writer_src, writer_translations, None, parallelsentence_attributes)
            writer.add_parallelsentence(writer_parallelsentence)



if __name__ == "__main__":

    tasks = EvaluationTask.objects.filter(task_name__contains=KEYWORD)

    #preferable a separate file per task data (i.e. wmt12, wmt10, openoffice)
    for task in tasks:
        sourcesentences = SourceSentence.objects.select_related('evaluationitem__task', 'document', 'document__language', 'document__sourcedocument', ).filter(evaluationitem__task=task)
        
        #avoid creating a file, if task is not relevant
        if sourcesentences.count()==0:
            continue
        
        filename = os.path.join(OUTPUT_FOLDER, "task_"+task.task_id+"_"+OUTPUT_FILENAME)
        writer = IncrementalJcml(filename)
        write_parallelsentences(sourcesentences, writer)            
        writer.close()

    
