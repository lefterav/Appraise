from corpus.models import *
from evaluation.models import *
from evaluation.models import _RankingRank
from sentence.ranking import Ranking
from sentence.sentence import SimpleSentence
from sentence.parallelsentence import ParallelSentence
from itertools import groupby
from operator import attrgetter, itemgetter
from io_utils.sax.saxps2jcml import IncrementalJcml
import time

def average(l):
    return float(sum(l))/len(l) if len(l)>0 else float('nan')
    
def commajoin(l):
    return ",".join([str(i) for i in l])

class ResultsWriter:
    def __init__(self, filename, writerclass=IncrementalJcml):
        self.len = 0
        self.writer = IncrementalJcml(filename)
        self.starttime = time.clock()

    def close(self):
        self.writer.close()
        time_elapsed = time.clock() - self.starttime    
        try:    
            print "{} sec per sentence".format(time_elapsed*1.00/self.len)
        except:
            pass

    
    def _initialize_parallelsentence(self, sourcesentence, targetsentences, target_language):
        """
        Create a ParallelSentence object and initialize its basic arguments, given a SourceSentence
        django model and a list of target sentences
        @param sentence_custom_id: the custom sentence_id that points to the source sentence entry
        @type sentence_custom_id: corpus.models.SourceSentence        
        @param targetsentences: a list of translations already wrapped in the sentence.SimpleSentence object
        @type targetsentences: [sentence.SimpleSentence, ...]
        """
        
        #in round 4 there are more sentences with the same custom id, but there attributes
        #should be identical, so we only fetch the first one
        
        parallelsentence_attributes = {}
        parallelsentence_attributes['id'] = sourcesentence.custom_id.strip()
        parallelsentence_attributes['langsrc'] = sourcesentence.document.language.name.lower()
        parallelsentence_attributes['langtgt'] = target_language.lower()
        parallelsentence_attributes['testset'] = sourcesentence.document.sourcedocument.custom_id
        simplesentence = SimpleSentence(sourcesentence.text)
        parallelsentence = ParallelSentence(simplesentence, targetsentences, None, parallelsentence_attributes)
        return parallelsentence
        
        
    def _get_targetsentences(self, system_names, translation_texts, combined_ranking, quality_ranking, detailed_ranks, detailed_qualityscores):
        """
        Convert a list of rank objects into a list of SimpleSentence objects
        @param system_names: a list of system names
        @type system_names: [str, ...]
        @param translation_texts: a list of the strings of translations
        @type translation_texts: [str, ...]
        @param combined_ranking: a list of the respective rank values for the translations
        @type translation_texts: [object, ...]
        @param quality_ranking: a list of the respective quality scores for the translations
        @type quality_ranking: [object, ...]
        """
        translationlist = []
    
        for system, translation_text, rank, qualityscore, detailed_rank, detailed_qualityscore in zip(system_names, translation_texts, combined_ranking, quality_ranking, detailed_ranks, detailed_qualityscores):
            tgt_attributes = {}
            tgt_attributes['system'] = system
            tgt_attributes['rank'] = str(rank)
            tgt_attributes['ranks'] = detailed_rank
            tgt_attributes['quality_score'] = str(qualityscore)
            tgt_attributes['quality_scores'] = detailed_qualityscore
            translationlist.append(SimpleSentence(translation_text, tgt_attributes))
        return translationlist


    def get_rank_per_system(self, sentence, aggregate_function=sum):
        """
        Retrieve from DB the rankings relevant for this sentence and 
        return a dict of the rank valuies indexed by system name. 
        We do this, instead of sending multiple requests, in order to 
        avoid a bottleneck due to the multiple joins.
        
        @param sentence: the source sentence django model 
        @type sentence: evaluation.models.SourceSentence     
        @return: a rank output per system name
        @rtype: dict(corpus.models.TranslationSystem, float)
        """
        ## Process ranking for this sentence

        sentence_custom_id = sentence.custom_id        
        #get the ranking results for this particular sentence
        rankingresults = RankingResult.objects.filter(item__source_sentence__custom_id=sentence_custom_id).order_by('item__source_sentence__custom_id').exclude(user__username='wizard')
       
        #retrieve all ranking judgments for this sentence
        for rankingresult in rankingresults:
            ranks = rankingresult._rankingrank_set.order_by('translation__document__translateddocument__translation_system').all()
            
        #index ranks by system    
        groupped_ranks = {}
        for rank in ranks:
            groupped_ranks.setdefault(rank.translation.document.translateddocument.translation_system, []).append(rank)
        
        #there may be more than one ranks per system due to multiple judgments
        #here an aggregate function can merge them
        #this function can be passed as a parameter to the function
        aggregated_ranks = {}
        detailed_ranks = {}
        for system, ranks in groupped_ranks.iteritems():
            aggregated_ranks[system] = aggregate_function([rank.rank for rank in ranks])
            detailed_ranks[system] = ",".join(["{}:{}".format(rank.result.user.username,rank.rank) for rank in ranks])

        return aggregated_ranks, detailed_ranks



    def get_qualityscore_per_system(self, sentence, aggregate_function=average):
        """
        Retrieve from DB the rankings relevant for this sentence and 
        return a dict of the rank valuies indexed by system name. 
        We do this, instead of sending multiple requests, in order to 
        avoid a bottleneck due to the multiple joins.
        
        @param sentence: the source sentence django model 
        @type sentence: evaluation.models.SourceSentence     
        @return: a rank output per system name
        @rtype: dict(corpus.models.TranslationSystem, float)
        """
        sentence_custom_id = sentence.custom_id
        qualityresults = QualityResult.objects.filter(item__source_sentence__custom_id=sentence_custom_id).exclude(user__username='wizard').order_by("item__systems")
     


        #index ranks by system
        groupped_scores = {}
        for result in qualityresults:
            groupped_scores.setdefault(result.item.systems.get(), []).append(result)

        
        #aggregate
        aggregated_scores = {}
        detailed_scores = {}

        for system, results in groupped_scores.iteritems():
            aggregated_scores[system] = aggregate_function([result.score for result in results])
            detailed_scores[system] = ",".join(["{}:{}".format(result.user.username,result.score) for result in results])
            
        
        return aggregated_scores, detailed_scores
        
        

    def get_translation_per_system(self, sentence):
        """
        Retrieve from DB the tranlsations given for this sentence and 
        return a dict of the translation texts indexed by system name. 
        
        @param sentence: the source sentence django model 
        @type sentence: evaluation.models.SourceSentence     
        @return: a dict of stringa containing the translation produced by each system
        @rtype: dict(corpus.models.TranslationSystem, str)
        """
        
        translations = Translation.objects.filter(source_sentence=sentence)
        indexed_translations = dict([(translation.document.translateddocument.translation_system, translation.text.strip()) for translation in translations])
        return indexed_translations
        


    def process_sentence(self, sentence, target_language):
        """
        Function that is to process the evaluation of a particular source sentence
        @param sentence: the source sentence database object that needs to be processed
        @type sentence: SourceSentence
        """

        #combined original ranking assigned by humans
        combined_ranking = Ranking([])  
        #ranking consisting of quality scores
        quality_ranking = Ranking([])   

        sentence_custom_id = sentence.custom_id


        #this will give us a dict of rankingrank object lists, indexed by translation system objects
        groupped_ranks, detailed_ranks = self.get_rank_per_system(sentence)
        groupped_qualityscores, detailed_qualityscores = self.get_qualityscore_per_system(sentence)
        indexed_translations =  self.get_translation_per_system(sentence)
        
        #get attributes and text from source of the parallelsentence
        
        system_names = []
        translation_texts = []
        
        for system, qualityscore in groupped_qualityscores.iteritems():
            #if there is no rank for this translation (it happens) don't include it            
            try:
                rank = groupped_ranks[system]
            except KeyError:
                continue
            translation_text = indexed_translations[system]
     
            #get respective ranking results
            quality_ranking.append(qualityscore)
            combined_ranking.append(rank)
            translation_texts.append(translation_text)
            system_names.append(system.name)
        
        #we get everything together in order to normalize                     
        combined_ranking = combined_ranking.normalize()
        #quality_ranking = quality_ranking.normalize()
        
        targetsentences = self._get_targetsentences(system_names, translation_texts, combined_ranking, quality_ranking, detailed_ranks, detailed_qualityscores)
        
        parallelsentence = self._initialize_parallelsentence(sentence, targetsentences, target_language)
        self.writer.add_parallelsentence(parallelsentence)


    def process_corpus(self, corpus, target_language):
        """
        Function that is supposed to be repeated once per corpus
        """
        
        
        sentences = SourceSentence.objects.filter(evaluationitem__task__corpus=corpus, evaluationitem__newevaluationresult__qualityresult__isnull=False).filter(evaluationitem__newevaluationresult__rankingresult__isnull=False)
        
        seen_custom_sentence_ids = set()
       
        for sentence in sentences:
            if sentence.custom_id not in seen_custom_sentence_ids:
                self.process_sentence(sentence, target_language)
                self.len += 1
                seen_custom_sentence_ids.add(sentence.custom_id)


def process_task_name__contains(keyword,prefix):
    corpora = Corpus.objects.filter(evaluationtask__task_name__contains=keyword)

    for corpus in corpora:
        for target_language in [task.targetLanguage.name for task in corpus.evaluationtask_set.all()]:

    #        task_name = task.task_name.replace(' ', '_').replace("'", '_').replace(':','_').lower()
            language_pair = "{}-{}".format(corpus.language.name.lower(), target_language.lower())
            filename = "{prefix}_{task_name}_{language_pair}.jcml".format(prefix=prefix,
                                                                          task_name=corpus.custom_id,
                                                                          language_pair=language_pair)
            print "=================\n{}\n=================".format(filename)                                                                          
                                                                          
            resultswriter = ResultsWriter(filename)
            resultswriter.process_corpus(corpus, target_language)
            resultswriter.close()
        
        
if __name__ == '__main__':
    process_task_name__contains("Round 4", "/home/appraise/R4_")
